using System;
using HarmonyLib;
using MegaCrit.Sts2.Core.Modding;

namespace StS2Tracker;

[ModInitializer(nameof(Initialize))]
public static class ModEntry
{
    public static Harmony? HarmonyInstance { get; private set; }

    public const int DashboardPort = 3000;

    public static void Initialize()
    {
        try
        {
            Log("StS2Tracker v0.1.0 initializing...");

            HarmonyInstance = new Harmony("com.jhol.sts2tracker");
            HarmonyInstance.PatchAll(typeof(ModEntry).Assembly);

            CombatTracker.Initialize();
            StatusOverlay.Create(DashboardPort);

            Log("StS2Tracker initialized successfully. Patches applied: " +
                HarmonyInstance.GetPatchedMethods().GetEnumerator().MoveNext());
        }
        catch (Exception ex)
        {
            Log("ERROR initializing StS2Tracker: " + ex);
        }
    }

    public static void Log(string message)
    {
        // Uses Godot's built-in logging which shows in the game log files
        Godot.GD.Print("[StS2Tracker] " + message);
    }
}
