using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;

namespace StS2Tracker;

public static class CombatTracker
{
    private static readonly List<CombatData> _combats = new();
    private static CombatData? _current;
    private static int _turnNumber;
    private static RunInfo? _runInfo;
    private static string? _outputPath;
    private static readonly string _outputDir;

    static CombatTracker()
    {
        _outputDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "SlayTheSpire2", "tracker");
    }

    public static void Initialize()
    {
        _combats.Clear();
        _current = null;
        _turnNumber = 0;
        _runInfo = null;
        _outputPath = null;
        ModEntry.Log("CombatTracker initialized. Output dir: " + _outputDir);
    }

    // --- Called by Harmony patches ---

    public static void OnCombatStart(IRunState? runState, CombatState? combatState)
    {
        if (combatState == null) return;

        _turnNumber = 0;

        // Capture run info once on first combat
        if (_runInfo == null && runState != null)
        {
            string seed = runState.Rng?.StringSeed ?? "unknown";
            long startTime = DateTimeOffset.UtcNow.ToUnixTimeSeconds();

            _runInfo = new RunInfo
            {
                Seed = seed,
                StartTime = startTime,
                Ascension = runState.AscensionLevel,
                Acts = runState.Acts?.Select(a => a.Id.ToString()).ToList() ?? new(),
                GameMode = runState.Modifiers?.Count > 0 ? "custom" : "standard",
            };

            // Capture player info from the combat state (has all players)
            foreach (var player in combatState.Players)
            {
                _runInfo.Players.Add(new RunPlayerInfo
                {
                    SteamId = player.NetId.ToString(),
                    Character = player.Character.Id.ToString(),
                });
            }

            _outputPath = Path.Combine(_outputDir, $"{seed}_{startTime}.json");

            ModEntry.Log($"Run info captured: {seed} A{_runInfo.Ascension} " +
                         $"{string.Join(", ", _runInfo.Players.Select(p => p.Character))}");
        }

        var encounter = combatState.Encounter;
        int floor = runState?.TotalFloor ?? (_combats.Count + 1);
        _current = new CombatData
        {
            Encounter = encounter.Id.ToString(),
            Monsters = combatState.Enemies
                .Select(e => e.ModelId.ToString())
                .ToList(),
            Floor = floor,
        };

        // Initialize player stats
        foreach (var player in combatState.Players)
        {
            var pid = player.NetId.ToString();
            _current.Players[pid] = new PlayerCombatStats
            {
                Character = player.Character.Id.ToString(),
                SteamId = pid,
            };
        }

        ModEntry.Log($"Combat started: {_current.Encounter} (floor {floor}) with {_current.Players.Count} player(s)");
    }

    public static void OnCombatEnd(IRunState? runState, CombatState? combatState, CombatRoom? room)
    {
        if (_current == null) return;

        _current.TotalTurns = _turnNumber;

        // Determine result
        bool victory = combatState?.Enemies.All(e => !e.IsAlive) ?? false;
        _current.Result = victory ? "win" : "loss";

        _combats.Add(_current);
        ModEntry.Log($"Combat ended: {_current.Encounter} = {_current.Result} " +
                     $"({_current.TotalTurns} turns, {_current.Players.Count} players)");

        // Log summary per player
        foreach (var (pid, stats) in _current.Players)
        {
            ModEntry.Log($"  Player {pid}: dealt={stats.DamageDealt} taken={stats.DamageTaken} " +
                         $"block={stats.BlockGained} cards={stats.CardsPlayed}");
        }

        // Write after each combat for safety
        WriteToDisk();
        _current = null;
    }

    public static void OnTurnStart(Player player)
    {
        _turnNumber++;
    }

    public static void OnDamageGiven(Creature? dealer, DamageResult result, Creature target, CardModel? cardSource)
    {
        if (_current == null) return;

        // Attribute damage to the dealer's player
        string? dealerPid = GetPlayerId(dealer);
        if (dealerPid != null && _current.Players.TryGetValue(dealerPid, out var dealerStats))
        {
            dealerStats.DamageDealt += result.TotalDamage;

            // Per-turn tracking
            EnsureTurnEntry(dealerStats);
            dealerStats.DamagePerTurn[^1] += result.TotalDamage;

            // Per-target tracking
            string targetKey = target.ModelId.ToString();
            if (!dealerStats.DamageByTarget.ContainsKey(targetKey))
                dealerStats.DamageByTarget[targetKey] = 0;
            dealerStats.DamageByTarget[targetKey] += result.TotalDamage;

            // Per-card damage tracking
            string cardKey = cardSource?.Id.ToString() ?? "_non_card";
            if (!dealerStats.DamageByCard.ContainsKey(cardKey))
                dealerStats.DamageByCard[cardKey] = new CardDamageStats();
            var cardStats = dealerStats.DamageByCard[cardKey];
            cardStats.TotalDamage += result.TotalDamage;
            cardStats.Hits++;
            if (result.TotalDamage > cardStats.MaxHit)
                cardStats.MaxHit = result.TotalDamage;
            if (result.WasTargetKilled)
                cardStats.Kills++;

            if (result.WasTargetKilled)
                dealerStats.Kills++;
        }

        // Track damage received by target player
        string? targetPid = GetPlayerId(target);
        if (targetPid != null && _current.Players.TryGetValue(targetPid, out var targetStats))
        {
            targetStats.DamageTaken += result.UnblockedDamage;
            targetStats.DamageBlocked += result.BlockedDamage;
        }
    }

    public static void OnBlockGained(Creature creature, decimal amount)
    {
        if (_current == null) return;

        string? pid = GetPlayerId(creature);
        if (pid != null && _current.Players.TryGetValue(pid, out var stats))
        {
            stats.BlockGained += (int)amount;
            EnsureTurnEntry(stats);
            stats.BlockPerTurn[^1] += (int)amount;
        }
    }

    public static void OnCardPlayed(CardPlay cardPlay)
    {
        if (_current == null) return;

        var card = cardPlay.Card;
        string? pid = card.Owner?.NetId.ToString();
        if (pid != null && _current.Players.TryGetValue(pid, out var stats))
        {
            stats.CardsPlayed++;
            EnsureTurnEntry(stats);
            stats.CardsPerTurn[^1]++;

            stats.CardSequence.Add(new CardPlayEntry
            {
                Card = card.Id.ToString(),
                Target = cardPlay.Target?.ModelId.ToString(),
                Turn = _turnNumber,
            });
        }
    }

    // --- Helpers ---

    private static string? GetPlayerId(Creature? creature)
    {
        if (creature == null) return null;
        if (creature.IsPlayer && creature.Player != null)
            return creature.Player.NetId.ToString();
        if (creature.IsPet && creature.PetOwner != null)
            return creature.PetOwner.NetId.ToString();
        return null;
    }

    private static void EnsureTurnEntry(PlayerCombatStats stats)
    {
        while (stats.DamagePerTurn.Count < _turnNumber)
            stats.DamagePerTurn.Add(0);
        while (stats.BlockPerTurn.Count < _turnNumber)
            stats.BlockPerTurn.Add(0);
        while (stats.CardsPerTurn.Count < _turnNumber)
            stats.CardsPerTurn.Add(0);
    }

    private static void WriteToDisk()
    {
        if (_runInfo == null || _outputPath == null) return;

        try
        {
            if (!Directory.Exists(_outputDir))
                Directory.CreateDirectory(_outputDir);

            var runData = new RunTrackerData
            {
                ModVersion = "0.1.0",
                RunInfo = _runInfo,
                Combats = _combats.ToList(),
            };

            string json = JsonSerializer.Serialize(runData, new JsonSerializerOptions
            {
                WriteIndented = true,
                DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
            });
            File.WriteAllText(_outputPath, json);
            ModEntry.Log($"Wrote tracker data to {_outputPath} ({json.Length} bytes, {_combats.Count} combats)");
        }
        catch (Exception ex)
        {
            ModEntry.Log("ERROR writing tracker data: " + ex.Message);
        }
    }
}

// --- Data models for JSON serialization ---

public class RunTrackerData
{
    [JsonPropertyName("mod_version")]
    public string ModVersion { get; set; } = "";

    [JsonPropertyName("run_info")]
    public RunInfo RunInfo { get; set; } = new();

    [JsonPropertyName("combats")]
    public List<CombatData> Combats { get; set; } = new();
}

public class RunInfo
{
    [JsonPropertyName("seed")]
    public string Seed { get; set; } = "";

    [JsonPropertyName("start_time")]
    public long StartTime { get; set; }

    [JsonPropertyName("ascension")]
    public int Ascension { get; set; }

    [JsonPropertyName("game_mode")]
    public string GameMode { get; set; } = "standard";

    [JsonPropertyName("acts")]
    public List<string> Acts { get; set; } = new();

    [JsonPropertyName("players")]
    public List<RunPlayerInfo> Players { get; set; } = new();
}

public class RunPlayerInfo
{
    [JsonPropertyName("steam_id")]
    public string SteamId { get; set; } = "";

    [JsonPropertyName("character")]
    public string Character { get; set; } = "";
}

public class CombatData
{
    [JsonPropertyName("encounter")]
    public string Encounter { get; set; } = "";

    [JsonPropertyName("monsters")]
    public List<string> Monsters { get; set; } = new();

    [JsonPropertyName("floor")]
    public int Floor { get; set; }

    [JsonPropertyName("total_turns")]
    public int TotalTurns { get; set; }

    [JsonPropertyName("result")]
    public string Result { get; set; } = "";

    [JsonPropertyName("players")]
    public Dictionary<string, PlayerCombatStats> Players { get; set; } = new();
}

public class PlayerCombatStats
{
    [JsonPropertyName("steam_id")]
    public string SteamId { get; set; } = "";

    [JsonPropertyName("character")]
    public string Character { get; set; } = "";

    [JsonPropertyName("damage_dealt")]
    public int DamageDealt { get; set; }

    [JsonPropertyName("damage_taken")]
    public int DamageTaken { get; set; }

    [JsonPropertyName("damage_blocked")]
    public int DamageBlocked { get; set; }

    [JsonPropertyName("block_gained")]
    public int BlockGained { get; set; }

    [JsonPropertyName("cards_played")]
    public int CardsPlayed { get; set; }

    [JsonPropertyName("kills")]
    public int Kills { get; set; }

    [JsonPropertyName("damage_per_turn")]
    public List<int> DamagePerTurn { get; set; } = new();

    [JsonPropertyName("block_per_turn")]
    public List<int> BlockPerTurn { get; set; } = new();

    [JsonPropertyName("cards_per_turn")]
    public List<int> CardsPerTurn { get; set; } = new();

    [JsonPropertyName("card_sequence")]
    public List<CardPlayEntry> CardSequence { get; set; } = new();

    [JsonPropertyName("damage_by_target")]
    public Dictionary<string, int> DamageByTarget { get; set; } = new();

    [JsonPropertyName("damage_by_card")]
    public Dictionary<string, CardDamageStats> DamageByCard { get; set; } = new();
}

public class CardDamageStats
{
    [JsonPropertyName("total_damage")]
    public int TotalDamage { get; set; }

    [JsonPropertyName("hits")]
    public int Hits { get; set; }

    [JsonPropertyName("max_hit")]
    public int MaxHit { get; set; }

    [JsonPropertyName("kills")]
    public int Kills { get; set; }
}

public class CardPlayEntry
{
    [JsonPropertyName("card")]
    public string Card { get; set; } = "";

    [JsonPropertyName("target")]
    public string? Target { get; set; }

    [JsonPropertyName("turn")]
    public int Turn { get; set; }
}
