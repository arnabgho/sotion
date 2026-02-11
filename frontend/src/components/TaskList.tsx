import { useEffect, useState } from "react";
import type { Task, Agent } from "../types";

const API_URL = "http://localhost:8000/api";

interface Props {
  channelId: string;
}

const PRIORITY_LABELS: Record<number, string> = {
  0: "Low",
  1: "Medium",
  2: "High",
};

const PRIORITY_COLORS: Record<number, string> = {
  0: "#95a5a6",
  1: "#f39c12",
  2: "#e74c3c",
};

export function TaskList({ channelId }: Props) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string | null>(null);

  const refreshTasks = () => {
    Promise.all([
      fetch(`${API_URL}/channels/${channelId}/tasks`).then((r) => r.json()),
      fetch(`${API_URL}/agents`).then((r) => r.json()),
    ])
      .then(([tasksData, agentsData]) => {
        setTasks(tasksData);
        setAgents(agentsData);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load tasks:", err);
        setLoading(false);
      });
  };

  useEffect(() => {
    refreshTasks();
  }, [channelId]);

  const getAgentName = (agentId: string | null) => {
    if (!agentId) return "Unassigned";
    const agent = agents.find((a) => a.id === agentId);
    return agent ? agent.name : "Unknown";
  };

  const filteredTasks = filterStatus
    ? tasks.filter((t) => t.status === filterStatus)
    : tasks;

  const handleComplete = async (taskId: string) => {
    const qualityInput = prompt("Enter quality score (0.0-1.0):");
    const quality = qualityInput ? parseFloat(qualityInput) : null;

    if (quality !== null && (quality < 0 || quality > 1)) {
      alert("Quality score must be between 0.0 and 1.0");
      return;
    }

    try {
      const response = await fetch(`${API_URL}/tasks/${taskId}/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quality_score: quality }),
      });

      if (response.ok) {
        refreshTasks();
      } else {
        throw new Error("Failed to complete task");
      }
    } catch (error) {
      console.error("Failed to complete task:", error);
      alert("Failed to complete task");
    }
  };

  return (
    <div className="task-panel">
      <div className="task-panel-header">
        <h3>Tasks</h3>
        <select
          className="task-status-filter"
          value={filterStatus || ""}
          onChange={(e) => setFilterStatus(e.target.value || null)}
        >
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
        </select>
        <span className="task-count">{filteredTasks.length}</span>
      </div>

      {loading ? (
        <div className="task-loading">Loading tasks...</div>
      ) : filteredTasks.length === 0 ? (
        <div className="task-empty">
          {tasks.length === 0 ? (
            <>
              <p>No tasks yet</p>
              <p className="task-hint">Agents can create tasks using create_task tool</p>
            </>
          ) : (
            <p>No tasks match your filter</p>
          )}
        </div>
      ) : (
        <div className="task-list">
          {filteredTasks.map((task) => (
            <div key={task.id} className={`task-item status-${task.status}`}>
              <div className="task-header">
                <span
                  className="task-priority"
                  style={{ color: PRIORITY_COLORS[task.priority] }}
                >
                  {PRIORITY_LABELS[task.priority]}
                </span>
                <span className="task-title">{task.title}</span>
                <span className="task-status-badge">{task.status.replace("_", " ")}</span>
              </div>
              {task.description && (
                <div className="task-description">{task.description}</div>
              )}
              <div className="task-meta">
                <span>Assigned: {getAgentName(task.assigned_to)}</span>
                {task.quality_score !== null && (
                  <span className="task-quality">
                    Quality: {(task.quality_score * 100).toFixed(0)}%
                  </span>
                )}
                {task.status !== "completed" && (
                  <button
                    className="btn-complete-task"
                    onClick={() => handleComplete(task.id)}
                  >
                    Complete
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
