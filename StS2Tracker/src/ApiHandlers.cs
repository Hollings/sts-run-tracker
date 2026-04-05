using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace StS2Tracker;

public static class ApiHandlers
{
    private static readonly JsonSerializerOptions s_jsonOptions = new()
    {
        WriteIndented = false,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    // GET /api/live
    public static string HandleLive()
    {
        try
        {
            var tracker = CombatTracker.GetSnapshot();
            var save = SaveFileReader.LoadCurrentRun();
            if (tracker == null && save == null)
                return "{\"status\":\"no_data\",\"data\":null}";
            string merged = MergeEngine.MergeLiveRun(tracker, save);
            return "{\"status\":\"ok\",\"data\":" + merged + "}";
        }
        catch (Exception ex)
        {
            ModEntry.Log("Error in /api/live: " + ex.Message);
            return "{\"status\":\"error\",\"data\":null}";
        }
    }

    // GET /api/runs
    public static string HandleRunsList()
    {
        try
        {
            var runs = SaveFileReader.LoadAllRuns();
            var summaries = new List<Dictionary<string, object?>>();
            foreach (var run in runs)
            {
                string filename = "";
                if (run.TryGetValue("_filename", out var fnEl))
                    filename = fnEl.GetString() ?? "";
                summaries.Add(MergeEngine.BuildRunSummary(run, filename));
            }
            return JsonSerializer.Serialize(summaries, s_jsonOptions);
        }
        catch (Exception ex)
        {
            ModEntry.Log("Error in /api/runs: " + ex.Message);
            return "[]";
        }
    }

    // GET /api/runs/{filename} -- null return signals HttpServer to send 404
    public static string HandleRunDetail(string filename)
    {
        try
        {
            var run = SaveFileReader.LoadRun(filename);
            if (run == null)
                return null!;
            return JsonSerializer.Serialize(run, s_jsonOptions);
        }
        catch (Exception ex)
        {
            ModEntry.Log("Error in /api/runs/" + filename + ": " + ex.Message);
            return null!;
        }
    }

    // GET /api/progress
    public static string HandleProgress()
    {
        try
        {
            var data = SaveFileReader.LoadProgress();
            if (data == null)
                return "{\"status\":\"no_data\",\"data\":null}";

            var subset = new Dictionary<string, object?>();
            if (data.TryGetValue("character_stats", out var cs)) subset["character_stats"] = cs;
            if (data.TryGetValue("card_stats", out var cas)) subset["card_stats"] = cas;
            if (data.TryGetValue("encounter_stats", out var es)) subset["encounter_stats"] = es;
            if (data.TryGetValue("total_playtime", out var tp)) subset["total_playtime"] = tp;
            if (data.TryGetValue("floors_climbed", out var fc)) subset["floors_climbed"] = fc;
            if (data.TryGetValue("architect_damage", out var ad)) subset["architect_damage"] = ad;

            return "{\"status\":\"ok\",\"data\":" + JsonSerializer.Serialize(subset, s_jsonOptions) + "}";
        }
        catch (Exception ex)
        {
            ModEntry.Log("Error in /api/progress: " + ex.Message);
            return "{\"status\":\"no_data\",\"data\":null}";
        }
    }
}
