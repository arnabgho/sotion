import { useEffect, useState } from "react";
import type { Agent } from "../types";
import { AgentProfile } from "./AgentProfile";

const API_URL = "http://localhost:8000/api";

export function AgentSidebar() {
  const [agents, setAgents] = useState<Agent[]>([]);

  useEffect(() => {
    fetch(`${API_URL}/agents`)
      .then((r) => r.json())
      .then(setAgents)
      .catch(console.error);
  }, []);

  return (
    <div className="agent-sidebar">
      <div className="agent-sidebar-header">
        <h2>Team</h2>
      </div>
      <div className="agent-sidebar-list">
        {agents.map((agent) => (
          <AgentProfile key={agent.id} agent={agent} />
        ))}
        {agents.length === 0 && (
          <div className="agent-empty">No agents registered</div>
        )}
      </div>
    </div>
  );
}
