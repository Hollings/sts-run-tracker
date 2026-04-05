using System;
using System.Collections.Generic;
using System.Net;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace StS2Tracker;

public static class WebSocketManager
{
    private static readonly List<WebSocket> _clients = new();
    private static readonly object _lock = new();

    public static async Task HandleWebSocket(HttpListenerContext context)
    {
        WebSocket ws;
        try
        {
            var wsContext = await context.AcceptWebSocketAsync(null);
            ws = wsContext.WebSocket;
        }
        catch (Exception ex)
        {
            ModEntry.Log("WebSocket accept failed: " + ex.Message);
            context.Response.StatusCode = 500;
            context.Response.Close();
            return;
        }

        lock (_lock) { _clients.Add(ws); }
        ModEntry.Log($"WebSocket connected ({ClientCount} total)");

        // Send initial snapshot so the client doesn't have to poll
        try
        {
            string? msg = BuildCombatUpdateMessage();
            if (msg != null)
                await SendAsync(ws, msg);
        }
        catch { /* ignore send failure on initial data */ }

        await ReceiveLoop(ws);
    }

    public static async Task BroadcastUpdate()
    {
        string? msg = BuildCombatUpdateMessage();
        if (msg == null) return;

        List<WebSocket> snapshot;
        lock (_lock) { snapshot = new List<WebSocket>(_clients); }

        List<WebSocket>? dead = null;
        foreach (var ws in snapshot)
        {
            try
            {
                if (ws.State == WebSocketState.Open)
                    await SendAsync(ws, msg);
                else
                    (dead ??= new()).Add(ws);
            }
            catch { (dead ??= new()).Add(ws); }
        }

        if (dead != null)
        {
            lock (_lock) { foreach (var ws in dead) _clients.Remove(ws); }
        }
    }

    private static int ClientCount { get { lock (_lock) return _clients.Count; } }

    private static async Task ReceiveLoop(WebSocket ws)
    {
        var buffer = new byte[1024];
        try
        {
            while (ws.State == WebSocketState.Open)
            {
                var result = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
                if (result.MessageType == WebSocketMessageType.Close)
                    break;
                if (result.MessageType == WebSocketMessageType.Text)
                {
                    string text = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    if (text == "ping")
                        await SendAsync(ws, "{\"type\":\"pong\"}");
                }
            }
        }
        catch { /* connection lost */ }
        finally
        {
            lock (_lock) { _clients.Remove(ws); }
            ModEntry.Log($"WebSocket disconnected ({ClientCount} total)");
            try { ws.Dispose(); } catch { }
        }
    }

    private static async Task SendAsync(WebSocket ws, string message)
    {
        byte[] bytes = Encoding.UTF8.GetBytes(message);
        await ws.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, CancellationToken.None);
    }

    /// <summary>
    /// Build a complete combat_update WebSocket message, or null if no data is available.
    /// </summary>
    private static string? BuildCombatUpdateMessage()
    {
        try
        {
            var tracker = CombatTracker.GetSnapshot();
            var save = SaveFileReader.LoadCurrentRun();
            string? merged = MergeEngine.MergeLiveRun(tracker, save);
            if (merged == null) return null;
            return "{\"type\":\"combat_update\",\"data\":" + merged + "}";
        }
        catch (Exception ex)
        {
            ModEntry.Log("Error building merged data: " + ex.Message);
            return null;
        }
    }
}
