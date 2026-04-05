using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace StS2Tracker;

/// <summary>
/// Ports the Python merge.py logic to C#.
/// Combines mod tracker data (combat detail) with game save data (floor-by-floor
/// HP, gold, card/relic picks, events) into a unified run view.
/// All methods are static and thread-safe (no mutable static state).
/// </summary>
public static class MergeEngine
{
    private static readonly JsonSerializerOptions s_jsonOptions = new()
    {
        WriteIndented = false,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    private static readonly TextInfo s_textInfo =
        CultureInfo.InvariantCulture.TextInfo;

    private static readonly Dictionary<string, string> s_roomTypeNames = new()
    {
        ["rest_site"] = "Rest Site",
        ["treasure"] = "Treasure",
        ["shop"] = "Shop",
        ["event"] = "Event",
        ["unknown"] = "Event",
        ["ancient"] = "Ancient",
        ["monster"] = "Monster",
        ["elite"] = "Elite",
        ["boss"] = "Boss",
    };

    // -----------------------------------------------------------------------
    // ShortId: "CARD.STRIKE_IRONCLAD" -> "Strike Ironclad"
    // -----------------------------------------------------------------------

    public static string ShortId(string? fullId)
    {
        if (string.IsNullOrEmpty(fullId))
            return "?";
        string id = fullId;
        int dotIdx = id.IndexOf('.');
        if (dotIdx >= 0)
            id = id.Substring(dotIdx + 1);
        return s_textInfo.ToTitleCase(id.Replace('_', ' ').ToLowerInvariant());
    }

    // -----------------------------------------------------------------------
    // MergeLiveRun: core merge of tracker + save -> unified JSON
    // -----------------------------------------------------------------------

    public static string MergeLiveRun(
        RunTrackerData? tracker,
        Dictionary<string, JsonElement>? save)
    {
        var runInfo = new Dictionary<string, object?>();
        var floors = new List<Dictionary<string, object?>>();
        var combats = new List<object>();
        var runTotals = new Dictionary<string, object?>();

        var matchedCombats = new HashSet<int>();

        // Run info and raw combats from tracker
        List<CombatData> trackerCombats;
        if (tracker != null)
        {
            runInfo = RunInfoToDict(tracker.RunInfo);
            trackerCombats = tracker.Combats ?? new List<CombatData>();
            foreach (var c in trackerCombats)
                combats.Add(c);
        }
        else
        {
            trackerCombats = new List<CombatData>();
        }

        // Validate seeds match; discard stale save data
        if (save != null && tracker != null)
        {
            string trackerSeed = tracker.RunInfo?.Seed ?? "";
            string saveSeed = GetString(save, "seed");

            if (!string.IsNullOrEmpty(trackerSeed) && !string.IsNullOrEmpty(saveSeed)
                && trackerSeed != saveSeed)
            {
                save = null;
            }
            else if (!string.IsNullOrEmpty(trackerSeed) && string.IsNullOrEmpty(saveSeed))
            {
                long trackerStart = tracker.RunInfo?.StartTime ?? 0;
                long saveStart = GetLong(save, "start_time");
                if (trackerStart > 0 && saveStart > 0
                    && Math.Abs(trackerStart - saveStart) > 3600)
                {
                    save = null;
                }
            }
        }

        // Build floor timeline from save's map_point_history
        if (save != null)
        {
            // Overlay run info from save if tracker didn't provide it
            if (runInfo.Count == 0)
            {
                runInfo = BuildRunInfoFromSave(save);
            }

            int floorNum = 0;
            if (save.TryGetValue("map_point_history", out var historyEl)
                && historyEl.ValueKind == JsonValueKind.Array)
            {
                int actIdx = 0;
                foreach (var act in historyEl.EnumerateArray())
                {
                    if (act.ValueKind != JsonValueKind.Array)
                    {
                        actIdx++;
                        continue;
                    }
                    foreach (var mp in act.EnumerateArray())
                    {
                        floorNum++;
                        var floor = BuildFloor(mp, floorNum, actIdx);

                        // Try to match combat data from tracker
                        string floorType = floor.TryGetValue("type", out var ft)
                            ? ft?.ToString() ?? "" : "";
                        if (tracker != null && IsCombatLikeType(floorType))
                        {
                            string roomModel = GetRoomModelId(mp);
                            bool matched = false;

                            // First pass: match by floor number
                            for (int ci = 0; ci < trackerCombats.Count; ci++)
                            {
                                if (matchedCombats.Contains(ci)) continue;
                                if (trackerCombats[ci].Floor == floorNum)
                                {
                                    floor["combat"] = trackerCombats[ci];
                                    matchedCombats.Add(ci);
                                    matched = true;
                                    break;
                                }
                            }

                            // Second pass: match by encounter name
                            if (!matched)
                            {
                                for (int ci = 0; ci < trackerCombats.Count; ci++)
                                {
                                    if (matchedCombats.Contains(ci)) continue;
                                    if (!string.IsNullOrEmpty(roomModel)
                                        && trackerCombats[ci].Encounter == roomModel)
                                    {
                                        floor["combat"] = trackerCombats[ci];
                                        matchedCombats.Add(ci);
                                        break;
                                    }
                                }
                            }
                        }

                        floors.Add(floor);
                    }
                    actIdx++;
                }
            }
        }

        // Inject synthetic floors for tracker combats not yet in the save
        if (tracker != null)
        {
            var existingFloors = new HashSet<int>(floors.Select(f =>
                f.TryGetValue("floor", out var fv) && fv is int fi ? fi : 0));
            var seenSynthetic = new HashSet<int>();

            for (int ci = 0; ci < trackerCombats.Count; ci++)
            {
                var combat = trackerCombats[ci];
                int combatFloor = combat.Floor;
                if (existingFloors.Contains(combatFloor) || seenSynthetic.Contains(combatFloor))
                    continue;
                seenSynthetic.Add(combatFloor);

                string encounter = combat.Encounter ?? "";
                string encLower = encounter.ToLowerInvariant();
                string floorType;
                if (encLower.Contains("boss"))
                    floorType = "boss";
                else if (encLower.Contains("elite"))
                    floorType = "elite";
                else
                    floorType = "monster";

                int lastAct = floors.Count > 0
                    && floors[^1].TryGetValue("act", out var la) && la is int lai
                        ? lai : 1;

                var playersList = new List<Dictionary<string, object?>>();
                foreach (var kvp in combat.Players)
                {
                    playersList.Add(new Dictionary<string, object?>
                    {
                        ["player_id"] = kvp.Key,
                        ["hp"] = 0,
                        ["max_hp"] = 0,
                        ["damage_taken"] = kvp.Value.DamageTaken,
                        ["hp_healed"] = 0,
                        ["gold"] = 0,
                        ["gold_gained"] = 0,
                        ["gold_spent"] = 0,
                        ["cards_picked"] = Array.Empty<string>(),
                        ["cards_skipped"] = Array.Empty<string>(),
                        ["relics_picked"] = Array.Empty<string>(),
                        ["potions_picked"] = Array.Empty<string>(),
                        ["event_choices"] = Array.Empty<string>(),
                    });
                }

                var synthetic = new Dictionary<string, object?>
                {
                    ["floor"] = combatFloor,
                    ["act"] = lastAct,
                    ["type"] = floorType,
                    ["room_id"] = ShortId(encounter),
                    ["room_type"] = floorType,
                    ["turns_taken"] = combat.TotalTurns,
                    ["monsters"] = combat.Monsters.Select(m => ShortId(m)).ToList(),
                    ["players"] = playersList,
                    ["combat"] = combat,
                };
                floors.Add(synthetic);
            }
        }

        // Compute run totals
        if (trackerCombats.Count > 0)
            runTotals = ComputeRunTotals(trackerCombats);

        var result = new Dictionary<string, object?>
        {
            ["run_info"] = runInfo,
            ["floors"] = floors,
            ["combats"] = combats,
            ["run_totals"] = runTotals,
        };

        return JsonSerializer.Serialize(result, s_jsonOptions);
    }

    // -----------------------------------------------------------------------
    // BuildRunSummary: compact summary from a history .run file
    // -----------------------------------------------------------------------

    public static Dictionary<string, object?> BuildRunSummary(
        Dictionary<string, JsonElement> run,
        string filename)
    {
        var characters = new List<string>();
        if (run.TryGetValue("players", out var playersEl)
            && playersEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var p in playersEl.EnumerateArray())
            {
                if (p.TryGetProperty("character", out var chEl))
                    characters.Add(chEl.GetString() ?? "");
            }
        }

        string killedBy = GetString(run, "killed_by_encounter");
        if (killedBy == "NONE.NONE" || string.IsNullOrEmpty(killedBy))
        {
            killedBy = GetString(run, "killed_by_event");
        }

        int floorCount = 0;
        if (run.TryGetValue("map_point_history", out var histEl)
            && histEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var act in histEl.EnumerateArray())
            {
                if (act.ValueKind == JsonValueKind.Array)
                    floorCount += act.GetArrayLength();
            }
        }

        return new Dictionary<string, object?>
        {
            ["filename"] = filename,
            ["seed"] = GetString(run, "seed"),
            ["start_time"] = GetLong(run, "start_time"),
            ["run_time"] = GetLong(run, "run_time"),
            ["win"] = GetBool(run, "win"),
            ["was_abandoned"] = GetBool(run, "was_abandoned"),
            ["ascension"] = GetInt(run, "ascension"),
            ["characters"] = characters,
            ["killed_by"] = killedBy,
            ["floor_count"] = floorCount,
            ["game_mode"] = GetStringOrDefault(run, "game_mode", "standard"),
        };
    }

    // -----------------------------------------------------------------------
    // BuildFloor: build a floor entry from a map_point_history entry
    // -----------------------------------------------------------------------

    private static Dictionary<string, object?> BuildFloor(
        JsonElement mp, int floorNum, int actIdx)
    {
        JsonElement room = default;
        bool hasRoom = false;
        if (mp.TryGetProperty("rooms", out var roomsEl)
            && roomsEl.ValueKind == JsonValueKind.Array
            && roomsEl.GetArrayLength() > 0)
        {
            room = roomsEl[0];
            hasRoom = true;
        }

        string mapPointType = "unknown";
        if (mp.TryGetProperty("map_point_type", out var mptEl))
            mapPointType = mptEl.GetString() ?? "unknown";

        string roomModelId = hasRoom && room.TryGetProperty("model_id", out var midEl)
            ? midEl.GetString() ?? "" : "";
        string roomId = ShortId(roomModelId);
        if (roomId == "?")
        {
            s_roomTypeNames.TryGetValue(mapPointType, out var fallback);
            roomId = fallback ?? mapPointType;
        }

        string roomType = hasRoom && room.TryGetProperty("room_type", out var rtEl)
            ? rtEl.GetString() ?? "" : "";
        int turnsTaken = hasRoom && room.TryGetProperty("turns_taken", out var ttEl)
            ? ttEl.GetInt32() : 0;

        var monsters = new List<string>();
        if (hasRoom && room.TryGetProperty("monster_ids", out var monstersEl)
            && monstersEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var m in monstersEl.EnumerateArray())
                monsters.Add(ShortId(m.GetString()));
        }

        var playersList = new List<Dictionary<string, object?>>();
        if (mp.TryGetProperty("player_stats", out var psArrayEl)
            && psArrayEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var ps in psArrayEl.EnumerateArray())
            {
                var playerFloor = BuildPlayerFloor(ps);
                playersList.Add(playerFloor);
            }
        }

        return new Dictionary<string, object?>
        {
            ["floor"] = floorNum,
            ["act"] = actIdx + 1,
            ["type"] = mapPointType,
            ["room_id"] = roomId,
            ["room_type"] = roomType,
            ["turns_taken"] = turnsTaken,
            ["monsters"] = monsters,
            ["players"] = playersList,
        };
    }

    // -----------------------------------------------------------------------
    // BuildPlayerFloor: extract per-player floor data from a player_stats entry
    // -----------------------------------------------------------------------

    private static Dictionary<string, object?> BuildPlayerFloor(JsonElement ps)
    {
        var result = new Dictionary<string, object?>
        {
            ["player_id"] = GetJsonString(ps, "player_id"),
            ["hp"] = GetJsonInt(ps, "current_hp"),
            ["max_hp"] = GetJsonInt(ps, "max_hp"),
            ["damage_taken"] = GetJsonInt(ps, "damage_taken"),
            ["hp_healed"] = GetJsonInt(ps, "hp_healed"),
            ["gold"] = GetJsonInt(ps, "current_gold"),
            ["gold_gained"] = GetJsonInt(ps, "gold_gained"),
            ["gold_spent"] = GetJsonInt(ps, "gold_spent"),
        };

        // Card choices
        var cardsPicked = new List<string>();
        var cardsSkipped = new List<string>();
        if (ps.TryGetProperty("card_choices", out var ccEl)
            && ccEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var cc in ccEl.EnumerateArray())
            {
                string cardId = "";
                if (cc.TryGetProperty("card", out var cardEl)
                    && cardEl.TryGetProperty("id", out var idEl))
                {
                    cardId = idEl.GetString() ?? "";
                }
                bool wasPicked = cc.TryGetProperty("was_picked", out var wpEl)
                    && wpEl.GetBoolean();
                if (wasPicked)
                    cardsPicked.Add(ShortId(cardId));
                else
                    cardsSkipped.Add(ShortId(cardId));
            }
        }
        result["cards_picked"] = cardsPicked;
        result["cards_skipped"] = cardsSkipped;

        result["relics_picked"] = CollectPickedChoices(ps, "relic_choices");
        result["potions_picked"] = CollectPickedChoices(ps, "potion_choices");

        // Event choices
        var eventChoices = new List<string>();
        if (ps.TryGetProperty("event_choices", out var ecEl)
            && ecEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var ec in ecEl.EnumerateArray())
            {
                string key = "";
                if (ec.TryGetProperty("title", out var titleEl)
                    && titleEl.TryGetProperty("key", out var keyEl))
                {
                    key = keyEl.GetString() ?? "";
                }
                eventChoices.Add(ParseEventChoice(key));
            }
        }
        result["event_choices"] = eventChoices;

        // Rest site choices
        var restSiteChoices = new List<string>();
        if (ps.TryGetProperty("rest_site_choices", out var rscEl)
            && rscEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var rsc in rscEl.EnumerateArray())
            {
                string s = rsc.GetString() ?? "";
                restSiteChoices.Add(s_textInfo.ToTitleCase(s.ToLowerInvariant()));
            }
        }
        result["rest_site_choices"] = restSiteChoices;

        // Upgraded cards
        var upgradedCards = new List<string>();
        if (ps.TryGetProperty("upgraded_cards", out var ucEl)
            && ucEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var uc in ucEl.EnumerateArray())
                upgradedCards.Add(ShortId(uc.GetString()));
        }
        result["upgraded_cards"] = upgradedCards;

        return result;
    }

    // -----------------------------------------------------------------------
    // ComputeRunTotals: aggregate combat stats across the full run
    // -----------------------------------------------------------------------

    private static Dictionary<string, object?> ComputeRunTotals(
        List<CombatData> combats)
    {
        var playerTotals = new Dictionary<string, Dictionary<string, object?>>();

        foreach (var combat in combats)
        {
            foreach (var kvp in combat.Players)
            {
                string pid = kvp.Key;
                var stats = kvp.Value;

                if (!playerTotals.TryGetValue(pid, out var t))
                {
                    t = new Dictionary<string, object?>
                    {
                        ["steam_id"] = pid,
                        ["character"] = stats.Character ?? "",
                        ["damage_dealt"] = 0,
                        ["damage_taken"] = 0,
                        ["damage_blocked"] = 0,
                        ["block_gained"] = 0,
                        ["cards_played"] = 0,
                        ["kills"] = 0,
                        ["combats"] = 0,
                        ["best_hit"] = new Dictionary<string, object?>
                        {
                            ["card"] = "",
                            ["damage"] = 0,
                            ["encounter"] = "",
                        },
                        ["damage_by_card"] = new Dictionary<string, Dictionary<string, object?>>(),
                    };
                    playerTotals[pid] = t;
                }

                t["damage_dealt"] = (int)t["damage_dealt"]! + stats.DamageDealt;
                t["damage_taken"] = (int)t["damage_taken"]! + stats.DamageTaken;
                t["damage_blocked"] = (int)t["damage_blocked"]! + stats.DamageBlocked;
                t["block_gained"] = (int)t["block_gained"]! + stats.BlockGained;
                t["cards_played"] = (int)t["cards_played"]! + stats.CardsPlayed;
                t["kills"] = (int)t["kills"]! + stats.Kills;
                t["combats"] = (int)t["combats"]! + 1;

                // Aggregate per-card damage and find best single hit
                var damageByCard = (Dictionary<string, Dictionary<string, object?>>)t["damage_by_card"]!;
                foreach (var cardKvp in stats.DamageByCard)
                {
                    string cardId = cardKvp.Key;
                    var cardStats = cardKvp.Value;

                    if (!damageByCard.TryGetValue(cardId, out var agg))
                    {
                        agg = new Dictionary<string, object?>
                        {
                            ["total_damage"] = 0,
                            ["hits"] = 0,
                            ["max_hit"] = 0,
                            ["kills"] = 0,
                        };
                        damageByCard[cardId] = agg;
                    }

                    agg["total_damage"] = (int)agg["total_damage"]! + cardStats.TotalDamage;
                    agg["hits"] = (int)agg["hits"]! + cardStats.Hits;
                    agg["kills"] = (int)agg["kills"]! + cardStats.Kills;
                    if (cardStats.MaxHit > (int)agg["max_hit"]!)
                        agg["max_hit"] = cardStats.MaxHit;

                    // Track best single hit across the run
                    var bestHit = (Dictionary<string, object?>)t["best_hit"]!;
                    if (cardStats.MaxHit > (int)bestHit["damage"]!)
                    {
                        bestHit["card"] = ShortId(cardId);
                        bestHit["damage"] = cardStats.MaxHit;
                        bestHit["encounter"] = ShortId(combat.Encounter ?? "");
                    }
                }
            }
        }

        return new Dictionary<string, object?>
        {
            ["total_combats"] = combats.Count,
            ["wins"] = combats.Count(c => c.Result == "win"),
            ["losses"] = combats.Count(c => c.Result == "loss"),
            ["players"] = playerTotals,
        };
    }

    // -----------------------------------------------------------------------
    // ParseEventChoice: parse localization keys into readable names
    // -----------------------------------------------------------------------

    private static string ParseEventChoice(string key)
    {
        if (string.IsNullOrEmpty(key))
            return "";

        string[] parts = key.Split('.');

        // Pattern: EVENT.pages.PAGE.options.CHOICE.title
        int optionsIdx = Array.IndexOf(parts, "options");
        if (optionsIdx >= 0 && optionsIdx + 1 < parts.Length)
        {
            string choice = parts[optionsIdx + 1];
            return s_textInfo.ToTitleCase(choice.Replace('_', ' ').ToLowerInvariant());
        }

        // Fallback: use first part
        return s_textInfo.ToTitleCase(parts[0].Replace('_', ' ').ToLowerInvariant());
    }

    /// <summary>
    /// Extract picked choices from a relic_choices or potion_choices array.
    /// Both use the same schema: [{choice: "ID", was_picked: bool}, ...].
    /// </summary>
    private static List<string> CollectPickedChoices(JsonElement ps, string propertyName)
    {
        var result = new List<string>();
        if (ps.TryGetProperty(propertyName, out var arr)
            && arr.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in arr.EnumerateArray())
            {
                bool wasPicked = item.TryGetProperty("was_picked", out var wpEl)
                    && wpEl.GetBoolean();
                if (wasPicked)
                {
                    string choice = item.TryGetProperty("choice", out var chEl)
                        ? chEl.GetString() ?? "" : "";
                    result.Add(ShortId(choice));
                }
            }
        }
        return result;
    }

    private static bool IsCombatLikeType(string floorType)
    {
        return floorType == "monster" || floorType == "elite"
            || floorType == "boss" || floorType == "event"
            || floorType == "unknown";
    }

    private static string GetRoomModelId(JsonElement mp)
    {
        if (mp.TryGetProperty("rooms", out var rooms)
            && rooms.ValueKind == JsonValueKind.Array
            && rooms.GetArrayLength() > 0)
        {
            var firstRoom = rooms[0];
            if (firstRoom.TryGetProperty("model_id", out var mid))
                return mid.GetString() ?? "";
        }
        return "";
    }

    private static Dictionary<string, object?> RunInfoToDict(RunInfo? info)
    {
        if (info == null)
            return new Dictionary<string, object?>();

        return new Dictionary<string, object?>
        {
            ["seed"] = info.Seed,
            ["ascension"] = info.Ascension,
            ["start_time"] = info.StartTime,
            ["game_mode"] = info.GameMode,
            ["acts"] = info.Acts ?? new List<string>(),
            ["players"] = info.Players?.Select(p => new Dictionary<string, object?>
            {
                ["steam_id"] = p.SteamId,
                ["character"] = p.Character,
            }).ToList() ?? new List<Dictionary<string, object?>>(),
        };
    }

    private static Dictionary<string, object?> BuildRunInfoFromSave(
        Dictionary<string, JsonElement> save)
    {
        var players = new List<Dictionary<string, object?>>();
        if (save.TryGetValue("players", out var playersEl)
            && playersEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var p in playersEl.EnumerateArray())
            {
                players.Add(new Dictionary<string, object?>
                {
                    ["steam_id"] = GetJsonString(p, "id"),
                    ["character"] = GetJsonString(p, "character"),
                });
            }
        }

        return new Dictionary<string, object?>
        {
            ["seed"] = GetString(save, "seed"),
            ["ascension"] = GetInt(save, "ascension"),
            ["players"] = players,
        };
    }

    // --- Dictionary<string, JsonElement> helpers ---

    private static string GetString(Dictionary<string, JsonElement> dict, string key)
    {
        if (dict.TryGetValue(key, out var el) && el.ValueKind == JsonValueKind.String)
            return el.GetString() ?? "";
        return "";
    }

    private static string GetStringOrDefault(
        Dictionary<string, JsonElement> dict, string key, string defaultVal)
    {
        if (dict.TryGetValue(key, out var el) && el.ValueKind == JsonValueKind.String)
            return el.GetString() ?? defaultVal;
        return defaultVal;
    }

    private static int GetInt(Dictionary<string, JsonElement> dict, string key)
    {
        if (dict.TryGetValue(key, out var el) && el.ValueKind == JsonValueKind.Number)
            return el.GetInt32();
        return 0;
    }

    private static long GetLong(Dictionary<string, JsonElement> dict, string key)
    {
        if (dict.TryGetValue(key, out var el) && el.ValueKind == JsonValueKind.Number)
            return el.GetInt64();
        return 0;
    }

    private static bool GetBool(Dictionary<string, JsonElement> dict, string key)
    {
        if (dict.TryGetValue(key, out var el))
        {
            if (el.ValueKind == JsonValueKind.True) return true;
            if (el.ValueKind == JsonValueKind.False) return false;
        }
        return false;
    }

    // --- JsonElement property helpers ---

    private static string GetJsonString(JsonElement el, string prop)
    {
        if (el.TryGetProperty(prop, out var val))
        {
            if (val.ValueKind == JsonValueKind.String)
                return val.GetString() ?? "";
            if (val.ValueKind == JsonValueKind.Number)
                return val.GetRawText();
        }
        return "";
    }

    private static int GetJsonInt(JsonElement el, string prop)
    {
        if (el.TryGetProperty(prop, out var val) && val.ValueKind == JsonValueKind.Number)
            return val.GetInt32();
        return 0;
    }
}
