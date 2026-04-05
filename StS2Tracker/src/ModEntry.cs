using System;
using System.Threading.Tasks;
using HarmonyLib;
using MegaCrit.Sts2.Core.Modding;

namespace StS2Tracker;

[ModInitializer(nameof(Initialize))]
public static class ModEntry
{
    public static Harmony? HarmonyInstance { get; private set; }

    public const int DashboardPort = 52323;

    public static void Initialize()
    {
        try
        {
            Log("StS2Tracker v0.1.0 initializing...");

            // Capture the main thread synchronization context before anything else
            HttpServer.CaptureMainThread();

            HarmonyInstance = new Harmony("com.jhol.sts2tracker");
            HarmonyInstance.PatchAll(typeof(ModEntry).Assembly);

            CombatTracker.Initialize();
            SaveFileReader.Initialize();

            // Wire up HTTP route handlers
            HttpServer.OnApiLive = ApiHandlers.HandleLive;
            HttpServer.OnApiRuns = ApiHandlers.HandleRunsList;
            HttpServer.OnApiRunDetail = ApiHandlers.HandleRunDetail;
            HttpServer.OnApiProgress = ApiHandlers.HandleProgress;
            HttpServer.OnWebSocket = WebSocketManager.HandleWebSocket;

            CombatTracker.OnDataChanged = () => Task.Run(WebSocketManager.BroadcastUpdate);

            HttpServer.Start();
            StatusOverlay.Create(DashboardPort);

            Log($"StS2Tracker initialized. Dashboard: http://localhost:{DashboardPort}");
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
