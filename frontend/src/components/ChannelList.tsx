import { useEffect, useState } from "react";
import type { Channel } from "../types";

const API_URL = "http://localhost:8000/api";

interface Props {
  selectedChannel: Channel | null;
  onSelectChannel: (channel: Channel) => void;
}

export function ChannelList({ selectedChannel, onSelectChannel }: Props) {
  const [channels, setChannels] = useState<Channel[]>([]);

  useEffect(() => {
    fetch(`${API_URL}/channels`)
      .then((r) => r.json())
      .then(setChannels)
      .catch(console.error);
  }, []);

  return (
    <div className="channel-list">
      <div className="channel-list-header">
        <h2>Channels</h2>
      </div>
      <div className="channel-list-items">
        {channels.map((ch) => (
          <button
            key={ch.id}
            className={`channel-item ${selectedChannel?.id === ch.id ? "active" : ""}`}
            onClick={() => onSelectChannel(ch)}
          >
            <span className="channel-hash">#</span>
            <span className="channel-name">{ch.name}</span>
          </button>
        ))}
        {channels.length === 0 && (
          <div className="channel-empty">No channels yet</div>
        )}
      </div>
    </div>
  );
}
