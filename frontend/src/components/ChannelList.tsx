import { useEffect, useState } from "react";
import type { Channel } from "../types";

const API_URL = "http://localhost:8000/api";

interface ChannelWithStatus extends Channel {
  is_dm: boolean;
  dm_agent_name?: string;
}

interface Props {
  selectedChannel: Channel | null;
  onSelectChannel: (channel: Channel) => void;
}

export function ChannelList({ selectedChannel, onSelectChannel }: Props) {
  const [channels, setChannels] = useState<ChannelWithStatus[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchChannelsWithStatus = async () => {
      setLoading(true);
      try {
        const channelsRes = await fetch(`${API_URL}/channels`);
        const channelsData: Channel[] = await channelsRes.json();

        // Check pause status for each channel
        const channelsWithStatus = await Promise.all(
          channelsData.map(async (ch: Channel) => {
            try {
              const membersRes = await fetch(`${API_URL}/channels/${ch.id}/members`);
              const members = await membersRes.json();

              const pausedCount = members.filter((m: any) => m.is_paused).length;
              const is_dm = pausedCount === members.length - 1; // All but one paused
              const dm_agent_name = is_dm
                ? members.find((m: any) => !m.is_paused)?.agent_name
                : undefined;

              return { ...ch, is_dm, dm_agent_name };
            } catch (error) {
              console.error(`Failed to fetch members for channel ${ch.id}:`, error);
              return { ...ch, is_dm: false };
            }
          })
        );

        setChannels(channelsWithStatus);
      } catch (err) {
        console.error("Failed to load channels:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchChannelsWithStatus();
  }, []);

  return (
    <div className="channel-list">
      <div className="channel-list-header">
        <h2>Channels</h2>
      </div>
      <div className="channel-list-items">
        {loading ? (
          <div className="channel-loading">Loading channels...</div>
        ) : channels.length === 0 ? (
          <div className="channel-empty">No channels yet</div>
        ) : (
          channels.map((ch) => (
            <button
              key={ch.id}
              className={`channel-item ${selectedChannel?.id === ch.id ? "active" : ""} ${ch.is_dm ? "dm-mode" : ""}`}
              onClick={() => onSelectChannel(ch)}
            >
              <span className="channel-prefix">{ch.is_dm ? "@" : "#"}</span>
              <span className="channel-name">
                {ch.is_dm && ch.dm_agent_name ? ch.dm_agent_name : ch.name}
              </span>
              {ch.is_dm && <span className="dm-badge">1:1</span>}
            </button>
          ))
        )}
      </div>
    </div>
  );
}
