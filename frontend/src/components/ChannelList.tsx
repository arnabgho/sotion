import { useEffect, useState } from "react";
import type { Channel } from "../types";

const API_URL = "http://localhost:8000/api";

interface Props {
  selectedChannel: Channel | null;
  onSelectChannel: (channel: Channel) => void;
}

export function ChannelList({ selectedChannel, onSelectChannel }: Props) {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/channels`)
      .then((r) => r.json())
      .then((data) => {
        setChannels(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load channels:", err);
        setLoading(false);
      });
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
              className={`channel-item ${selectedChannel?.id === ch.id ? "active" : ""}`}
              onClick={() => onSelectChannel(ch)}
            >
              <span className="channel-hash">#</span>
              <span className="channel-name">{ch.name}</span>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
