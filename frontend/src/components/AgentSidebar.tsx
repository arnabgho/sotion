import { useEffect, useState } from "react";
import type { Agent, Channel } from "../types";
import { AgentProfile } from "./AgentProfile";

const API_URL = "http://localhost:8000/api";

interface Props {
  onSelectChannel?: (channel: Channel) => void;
}

export function AgentSidebar({ onSelectChannel }: Props) {
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

  const handleDMCreated = (dmChannel: any) => {
    // Notify parent to select the newly created DM
    if (onSelectChannel) {
      onSelectChannel(dmChannel as Channel);
    }
  };

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
            <AgentProfile
              key={agent.id}
              agent={agent}
              onDMCreated={handleDMCreated}
            />
          ))
        )}
      </div>
    </div>
  );
}
