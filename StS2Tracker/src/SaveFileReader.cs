using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;

namespace StS2Tracker;

/// <summary>
/// Reads game save files from disk: current run, run history, and progress.
/// Ported from web/server/merge.py save-reading logic.
/// </summary>
public static class SaveFileReader
{
    private static string? _saveDir;
    private static string? _moddedSaves;
    private static string? _unmoddedSaves;

    public static void Initialize()
    {
        _saveDir = DiscoverSaveDir();
        if (_saveDir != null)
        {
            _moddedSaves = Path.Combine(_saveDir, "modded", "profile1", "saves");
            _unmoddedSaves = Path.Combine(_saveDir, "profile1", "saves");
            ModEntry.Log("SaveFileReader: save dir = " + _saveDir);
            ModEntry.Log("SaveFileReader: modded saves = " + _moddedSaves);
            ModEntry.Log("SaveFileReader: unmodded saves = " + _unmoddedSaves);
        }
        else
        {
            ModEntry.Log("SaveFileReader: WARNING - could not discover save directory");
        }
    }

    /// <summary>
    /// Return the active save profile dir (modded or unmodded).
    /// Prefers modded if it has a current run save or a history directory.
    /// </summary>
    public static string? GetSaveProfileDir()
    {
        if (_moddedSaves == null || _unmoddedSaves == null)
            return null;

        if (File.Exists(Path.Combine(_moddedSaves, "current_run.save")))
            return _moddedSaves;
        if (Directory.Exists(Path.Combine(_moddedSaves, "history")))
            return _moddedSaves;

        return _unmoddedSaves;
    }

    /// <summary>
    /// Load active run save, or fall back to the most recent completed run.
    /// Checks both current_run.save and current_run_mp.save, prefers most recently modified.
    /// </summary>
    public static Dictionary<string, JsonElement>? LoadCurrentRun()
    {
        var saveDir = GetSaveProfileDir();
        if (saveDir == null)
            return null;

        var candidates = new List<string>();
        foreach (var name in new[] { "current_run.save", "current_run_mp.save" })
        {
            var path = Path.Combine(saveDir, name);
            if (File.Exists(path))
                candidates.Add(path);
        }

        if (candidates.Count > 0)
        {
            var best = candidates.OrderByDescending(p => File.GetLastWriteTimeUtc(p)).First();
            return ReadJson(best);
        }

        // No active run - load the latest completed run from history
        var historyDir = Path.Combine(saveDir, "history");
        if (Directory.Exists(historyDir))
        {
            var latest = Directory.GetFiles(historyDir, "*.run")
                .OrderByDescending(f => File.GetLastWriteTimeUtc(f))
                .FirstOrDefault();
            if (latest != null)
                return ReadJson(latest);
        }

        return null;
    }

    /// <summary>
    /// Load all completed .run files from BOTH modded and unmodded history dirs.
    /// Deduplicates by filename. Each dict includes a "_filename" key with the base filename.
    /// Sorted by file modification time, newest first.
    /// </summary>
    public static List<Dictionary<string, JsonElement>> LoadAllRuns()
    {
        var seenFilenames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var results = new List<(DateTime mtime, Dictionary<string, JsonElement> data)>();

        foreach (var historyDir in GetHistoryDirs())
        {
            string[] files;
            try
            {
                files = Directory.GetFiles(historyDir, "*.run");
            }
            catch (Exception ex)
            {
                ModEntry.Log("SaveFileReader: failed to list history dir " + historyDir + ": " + ex.Message);
                continue;
            }

            foreach (var filePath in files)
            {
                var filename = Path.GetFileName(filePath);
                if (!seenFilenames.Add(filename))
                    continue;

                var data = ReadJson(filePath);
                if (data == null)
                    continue;

                using var filenameJson = JsonDocument.Parse(JsonSerializer.Serialize(filename));
                data["_filename"] = filenameJson.RootElement.Clone();

                DateTime mtime;
                try
                {
                    mtime = File.GetLastWriteTimeUtc(filePath);
                }
                catch
                {
                    mtime = DateTime.MinValue;
                }

                results.Add((mtime, data));
            }
        }

        results.Sort((a, b) => b.mtime.CompareTo(a.mtime));
        return results.Select(r => r.data).ToList();
    }

    /// <summary>
    /// Load a specific .run file by filename, searching both modded and unmodded history dirs.
    /// </summary>
    public static Dictionary<string, JsonElement>? LoadRun(string filename)
    {
        if (string.IsNullOrEmpty(filename))
            return null;

        // Sanitize: prevent path traversal
        var safeFilename = Path.GetFileName(filename);

        foreach (var historyDir in GetHistoryDirs())
        {
            var filePath = Path.Combine(historyDir, safeFilename);
            var data = ReadJson(filePath);
            if (data != null)
                return data;
        }

        return null;
    }

    /// <summary>
    /// Load progress.save from the active profile directory.
    /// </summary>
    public static Dictionary<string, JsonElement>? LoadProgress()
    {
        var saveDir = GetSaveProfileDir();
        if (saveDir == null)
            return null;

        return ReadJson(Path.Combine(saveDir, "progress.save"));
    }

    /// <summary>
    /// Auto-discover the save directory for StS2.
    /// Primary: %APPDATA%/SlayTheSpire2/steam/{steam64id}/ - pick most recently modified.
    /// Fallback: %ProgramFiles(x86)%/Steam/userdata/*/2868840/remote/.
    /// </summary>
    private static string? DiscoverSaveDir()
    {
        // Primary: %APPDATA%/SlayTheSpire2/steam/<steam64id>/
        var appdata = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        var appdataBase = Path.Combine(appdata, "SlayTheSpire2", "steam");

        var result = PickNewestDir(appdataBase, "*", "appdata");
        if (result != null)
            return result;

        // Fallback: Steam userdata cloud sync copy
        var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86);
        if (string.IsNullOrEmpty(programFiles))
            programFiles = @"C:\Program Files (x86)";

        var steamBase = Path.Combine(programFiles, "Steam", "userdata");

        if (Directory.Exists(steamBase))
        {
            try
            {
                var candidates = Directory.GetDirectories(steamBase)
                    .Select(d => Path.Combine(d, "2868840", "remote"))
                    .Where(Directory.Exists)
                    .ToList();

                result = PickNewest(candidates, "steam userdata");
                if (result != null)
                    return result;
            }
            catch (Exception ex)
            {
                ModEntry.Log("SaveFileReader: error scanning " + steamBase + ": " + ex.Message);
            }
        }

        ModEntry.Log("SaveFileReader: no save directory found");
        return null;
    }

    /// <summary>
    /// List subdirectories matching a pattern, return the newest (or only) one.
    /// </summary>
    private static string? PickNewestDir(string parentDir, string pattern, string label)
    {
        if (!Directory.Exists(parentDir))
            return null;

        try
        {
            var candidates = Directory.GetDirectories(parentDir, pattern).ToList();
            return PickNewest(candidates, label);
        }
        catch (Exception ex)
        {
            ModEntry.Log("SaveFileReader: error scanning " + parentDir + ": " + ex.Message);
            return null;
        }
    }

    /// <summary>
    /// From a list of directory candidates, return the single entry or the most recently modified.
    /// </summary>
    private static string? PickNewest(List<string> candidates, string label)
    {
        if (candidates.Count == 0)
            return null;

        if (candidates.Count == 1)
        {
            ModEntry.Log("SaveFileReader: found save dir (" + label + ", single): " + candidates[0]);
            return candidates[0];
        }

        var best = candidates.OrderByDescending(d => Directory.GetLastWriteTimeUtc(d)).First();
        ModEntry.Log("SaveFileReader: found save dir (" + label + ", newest of " + candidates.Count + "): " + best);
        return best;
    }

    /// <summary>
    /// Return both modded and unmodded history directories that exist on disk.
    /// </summary>
    private static List<string> GetHistoryDirs()
    {
        var dirs = new List<string>(2);
        if (_moddedSaves != null)
        {
            var dir = Path.Combine(_moddedSaves, "history");
            if (Directory.Exists(dir))
                dirs.Add(dir);
        }
        if (_unmoddedSaves != null)
        {
            var dir = Path.Combine(_unmoddedSaves, "history");
            if (Directory.Exists(dir))
                dirs.Add(dir);
        }
        return dirs;
    }

    /// <summary>
    /// Safely read and parse a JSON file. Returns null on any error.
    /// Uses FileShare.Read to avoid locking issues with the game.
    /// </summary>
    private static Dictionary<string, JsonElement>? ReadJson(string path)
    {
        try
        {
            using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
            using var doc = JsonDocument.Parse(stream);
            var result = new Dictionary<string, JsonElement>();
            foreach (var prop in doc.RootElement.EnumerateObject())
            {
                result[prop.Name] = prop.Value.Clone();
            }
            return result;
        }
        catch (FileNotFoundException)
        {
            return null;
        }
        catch (IOException ex)
        {
            ModEntry.Log("SaveFileReader: IO error reading " + path + ": " + ex.Message);
            return null;
        }
        catch (JsonException ex)
        {
            ModEntry.Log("SaveFileReader: JSON parse error in " + path + ": " + ex.Message);
            return null;
        }
        catch (Exception ex)
        {
            ModEntry.Log("SaveFileReader: unexpected error reading " + path + ": " + ex.Message);
            return null;
        }
    }
}
