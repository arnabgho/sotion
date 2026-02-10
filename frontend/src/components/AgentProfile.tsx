import { useState } from "react";
import type { Agent } from "../types";

const API_URL = "http://localhost:8000/api";

interface Props {
  agent: Agent;
  onDMCreated?: (dmChannel: any) => void;
}

const STATUS_COLORS: Record<string, string> = {
  active: "#2ecc71",
  busy: "#f39c12",
  idle: "#95a5a6",
  warning: "#e67e22",
  fired: "#e74c3c",
};

export function AgentProfile({ agent, onDMCreated }: Props) {
  const statusColor = STATUS_COLORS[agent.status] || "#95a5a6";
  const scorePercent = Math.round(agent.performance_score * 100);
  const [creating, setCreating] = useState(false);

  const handleStartDM = async () => {
    setCreating(true);
    try {
      const response = await fetch(`${API_URL}/dms`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent_id: agent.id }),
      });

      if (!response.ok) {
        throw new Error("Failed to create DM");
      }

      const dm = await response.json();

      // Notify parent component to select the DM
      if (onDMCreated) {
        onDMCreated(dm);
      }
    } catch (error) {
      console.error("Failed to start DM:", error);
      alert("Failed to start DM with agent");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="agent-profile">
      <div className="agent-avatar">{agent.avatar_emoji}</div>
      <div className="agent-info">
        <div className="agent-name">{agent.name}</div>
        <div className="agent-role">{agent.role}</div>
        <div className="agent-status" style={{ color: statusColor }}>
          {agent.status}
        </div>
      </div>
      <div className="agent-stats">
        <div className="agent-stat">
          <span className="stat-label">Performance</span>
          <div className="stat-bar">
            <div
              className="stat-bar-fill"
              style={{
                width: `${scorePercent}%`,
                backgroundColor:
                  scorePercent >= 70
                    ? "#2ecc71"
                    : scorePercent >= 40
                    ? "#f39c12"
                    : "#e74c3c",
              }}
            />
          </div>
          <span className="stat-value">{scorePercent}%</span>
        </div>
        <div className="agent-stat">
          <span className="stat-label">Salary</span>
          <span className="stat-value">{agent.salary_balance} credits</span>
        </div>
        <div className="agent-stat">
          <span className="stat-label">Token Budget</span>
          <span className="stat-value">{agent.token_budget.toLocaleString()}</span>
        </div>
      </div>
      <button
        className="btn-start-dm"
        onClick={handleStartDM}
        disabled={creating}
      >
        {creating ? "Creating..." : "Message"}
      </button>
    </div>
  );
}
