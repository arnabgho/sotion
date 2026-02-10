"""Event types for the message bus."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class InboundMessage:
    """Message received from a channel (web UI or system)."""

    channel: str  # 'web', 'system', 'cli'
    sender_id: str  # User identifier or agent name
    chat_id: str  # Channel UUID
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    media: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Sotion extensions
    message_type: str = "chat"  # 'chat', 'standup_request', 'standup_response', 'command'
    mentions: list[str] = field(default_factory=list)  # Agent names mentioned with @
    owner_agent_id: str | None = None  # Pre-resolved owner

    @property
    def session_key(self) -> str:
        """Unique key for session identification."""
        return f"{self.channel}:{self.chat_id}"

    @property
    def is_standup_request(self) -> bool:
        return self.message_type == "standup_request"

    @property
    def is_command(self) -> bool:
        return self.message_type == "command"


@dataclass
class OutboundMessage:
    """Message to send to a channel."""

    channel: str
    chat_id: str
    content: str
    reply_to: str | None = None
    media: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Sotion extensions
    sender_agent_id: str | None = None
    sender_agent_name: str | None = None
    sender_agent_role: str | None = None
    message_type: str = "chat"
