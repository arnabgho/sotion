import { useState, useRef, useEffect } from "react";
import type { Channel, WebSocketMessage, Agent } from "../types";
import { useWebSocket } from "../hooks/useWebSocket";
import { MentionInput } from "./MentionInput";
import { MarkdownMessage } from "./MarkdownMessage";

const API_URL = "http://localhost:8000/api";

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

  const getMessageTypeIcon = () => {
    if (msg.message_type === "standup_request") return "📊";
    if (msg.message_type === "command") return "⚡";
    return null;
  };

  const messageTypeIcon = getMessageTypeIcon();

  return (
    <div className={`message ${isHuman ? "message-human" : "message-agent"} ${msg.message_type ? `message-${msg.message_type}` : ""}`}>
      <div className="message-header">
        {messageTypeIcon && <span className="message-type-icon">{messageTypeIcon}</span>}
        <span className="message-sender" style={!isHuman ? { color: roleColor } : {}}>
          {msg.sender_name || "Unknown"}
        </span>
        {msg.sender_role && (
          <span className="message-role" style={{ backgroundColor: roleColor }}>
            {msg.sender_role}
          </span>
        )}
        {msg.message_type && msg.message_type !== "chat" && (
          <span className="message-type-badge">{msg.message_type.replace("_", " ")}</span>
        )}
      </div>
      <div className="message-content">
        <MarkdownMessage content={msg.content} />
      </div>
    </div>
  );
}

export function ChatView({ channel }: Props) {
  const { messages, connected, loading, sendMessage } = useWebSocket(channel.id);
  const [input, setInput] = useState("");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [pauseTarget, setPauseTarget] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch agents for @mention autocomplete
  useEffect(() => {
    fetch(`${API_URL}/agents`)
      .then((r) => r.json())
      .then(setAgents)
      .catch(console.error);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    sendMessage(trimmed);
    setInput("");
  };

  const handleEnterDM = async (agentName: string) => {
    const agent = agents.find((a) => a.name === agentName);
    if (!agent) return;

    try {
      const response = await fetch(`${API_URL}/channels/${channel.id}/pause`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ except_agent_id: agent.id }),
      });

      if (response.ok) {
        setIsPaused(true);
        setPauseTarget(agentName);
      }
    } catch (error) {
      console.error("Failed to enter 1:1 mode:", error);
    }
  };

  const handleExitDM = async () => {
    try {
      const response = await fetch(`${API_URL}/channels/${channel.id}/unpause`, {
        method: "POST",
      });

      if (response.ok) {
        setIsPaused(false);
        setPauseTarget(null);
      }
    } catch (error) {
      console.error("Failed to exit 1:1 mode:", error);
    }
  };

  return (
    <div className="chat-view">
      <div className="chat-header">
        <h2>
          {isPaused && pauseTarget ? `@ ${pauseTarget}` : `# ${channel.name}`}
        </h2>
        <div className="header-controls">
          {isPaused ? (
            <button className="btn-exit-dm" onClick={handleExitDM}>
              Exit 1:1 Mode
            </button>
          ) : (
            <select
              className="agent-selector"
              onChange={(e) => e.target.value && handleEnterDM(e.target.value)}
              value=""
            >
              <option value="">Enter 1:1 Mode...</option>
              {agents.map((agent) => (
                <option key={agent.id} value={agent.name}>
                  {agent.name} ({agent.role})
                </option>
              ))}
            </select>
          )}
          <span className={`connection-status ${connected ? "connected" : "disconnected"}`}>
            {connected ? "Connected" : "Disconnected"}
          </span>
        </div>
      </div>

      <div className="chat-messages">
        {loading ? (
          <div className="loading-messages">Loading messages...</div>
        ) : messages.length === 0 ? (
          <div className="no-messages">No messages yet. Start the conversation!</div>
        ) : (
          messages.map((msg, i) => <MessageBubble key={i} msg={msg} />)
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <button
          className="btn-here"
          onClick={() => sendMessage("@here Please share your standup updates")}
          disabled={!connected}
          title="Request standup from all agents"
        >
          @here
        </button>
        <MentionInput
          value={input}
          onChange={setInput}
          onSend={handleSend}
          agents={agents}
          placeholder={`Message #${channel.name}... (use @name to mention agents)`}
          disabled={!connected}
        />
        <button className="chat-send" onClick={handleSend} disabled={!connected}>
          Send
        </button>
      </div>
    </div>
  );
}
