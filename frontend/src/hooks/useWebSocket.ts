import { useEffect, useRef, useCallback, useState } from "react";
import type { WebSocketMessage } from "../types";

const WS_URL = "ws://localhost:8000/ws";
const API_URL = "http://localhost:8000/api";

export function useWebSocket(channelId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!channelId) {
      setMessages([]);
      return;
    }

    // Load message history first
    setLoading(true);
    fetch(`${API_URL}/channels/${channelId}/messages?limit=100`)
      .then((r) => r.json())
      .then((history: any[]) => {
        // Convert database messages to WebSocket message format
        const formattedHistory: WebSocketMessage[] = history.map((msg) => ({
          type: "message",
          channel_id: msg.channel_id,
          content: msg.content,
          sender_type: msg.sender_type || "agent",
          sender_name: msg.sender_name || msg.sender_id,
          sender_role: msg.metadata?.sender_role,
          sender_agent_id: msg.sender_id,
          message_type: msg.message_type || "chat",
        }));
        setMessages(formattedHistory);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load message history:", err);
        setLoading(false);
      });

    // Connect WebSocket for real-time messages
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

  return { messages, connected, loading, sendMessage, clearMessages };
}
