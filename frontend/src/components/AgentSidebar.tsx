import { useEffect, useState } from "react";
import type { Agent } from "../types";
import { AgentProfile } from "./AgentProfile";

const API_URL = "http://localhost:8000/api";

export function AgentSidebar() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/agents`)
      .then((r) => r.json())
      .then((data) => {
        setAgents(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load agents:", err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="agent-sidebar">
      <div className="agent-sidebar-header">
        <h2>Team</h2>
      </div>
      <div className="agent-sidebar-list">
        {loading ? (
          <div className="agent-loading">Loading team...</div>
        ) : agents.length === 0 ? (
          <div className="agent-empty">No agents registered</div>
        ) : (
          agents.map((agent) => (
            <AgentProfile key={agent.id} agent={agent} />
          ))
        )}
      </div>
    </div>
  );
}
