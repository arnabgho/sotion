"""Channel manager: handles pause/unpause and standup coordination."""

import asyncio
from typing import Any

from loguru import logger

from sotion.bus.events import OutboundMessage
from sotion.bus.queue import MessageBus
from sotion.channels.base import BaseChannel
from sotion.channels.web_channel import WebChannel
from sotion.config.schema import Config
from sotion.db.queries import DBQueries
from sotion.db.models import AgentUpdate


class ChannelManager:
    """Manages the web channel and channel operations."""

    def __init__(self, config: Config, bus: MessageBus, db: DBQueries):
        self.config = config
        self.bus = bus
        self.db = db
        self.channels: dict[str, BaseChannel] = {}
        self._dispatch_task: asyncio.Task | None = None

        # Initialize web channel
        self.channels["web"] = WebChannel(config, bus)

    async def start_all(self) -> None:
        """Start all channels and the outbound dispatcher."""
        self._dispatch_task = asyncio.create_task(self.bus.dispatch_outbound())
        for name, channel in self.channels.items():
            logger.info(f"Starting {name} channel...")
            await channel.start()

    async def stop_all(self) -> None:
        """Stop all channels."""
        if self._dispatch_task:
            self._dispatch_task.cancel()
        for name, channel in self.channels.items():
            await channel.stop()

    async def pause_all_except(self, channel_id: str, agent_name: str) -> str:
        """Pause all agents except one (1:1 mode)."""
        agent = await self.db.get_agent_by_name(agent_name)
        if not agent:
            return f"Agent '{agent_name}' not found"
        await self.db.pause_all_except(channel_id, agent.id)
        return f"All agents paused except {agent_name}. Use /unpause-all to restore."

    async def unpause_all(self, channel_id: str) -> str:
        """Unpause all agents in a channel."""
        await self.db.unpause_all(channel_id)
        return "All agents unpaused."

    async def get_standup_reports(self, channel_id: str) -> list[dict[str, Any]]:
        """Get recent updates from all active agents in a channel."""
        members = await self.db.get_channel_members(channel_id, include_paused=False)
        reports = []
        for m in members:
            agent = await self.db.get_agent(m.agent_id)
            if not agent:
                continue
            updates = await self.db.get_agent_updates(m.agent_id, channel_id, limit=5)
            reports.append({
                "agent_name": agent.name,
                "agent_role": agent.role,
                "updates": [u.summary for u in updates],
            })
        return reports
