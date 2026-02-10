"""Web channel: bridges the FastAPI WebSocket to the message bus."""

from typing import Any

from loguru import logger

from sotion.bus.events import OutboundMessage
from sotion.bus.queue import MessageBus
from sotion.channels.base import BaseChannel
from sotion.api.websocket import ws_manager


class WebChannel(BaseChannel):
    """
    Channel implementation for the web UI.

    Inbound messages come from WebSocket (handled in api/websocket.py).
    Outbound messages are broadcast to WebSocket clients.
    """

    name = "web"

    def __init__(self, config: Any, bus: MessageBus):
        super().__init__(config, bus)
        # Subscribe to outbound messages for this channel
        self.bus.subscribe_outbound("web", self._on_outbound)

    async def start(self) -> None:
        """Web channel starts when the FastAPI server starts."""
        self._running = True
        logger.info("Web channel started")

    async def stop(self) -> None:
        self._running = False
        logger.info("Web channel stopped")

    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through WebSocket to the web UI."""
        await ws_manager.broadcast_outbound(msg)

    async def _on_outbound(self, msg: OutboundMessage) -> None:
        """Handle outbound messages from the bus."""
        await self.send(msg)
