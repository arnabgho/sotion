"""Message bus module for decoupled channel-agent communication."""

from sotion.bus.events import InboundMessage, OutboundMessage
from sotion.bus.queue import MessageBus

__all__ = ["MessageBus", "InboundMessage", "OutboundMessage"]
