import { useState } from "react";
import type { Channel } from "./types";
import { ChannelList } from "./components/ChannelList";
import { ChatView } from "./components/ChatView";
import { AgentSidebar } from "./components/AgentSidebar";
import { DocumentList } from "./components/DocumentList";
import { TaskList } from "./components/TaskList";
import { ToastContainer } from "./components/Toast";
import { useToast } from "./hooks/useToast";
import "./App.css";

function App() {
  const [selectedChannel, setSelectedChannel] = useState<Channel | null>(null);
  const { toasts, closeToast } = useToast();

  return (
    <div className="app">
      <div className="sidebar-left">
        <div className="app-header">
          <h1>Sotion</h1>
        </div>
        <ChannelList
          selectedChannel={selectedChannel}
          onSelectChannel={setSelectedChannel}
        />
      </div>

      <div className="main-content">
        {selectedChannel ? (
          <>
            <ChatView channel={selectedChannel} />
            <div className="channel-details">
              <DocumentList channelId={selectedChannel.id} />
              <TaskList channelId={selectedChannel.id} />
            </div>
          </>
        ) : (
          <div className="no-channel">
            <h2>Welcome to Sotion</h2>
            <p>Select a channel to start chatting with your AI team.</p>
          </div>
        )}
      </div>

      <div className="sidebar-right">
        <AgentSidebar onSelectChannel={setSelectedChannel} />
      </div>

      <ToastContainer toasts={toasts} onClose={closeToast} />
    </div>
  );
}

export default App;
