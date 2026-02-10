"""Pydantic models for all database tables."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
import uuid


def _uuid() -> str:
    return str(uuid.uuid4())


class Agent(BaseModel):
    id: str = Field(default_factory=_uuid)
    name: str
    role: str
    status: str = "active"
    avatar_emoji: str = "\U0001f916"
    model: str = "anthropic/claude-sonnet-4-5-20250929"
    system_prompt: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    token_budget: int = 100000
    salary_balance: int = 0
    performance_score: float = 0.5
    learnings: str = ""
    principles: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Channel(BaseModel):
    id: str = Field(default_factory=_uuid)
    name: str
    description: str | None = None
    channel_type: str = "project"  # "project" or "dm"
    dm_participant_agent_id: str | None = None  # Set when channel_type="dm"
    is_archived: bool = False
    created_at: datetime = Field(default_factory=datetime.now)


class ChannelMember(BaseModel):
    channel_id: str
    agent_id: str
    is_paused: bool = False
    joined_at: datetime = Field(default_factory=datetime.now)


class Message(BaseModel):
    id: str = Field(default_factory=_uuid)
    channel_id: str
    sender_id: str | None = None
    sender_type: str  # 'human', 'agent', 'system'
    sender_name: str | None = None
    content: str
    message_type: str = "chat"
    mentions: list[str] = Field(default_factory=list)
    owner_agent_id: str | None = None
    reply_to: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class AgentUpdate(BaseModel):
    id: str = Field(default_factory=_uuid)
    agent_id: str
    channel_id: str
    summary: str
    created_at: datetime = Field(default_factory=datetime.now)


class Document(BaseModel):
    id: str = Field(default_factory=_uuid)
    channel_id: str
    title: str
    content: str = ""
    doc_type: str = "note"
    status: str = "active"
    created_by: str | None = None
    last_edited_by: str | None = None
    last_accessed_at: datetime = Field(default_factory=datetime.now)
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class DocumentVersion(BaseModel):
    id: str = Field(default_factory=_uuid)
    document_id: str
    version: int
    content: str
    edited_by: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class Task(BaseModel):
    id: str = Field(default_factory=_uuid)
    channel_id: str | None = None
    document_id: str | None = None
    title: str
    description: str | None = None
    assigned_to: str | None = None
    status: str = "pending"
    priority: int = 0
    completed_at: datetime | None = None
    quality_score: float | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PerformanceLog(BaseModel):
    id: str = Field(default_factory=_uuid)
    agent_id: str
    event_type: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class Reward(BaseModel):
    id: str = Field(default_factory=_uuid)
    agent_id: str
    reward_type: str
    amount: int
    reason: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
