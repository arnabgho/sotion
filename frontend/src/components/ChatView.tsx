import { useState, useRef, useEffect } from "react";
import type { Channel, WebSocketMessage } from "../types";
import { useWebSocket } from "../hooks/useWebSocket";

interface Props {
  channel: Channel;
}

const ROLE_COLORS: Record<string, string> = {
  coordinator: "#e74c3c",
  developer: "#3498db",
  reviewer: "#2ecc71",
  planner: "#f39c12",
  researcher: "#9b59b6",
  documenter: "#1abc9c",
};

function MessageBubble({ msg }: { msg: WebSocketMessage }) {
  const isHuman = msg.sender_type === "human";
  const roleColor = msg.sender_role
    ? ROLE_COLORS[msg.sender_role] || "#95a5a6"
    : "#95a5a6";

  return (
    <div className={`message ${isHuman ? "message-human" : "message-agent"}`}>
      <div className="message-header">
        <span className="message-sender" style={!isHuman ? { color: roleColor } : {}}>
          {msg.sender_name || "Unknown"}
        </span>
        {msg.sender_role && (
          <span className="message-role" style={{ backgroundColor: roleColor }}>
            {msg.sender_role}
          </span>
        )}
      </div>
      <div className="message-content">{msg.content}</div>
    </div>
  );
}

export function ChatView({ channel }: Props) {
  const { messages, connected, sendMessage } = useWebSocket(channel.id);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    sendMessage(trimmed);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-view">
      <div className="chat-header">
        <h2># {channel.name}</h2>
        <span className={`connection-status ${connected ? "connected" : "disconnected"}`}>
          {connected ? "Connected" : "Disconnected"}
        </span>
      </div>

      <div className="chat-messages">
        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <textarea
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Message #${channel.name}...`}
          rows={1}
        />
        <button className="chat-send" onClick={handleSend} disabled={!connected}>
          Send
        </button>
      </div>
    </div>
  );
}
