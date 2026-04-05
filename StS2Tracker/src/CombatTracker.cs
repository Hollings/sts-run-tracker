using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
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
    private const string CurrentModVersion = "0.1.0";
    private static readonly ReaderWriterLockSlim _rwLock = new();
    private static readonly List<CombatData> _combats = new();
    private static CombatData? _current;
    private static int _turnNumber;
    private static readonly Dictionary<string, int> _playerTurns = new();
    private static RunInfo? _runInfo;
    private static string? _outputPath;
    private static readonly string _outputDir;

    /// <summary>
    /// Fired after any state change. WebSocketManager registers a handler
    /// to broadcast updates to connected clients.
    /// </summary>
    public static Action? OnDataChanged;
    private static readonly JsonSerializerOptions s_jsonOptions = new()
    {
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

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
        _playerTurns.Clear();
        _runInfo = null;
        _outputPath = null;
        OnDataChanged = null;
        ModEntry.Log("CombatTracker initialized. Output dir: " + _outputDir);
    }

    // --- Called by Harmony patches ---

    public static void OnCombatStart(IRunState? runState, CombatState? combatState)
    {
        if (combatState == null) return;

        _rwLock.EnterWriteLock();
        try
        {
            _turnNumber = 0;
            _playerTurns.Clear();

            // Detect new run: if the seed changed, reinitialize everything
            if (runState != null && _runInfo != null)
            {
                string currentSeed = runState.Rng?.StringSeed ?? "unknown";
                if (currentSeed != _runInfo.Seed)
                {
                    ModEntry.Log($"New run detected (seed changed: {_runInfo.Seed} -> {currentSeed}). Resetting tracker.");
                    Initialize();
                }
            }

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
        finally
        {
            _rwLock.ExitWriteLock();
        }
        OnDataChanged?.Invoke();
    }

    public static void OnCombatEnd(IRunState? runState, CombatState? combatState, CombatRoom? room)
    {
        _rwLock.EnterWriteLock();
        try
        {
            if (_current == null) return;

            _current.TotalTurns = _turnNumber;

            // Find in-progress entry BEFORE changing result (same object reference)
            int existingIdx = _combats.FindIndex(c => c.Encounter == _current.Encounter && c.Floor == _current.Floor && c.Result == "in_progress");

            // Determine result
            bool victory = combatState?.Enemies.All(e => !e.IsAlive) ?? false;
            _current.Result = victory ? "win" : "loss";

            // Replace in-progress entry if we had one, otherwise add
            if (existingIdx >= 0)
                _combats[existingIdx] = _current;
            else
                _combats.Add(_current);

            ModEntry.Log($"Combat ended: {_current.Encounter} = {_current.Result} " +
                         $"({_current.TotalTurns} turns, {_current.Players.Count} players)");

            foreach (var (pid, stats) in _current.Players)
            {
                ModEntry.Log($"  Player {pid}: dealt={stats.DamageDealt} taken={stats.DamageTaken} " +
                             $"block={stats.BlockGained} cards={stats.CardsPlayed}");
            }

            WriteToDisk();
            _current = null;
        }
        finally
        {
            _rwLock.ExitWriteLock();
        }
        OnDataChanged?.Invoke();
    }

    public static void OnTurnStart(Player player)
    {
        _rwLock.EnterWriteLock();
        try
        {
            _turnNumber++;

            // Track per-player turn count
            string pid = player.NetId.ToString();
            if (!_playerTurns.ContainsKey(pid))
                _playerTurns[pid] = 0;
            _playerTurns[pid]++;

            FlushInProgress();
        }
        finally
        {
            _rwLock.ExitWriteLock();
        }
        OnDataChanged?.Invoke();
    }

    /// <summary>
    /// Write in-progress combat to disk so data is preserved even if the player dies.
    /// The in-progress entry gets replaced on next flush or finalized on combat end.
    /// </summary>
    private static void FlushInProgress()
    {
        if (_current == null) return;

        _current.TotalTurns = _turnNumber;
        _current.Result = "in_progress";

        // Add or update the in-progress entry
        int existingIdx = _combats.FindIndex(c => c.Encounter == _current.Encounter && c.Floor == _current.Floor && c.Result == "in_progress");
        if (existingIdx >= 0)
            _combats[existingIdx] = _current;
        else
            _combats.Add(_current);

        WriteToDisk();
    }

    public static void OnDamageGiven(Creature? dealer, DamageResult result, Creature target, CardModel? cardSource)
    {
        _rwLock.EnterWriteLock();
        try
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

                // Per-turn damage taken
                EnsureTurnEntry(targetStats);
                targetStats.DamageTakenPerTurn[^1] += result.UnblockedDamage;
                targetStats.DamageBlockedPerTurn[^1] += result.BlockedDamage;

                // Per-source damage breakdown (both blocked and unblocked)
                string sourceKey = dealer?.ModelId.ToString() ?? "_environmental";
                if (!targetStats.DamageTakenBySource.ContainsKey(sourceKey))
                    targetStats.DamageTakenBySource[sourceKey] = new DamageTakenStats();
                var srcStats = targetStats.DamageTakenBySource[sourceKey];
                srcStats.Unblocked += result.UnblockedDamage;
                srcStats.Blocked += result.BlockedDamage;
                srcStats.Hits++;
                if (result.UnblockedDamage > srcStats.MaxHit)
                    srcStats.MaxHit = result.UnblockedDamage;

                // Log individual hit for granular analysis
                targetStats.HitsReceived.Add(new HitReceivedEntry
                {
                    Source = sourceKey,
                    Unblocked = result.UnblockedDamage,
                    Blocked = result.BlockedDamage,
                    Turn = _turnNumber,
                    WasKilled = result.WasTargetKilled,
                });

                // Flush after taking damage - this could be the killing blow
                FlushInProgress();
            }
        }
        finally
        {
            _rwLock.ExitWriteLock();
        }
        OnDataChanged?.Invoke();
    }

    public static void OnBlockGained(Creature creature, decimal amount)
    {
        _rwLock.EnterWriteLock();
        try
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
        finally
        {
            _rwLock.ExitWriteLock();
        }
        OnDataChanged?.Invoke();
    }

    public static void OnCardPlayed(CardPlay cardPlay)
    {
        _rwLock.EnterWriteLock();
        try
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
        finally
        {
            _rwLock.ExitWriteLock();
        }
        OnDataChanged?.Invoke();
    }

    public static void OnPowerChanged(PowerModel power, int amount, Creature? applier)
    {
        _rwLock.EnterWriteLock();
        try
        {
            if (_current == null) return;

            string powerId = power.Id.ToString();
            Creature target = power.Owner;
            string targetId = target.ModelId.ToString();
            string? applierId = applier?.ModelId.ToString();

            // Track on the applier player (buffs/debuffs they caused)
            string? applierPid = GetPlayerId(applier);
            if (applierPid != null && _current.Players.TryGetValue(applierPid, out var applierStats))
            {
                if (!applierStats.PowersApplied.ContainsKey(powerId))
                    applierStats.PowersApplied[powerId] = 0;
                applierStats.PowersApplied[powerId] += amount;
            }

            // Track on the target player (buffs/debuffs they received)
            string? targetPid = GetPlayerId(target);
            if (targetPid != null && _current.Players.TryGetValue(targetPid, out var targetStats))
            {
                if (!targetStats.PowersReceived.ContainsKey(powerId))
                    targetStats.PowersReceived[powerId] = 0;
                targetStats.PowersReceived[powerId] += amount;
            }

            // Log the event on whichever player is involved (prefer target, fall back to applier)
            string? logPid = targetPid ?? applierPid;
            if (logPid != null && _current.Players.TryGetValue(logPid, out var logStats))
            {
                logStats.PowerLog.Add(new PowerEventEntry
                {
                    Power = powerId,
                    Stacks = amount,
                    Target = targetId,
                    Source = applierId,
                    Turn = _turnNumber,
                });
            }
        }
        finally
        {
            _rwLock.ExitWriteLock();
        }
        OnDataChanged?.Invoke();
    }

    // --- Thread-safe read access ---

    /// <summary>
    /// Thread-safe snapshot of current tracker data as a JSON string.
    /// Called from HTTP threads to serve /api/live and WebSocket updates.
    /// </summary>
    public static string? GetSnapshotJson()
    {
        _rwLock.EnterReadLock();
        try
        {
            var data = BuildSnapshot();
            if (data == null) return null;
            return JsonSerializer.Serialize(data, s_jsonOptions);
        }
        finally
        {
            _rwLock.ExitReadLock();
        }
    }

    /// <summary>
    /// Thread-safe snapshot of current tracker data as typed object.
    /// Returns null if no run is active.
    /// </summary>
    public static RunTrackerData? GetSnapshot()
    {
        _rwLock.EnterReadLock();
        try
        {
            return BuildSnapshot();
        }
        finally
        {
            _rwLock.ExitReadLock();
        }
    }

    // --- Helpers ---

    /// <summary>
    /// Build a RunTrackerData snapshot. Caller must hold a read or write lock.
    /// </summary>
    private static RunTrackerData? BuildSnapshot()
    {
        if (_runInfo == null) return null;
        return new RunTrackerData
        {
            ModVersion = CurrentModVersion,
            RunInfo = _runInfo,
            Combats = _combats.ToList(),  // shallow copy to isolate from future mutations
        };
    }

    private static string? GetPlayerId(Creature? creature)
    {
        if (creature == null) return null;
        if (creature.IsPlayer && creature.Player != null)
            return creature.Player.NetId.ToString();
        if (creature.IsPet && creature.PetOwner != null)
            return creature.PetOwner.NetId.ToString();
        return null;
    }

    private static int GetPlayerTurnCount(string pid)
    {
        return _playerTurns.TryGetValue(pid, out int count) ? count : 1;
    }

    private static void EnsureTurnEntry(PlayerCombatStats stats)
    {
        int turnCount = GetPlayerTurnCount(stats.SteamId);
        while (stats.DamagePerTurn.Count < turnCount)
            stats.DamagePerTurn.Add(0);
        while (stats.BlockPerTurn.Count < turnCount)
            stats.BlockPerTurn.Add(0);
        while (stats.CardsPerTurn.Count < turnCount)
            stats.CardsPerTurn.Add(0);
        while (stats.DamageTakenPerTurn.Count < turnCount)
            stats.DamageTakenPerTurn.Add(0);
        while (stats.DamageBlockedPerTurn.Count < turnCount)
            stats.DamageBlockedPerTurn.Add(0);
    }

    private static void WriteToDisk()
    {
        if (_runInfo == null || _outputPath == null) return;

        try
        {
            if (!Directory.Exists(_outputDir))
                Directory.CreateDirectory(_outputDir);

            var runData = BuildSnapshot()!;
            string json = JsonSerializer.Serialize(runData, s_jsonOptions);
            string tempPath = _outputPath + ".tmp";
            File.WriteAllText(tempPath, json);
            File.Move(tempPath, _outputPath, overwrite: true);
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

    [JsonPropertyName("damage_taken_per_turn")]
    public List<int> DamageTakenPerTurn { get; set; } = new();

    [JsonPropertyName("damage_blocked_per_turn")]
    public List<int> DamageBlockedPerTurn { get; set; } = new();

    [JsonPropertyName("damage_by_card")]
    public Dictionary<string, CardDamageStats> DamageByCard { get; set; } = new();

    [JsonPropertyName("damage_taken_by_source")]
    public Dictionary<string, DamageTakenStats> DamageTakenBySource { get; set; } = new();

    [JsonPropertyName("hits_received")]
    public List<HitReceivedEntry> HitsReceived { get; set; } = new();

    [JsonPropertyName("powers_applied")]
    public Dictionary<string, int> PowersApplied { get; set; } = new();

    [JsonPropertyName("powers_received")]
    public Dictionary<string, int> PowersReceived { get; set; } = new();

    [JsonPropertyName("power_log")]
    public List<PowerEventEntry> PowerLog { get; set; } = new();
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

public class DamageTakenStats
{
    [JsonPropertyName("unblocked")]
    public int Unblocked { get; set; }

    [JsonPropertyName("blocked")]
    public int Blocked { get; set; }

    [JsonPropertyName("hits")]
    public int Hits { get; set; }

    [JsonPropertyName("max_hit")]
    public int MaxHit { get; set; }
}

public class HitReceivedEntry
{
    [JsonPropertyName("source")]
    public string Source { get; set; } = "";

    [JsonPropertyName("unblocked")]
    public int Unblocked { get; set; }

    [JsonPropertyName("blocked")]
    public int Blocked { get; set; }

    [JsonPropertyName("turn")]
    public int Turn { get; set; }

    [JsonPropertyName("was_killed")]
    public bool WasKilled { get; set; }
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

public class PowerEventEntry
{
    [JsonPropertyName("power")]
    public string Power { get; set; } = "";

    [JsonPropertyName("stacks")]
    public int Stacks { get; set; }

    [JsonPropertyName("target")]
    public string Target { get; set; } = "";

    [JsonPropertyName("source")]
    public string? Source { get; set; }

    [JsonPropertyName("turn")]
    public int Turn { get; set; }
}
