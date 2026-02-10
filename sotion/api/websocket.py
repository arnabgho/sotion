"""WebSocket handler for real-time message streaming."""

import asyncio
import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from sotion.bus.events import InboundMessage, OutboundMessage
from sotion.bus.queue import MessageBus


class ConnectionManager:
    """Manages active WebSocket connections per channel."""

    def __init__(self):
        # channel_id -> list of websockets
        self.connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel_id: str) -> None:
        await websocket.accept()
        if channel_id not in self.connections:
            self.connections[channel_id] = []
        self.connections[channel_id].append(websocket)
        logger.info(f"WebSocket connected to channel {channel_id}")

    def disconnect(self, websocket: WebSocket, channel_id: str) -> None:
        if channel_id in self.connections:
            self.connections[channel_id] = [
                ws for ws in self.connections[channel_id] if ws != websocket
            ]
            if not self.connections[channel_id]:
                del self.connections[channel_id]
        logger.info(f"WebSocket disconnected from channel {channel_id}")

    async def broadcast_to_channel(self, channel_id: str, data: dict[str, Any]) -> None:
        """Send a message to all WebSocket connections in a channel."""
        if channel_id not in self.connections:
            return
        payload = json.dumps(data, default=str)
        dead = []
        for ws in self.connections[channel_id]:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, channel_id)

    async def broadcast_outbound(self, msg: OutboundMessage) -> None:
        """Broadcast an outbound message to the appropriate channel."""
        data = {
            "type": "message",
            "channel_id": msg.chat_id,
            "content": msg.content,
            "sender_type": "agent",
            "sender_name": msg.sender_agent_name,
            "sender_role": msg.sender_agent_role,
            "sender_agent_id": msg.sender_agent_id,
            "message_type": msg.message_type,
        }
        await self.broadcast_to_channel(msg.chat_id, data)


# Global connection manager
ws_manager = ConnectionManager()


async def websocket_endpoint(
    websocket: WebSocket,
    channel_id: str,
    bus: MessageBus,
) -> None:
    """Handle a WebSocket connection for a channel."""
    await ws_manager.connect(websocket, channel_id)

    try:
        while True:
            # Receive messages from the client
            data = await websocket.receive_text()
            payload = json.loads(data)

            content = payload.get("content", "")
            sender_name = payload.get("sender_name", "Human")
            mentions = payload.get("mentions", [])

            # Determine message type
            message_type = "chat"
            if "@here" in content:
                message_type = "standup_request"
            elif content.startswith("/"):
                message_type = "command"

            # Publish to bus
            msg = InboundMessage(
                channel="web",
                sender_id=sender_name,
                chat_id=channel_id,
                content=content,
                message_type=message_type,
                mentions=mentions,
            )
            await bus.publish_inbound(msg)

            # Echo the human message back to all clients in the channel
            echo = {
                "type": "message",
                "channel_id": channel_id,
                "content": content,
                "sender_type": "human",
                "sender_name": sender_name,
                "message_type": message_type,
            }
            await ws_manager.broadcast_to_channel(channel_id, echo)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket, channel_id)
