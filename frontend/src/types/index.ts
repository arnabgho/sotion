export interface Agent {
  id: string;
  name: string;
  role: string;
  status: string;
  avatar_emoji: string;
  model: string;
  salary_balance: number;
  performance_score: number;
  token_budget: number;
}

export interface Channel {
  id: string;
  name: string;
  description: string | null;
  channel_type: string;
  is_archived: boolean;
}

export interface Message {
  id?: string;
  channel_id: string;
  content: string;
  sender_type: "human" | "agent" | "system";
  sender_name: string | null;
  sender_role?: string | null;
  sender_agent_id?: string | null;
  message_type: string;
  created_at?: string;
}

export interface Document {
  id: string;
  channel_id: string;
  title: string;
  content: string;
  doc_type: string;
  status: string;
  version: number;
  updated_at: string;
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: string;
  priority: number;
  assigned_to: string | null;
}

export interface WebSocketMessage {
  type: "message";
  channel_id: string;
  content: string;
  sender_type: "human" | "agent" | "system";
  sender_name: string | null;
  sender_role?: string | null;
  sender_agent_id?: string | null;
  message_type: string;
}
