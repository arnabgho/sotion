import { useEffect, useRef, useCallback, useState } from "react";
import type { WebSocketMessage } from "../types";

const WS_URL = "ws://localhost:8000/ws";

export function useWebSocket(channelId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!channelId) return;

    const ws = new WebSocket(`${WS_URL}/${channelId}`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (event) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data);
        if (data.type === "message") {
          setMessages((prev) => [...prev, data]);
        }
      } catch {
        // ignore parse errors
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
      setConnected(false);
    };
  }, [channelId]);

  const sendMessage = useCallback(
    (content: string, senderName = "Human") => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({ content, sender_name: senderName })
        );
      }
    },
    []
  );

  const clearMessages = useCallback(() => setMessages([]), []);

  return { messages, connected, sendMessage, clearMessages };
}
