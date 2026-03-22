import { useEffect, useRef, useState, useCallback } from "react";
import type { MergedLiveData, WSMessage } from "../utils/types";

interface UseWebSocketResult {
  data: MergedLiveData | null;
  connected: boolean;
  error: string | null;
}

export function useWebSocket(url?: string): UseWebSocketResult {
  const [data, setData] = useState<MergedLiveData | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const wsUrl =
    url ||
    `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws`;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data);
          if (msg.type === "combat_update" && msg.data) {
            setData(msg.data as MergedLiveData);
          }
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        // Reconnect after 3 seconds
        reconnectTimerRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        setError("WebSocket connection error");
        ws.close();
      };
    } catch {
      setError("Failed to create WebSocket connection");
      reconnectTimerRef.current = setTimeout(connect, 3000);
    }
  }, [wsUrl]);

  useEffect(() => {
    connect();

    // Ping every 30 seconds to keep alive
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send("ping");
      }
    }, 30000);

    return () => {
      clearInterval(pingInterval);
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { data, connected, error };
}
