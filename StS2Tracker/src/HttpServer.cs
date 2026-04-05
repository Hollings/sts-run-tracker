using System;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace StS2Tracker;

public static class HttpServer
{
    public const int Port = 52323;

    private static HttpListener? _listener;
    private static Thread? _listenerThread;
    private static Thread? _mainThread;
    private static volatile bool _running;
    private static string? _webRoot;

    // Route handler delegates (set by ApiHandlers during init)
    public static Func<string>? OnApiLive;
    public static Func<string>? OnApiRuns;
    public static Func<string, string>? OnApiRunDetail; // param: filename
    public static Func<string>? OnApiProgress;
    public static Func<HttpListenerContext, Task>? OnWebSocket;

    /// <summary>
    /// Call from ModEntry.Initialize() (which runs on main thread) to capture
    /// the main thread reference for RunOnMainThread.
    /// </summary>
    public static void CaptureMainThread()
    {
        _mainThread = Thread.CurrentThread;
    }

    public static void Start()
    {
        if (_running) return;

        _webRoot = Path.Combine(
            Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location)!,
            "web");

        _listener = new HttpListener();
        _listener.Prefixes.Add($"http://localhost:{Port}/");
        _listener.Start();
        _running = true;

        _listenerThread = new Thread(ListenLoop)
        {
            IsBackground = true,
            Name = "StS2Tracker-HTTP"
        };
        _listenerThread.Start();

        ModEntry.Log($"HTTP server started on port {Port}");
    }

    public static void Stop()
    {
        _running = false;
        _listener?.Stop();
        _listener?.Close();
        ModEntry.Log("HTTP server stopped");
    }

    private static void ListenLoop()
    {
        while (_running)
        {
            try
            {
                var context = _listener!.GetContext();
                _ = Task.Run(() => HandleRequest(context));
            }
            catch (HttpListenerException) when (!_running)
            {
                // Expected on shutdown
            }
            catch (ObjectDisposedException) when (!_running)
            {
                // Expected on shutdown
            }
            catch (Exception ex)
            {
                ModEntry.Log("HTTP listen error: " + ex.Message);
            }
        }
    }

    private static void HandleRequest(HttpListenerContext context)
    {
        var request = context.Request;
        var response = context.Response;

        try
        {
            AddCorsHeaders(response);

            if (request.HttpMethod == "OPTIONS")
            {
                response.StatusCode = 204;
                response.Close();
                return;
            }

            string path = request.Url?.AbsolutePath ?? "/";
            RouteRequest(path, context);
        }
        catch (Exception ex)
        {
            ModEntry.Log("Request handler error: " + ex.Message);
            try
            {
                WriteErrorResponse(response, ex.Message, 500);
            }
            catch { }
        }
        finally
        {
            try { response.Close(); } catch { }
        }
    }

    private static void RouteRequest(string path, HttpListenerContext context)
    {
        var response = context.Response;

        if (path == "/api/live")
        {
            string json = OnApiLive?.Invoke() ?? "{\"status\":\"not_configured\"}";
            WriteJsonResponse(response, json);
        }
        else if (path == "/api/runs")
        {
            string json = OnApiRuns?.Invoke() ?? "{\"status\":\"not_configured\"}";
            WriteJsonResponse(response, json);
        }
        else if (path.StartsWith("/api/runs/") && path.Length > "/api/runs/".Length)
        {
            string filename = path.Substring("/api/runs/".Length);
            string json = OnApiRunDetail?.Invoke(filename) ?? "{\"status\":\"not_configured\"}";
            WriteJsonResponse(response, json);
        }
        else if (path == "/api/progress")
        {
            string json = OnApiProgress?.Invoke() ?? "{\"status\":\"not_configured\"}";
            WriteJsonResponse(response, json);
        }
        else if (path == "/ws")
        {
            if (context.Request.IsWebSocketRequest)
            {
                if (OnWebSocket != null)
                {
                    // Await the WebSocket handler - don't close the response in finally
                    // since the WebSocket handler manages its own lifecycle
                    OnWebSocket.Invoke(context).GetAwaiter().GetResult();
                }
                else
                {
                    WriteErrorResponse(response, "WebSocket not configured", 503);
                }
            }
            else
            {
                WriteErrorResponse(response, "WebSocket upgrade required", 400);
            }
        }
        else if (path.StartsWith("/assets/"))
        {
            ServeStaticFile(response, path);
        }
        else
        {
            // SPA fallback: serve index.html for all other paths
            ServeStaticFile(response, "/index.html");
        }
    }

    private static void ServeStaticFile(HttpListenerResponse response, string requestPath)
    {
        if (_webRoot == null)
        {
            WriteErrorResponse(response, "Web root not configured", 500);
            return;
        }

        string relativePath = requestPath.TrimStart('/');
        string filePath = Path.Combine(_webRoot, relativePath);

        // Prevent directory traversal: resolved path must be within web root
        string fullPath = Path.GetFullPath(filePath);
        string fullWebRoot = Path.GetFullPath(_webRoot);
        if (!fullPath.StartsWith(fullWebRoot, StringComparison.OrdinalIgnoreCase))
        {
            WriteErrorResponse(response, "Forbidden", 403);
            return;
        }

        if (!File.Exists(fullPath))
        {
            WriteErrorResponse(response, "Not found: " + requestPath, 404);
            return;
        }

        try
        {
            byte[] fileBytes = File.ReadAllBytes(fullPath);
            string ext = Path.GetExtension(fullPath).ToLowerInvariant();
            response.ContentType = GetMimeType(ext);
            response.StatusCode = 200;
            response.ContentLength64 = fileBytes.Length;
            response.OutputStream.Write(fileBytes, 0, fileBytes.Length);
        }
        catch (Exception ex)
        {
            WriteErrorResponse(response, "Error reading file: " + ex.Message, 500);
        }
    }

    private static string GetMimeType(string extension)
    {
        return extension switch
        {
            ".html" => "text/html; charset=utf-8",
            ".js" => "application/javascript; charset=utf-8",
            ".css" => "text/css; charset=utf-8",
            ".json" => "application/json; charset=utf-8",
            ".png" => "image/png",
            ".svg" => "image/svg+xml",
            ".ico" => "image/x-icon",
            _ => "application/octet-stream",
        };
    }

    private static void AddCorsHeaders(HttpListenerResponse response)
    {
        response.AddHeader("Access-Control-Allow-Origin", "*");
        response.AddHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
        response.AddHeader("Access-Control-Allow-Headers", "Content-Type");
    }

    internal static void WriteJsonResponse(HttpListenerResponse response, string json, int statusCode = 200)
    {
        response.StatusCode = statusCode;
        response.ContentType = "application/json; charset=utf-8";
        byte[] buffer = Encoding.UTF8.GetBytes(json);
        response.ContentLength64 = buffer.Length;
        response.OutputStream.Write(buffer, 0, buffer.Length);
    }

    internal static void WriteErrorResponse(HttpListenerResponse response, string message, int statusCode)
    {
        string json = "{\"error\":\"" + EscapeJson(message) + "\",\"code\":" + statusCode + "}";
        WriteJsonResponse(response, json, statusCode);
    }

    /// <summary>
    /// Runs a function on Godot's main thread and blocks until it completes.
    /// Required because game state can only be accessed from the main thread.
    /// </summary>
    internal static T RunOnMainThread<T>(Func<T> func)
    {
        if (Thread.CurrentThread == _mainThread)
            return func();

        var tcs = new TaskCompletionSource<T>();

        Godot.Callable.From(() =>
        {
            try
            {
                tcs.SetResult(func());
            }
            catch (Exception ex)
            {
                tcs.SetException(ex);
            }
        }).CallDeferred();

        // Block HTTP thread until main thread completes the work
        return tcs.Task.GetAwaiter().GetResult();
    }

    private static string EscapeJson(string s)
    {
        return s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n").Replace("\r", "");
    }
}
