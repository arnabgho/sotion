import { useEffect, useState } from "react";
import type { Channel } from "../types";

const API_URL = "http://localhost:8000/api";

interface DM extends Channel {
  agent_name: string;
  agent_role: string;
  agent_avatar_emoji: string;
}

interface Props {
  selectedChannel: Channel | null;
  onSelectChannel: (channel: Channel) => void;
}

export function ChannelList({ selectedChannel, onSelectChannel }: Props) {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [dms, setDms] = useState<DM[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      try {
        const [channelsRes, dmsRes] = await Promise.all([
          fetch(`${API_URL}/channels`),
          fetch(`${API_URL}/dms`),
        ]);

        const channelsData = await channelsRes.json();
        const dmsData = await dmsRes.json();

        setChannels(channelsData);
        setDms(dmsData);
      } catch (err) {
        console.error("Failed to load channels and DMs:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchAll();

    // Poll every 5 seconds to refresh data
    const interval = setInterval(() => {
      fetchAll();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="channel-list">
      <div className="channel-list-header">
        <h2>Sotion</h2>
      </div>

      {loading ? (
        <div className="channel-loading">Loading...</div>
      ) : (
        <>
          {/* DM Section */}
          {dms.length > 0 && (
            <div className="dm-section">
              <h3 className="section-title">Direct Messages</h3>
              <div className="channel-list-items">
                {dms.map((dm) => (
                  <button
                    key={dm.id}
                    className={`channel-item dm-item ${selectedChannel?.id === dm.id ? "active" : ""}`}
                    onClick={() => onSelectChannel(dm)}
                  >
                    <span className="channel-prefix">@</span>
                    <span className="channel-name">{dm.agent_name}</span>
                    <span className="agent-role-hint">{dm.agent_role}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Channels Section */}
          <div className="channel-section">
            <h3 className="section-title">Channels</h3>
            <div className="channel-list-items">
              {channels.length === 0 ? (
                <div className="channel-empty">No channels yet</div>
              ) : (
                channels.map((ch) => (
                  <button
                    key={ch.id}
                    className={`channel-item ${selectedChannel?.id === ch.id ? "active" : ""}`}
                    onClick={() => onSelectChannel(ch)}
                  >
                    <span className="channel-prefix">#</span>
                    <span className="channel-name">{ch.name}</span>
                  </button>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
