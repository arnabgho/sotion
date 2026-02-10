"""Multi-agent orchestrator: manages N agent loops with message routing."""

import asyncio
from pathlib import Path
from typing import Any

from loguru import logger

from sotion.bus.events import InboundMessage, OutboundMessage
from sotion.bus.queue import MessageBus
from sotion.bus.router import MessageRouter
from sotion.agent.loop import AgentLoop
from sotion.providers.base import LLMProvider
from sotion.session.manager import SessionManager
from sotion.db.client import get_supabase
from sotion.db.queries import DBQueries
from sotion.db.models import Agent, Message


# Role -> allowed tools mapping
ROLE_TOOLS = {
    "coordinator": ["delegate", "message", "log_update"],
    "developer": [
        "read_file", "write_file", "edit_file", "list_dir", "exec",
        "web_search", "web_fetch", "log_update",
    ],
    "reviewer": [
        "read_file", "list_dir", "web_search", "web_fetch", "log_update",
    ],
    "planner": [
        "create_doc", "edit_doc", "query_docs", "create_task",
        "read_file", "list_dir", "log_update",
    ],
    "researcher": [
        "read_file", "list_dir", "web_search", "web_fetch",
        "query_docs", "log_update",
    ],
    "documenter": [
        "create_doc", "edit_doc", "query_docs", "read_file",
        "list_dir", "log_update",
    ],
}


class SotionOrchestrator:
    """
    Manages multiple AgentLoop instances, routes messages between them.

    One orchestrator per sotion server instance.
    """

    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        workspace: Path,
        db: DBQueries,
        coordinator_name: str = "Max",
    ):
        self.bus = bus
        self.provider = provider
        self.workspace = workspace
        self.db = db
        self.router = MessageRouter(coordinator_name=coordinator_name)
        self.agents: dict[str, AgentLoop] = {}
        self.agent_configs: dict[str, Agent] = {}  # name -> DB agent record
        self._running = False

    async def register_agent(self, agent_config: Agent) -> AgentLoop:
        """
        Create and register an AgentLoop for an agent.

        Args:
            agent_config: Agent configuration from the database.

        Returns:
            The created AgentLoop.
        """
        model = agent_config.model or self.provider.get_default_model()

        loop = AgentLoop(
            bus=self.bus,
            provider=self.provider,
            workspace=self.workspace,
            model=model,
        )

        # Configure tools based on role
        allowed_tools = ROLE_TOOLS.get(agent_config.role, [])
        self._configure_tools(loop, agent_config, allowed_tools)

        self.agents[agent_config.name] = loop
        self.agent_configs[agent_config.name] = agent_config

        logger.info(
            f"Registered agent: {agent_config.name} "
            f"(role={agent_config.role}, model={model})"
        )
        return loop

    def _configure_tools(
        self, loop: AgentLoop, agent_config: Agent, allowed_tools: list[str]
    ) -> None:
        """Remove tools not in the agent's allowed list."""
        all_tool_names = list(loop.tools.tool_names)
        for tool_name in all_tool_names:
            if tool_name not in allowed_tools:
                loop.tools.unregister(tool_name)

    async def get_active_agents(self, channel_id: str) -> list[str]:
        """Get names of non-paused agents in a channel."""
        members = await self.db.get_channel_members(channel_id, include_paused=False)
        agent_names = []
        for m in members:
            config = next(
                (c for c in self.agent_configs.values() if c.id == m.agent_id), None
            )
            if config and config.name in self.agents:
                agent_names.append(config.name)
        return agent_names

    async def process_message(self, message: InboundMessage) -> list[OutboundMessage]:
        """
        Route and process an inbound message.

        Returns:
            List of outbound responses (one per responding agent).
        """
        # Get active agents for this channel
        active_names = await self.get_active_agents(message.chat_id)
        if not active_names:
            # Fall back to all registered agents
            active_names = list(self.agents.keys())

        # Resolve routing
        mode, target_names = self.router.resolve_owner(
            message, self.agents, active_names
        )

        if not target_names:
            return [
                OutboundMessage(
                    channel=message.channel,
                    chat_id=message.chat_id,
                    content="No agents available to handle this message.",
                    message_type="system",
                )
            ]

        # Store the inbound message
        await self._store_inbound(message)

        # Process based on routing mode
        if mode == "broadcast":
            # All target agents respond concurrently
            responses = await asyncio.gather(
                *[
                    self._agent_process(name, message)
                    for name in target_names
                    if name in self.agents
                ],
                return_exceptions=True,
            )
            results = []
            for r in responses:
                if isinstance(r, Exception):
                    logger.error(f"Agent error during broadcast: {r}")
                elif r:
                    results.append(r)
            return results
        else:
            # Single agent (or coordinator) processes
            name = target_names[0]
            if name not in self.agents:
                return []
            response = await self._agent_process(name, message)
            return [response] if response else []

    async def _agent_process(
        self, agent_name: str, message: InboundMessage
    ) -> OutboundMessage | None:
        """Have a specific agent process a message."""
        loop = self.agents.get(agent_name)
        if not loop:
            return None

        try:
            response_text = await loop.process_direct(
                content=message.content,
                session_key=f"{message.chat_id}:{agent_name}",
                channel=message.channel,
                chat_id=message.chat_id,
            )

            config = self.agent_configs.get(agent_name)

            outbound = OutboundMessage(
                channel=message.channel,
                chat_id=message.chat_id,
                content=response_text,
                sender_agent_id=config.id if config else None,
                sender_agent_name=agent_name,
                sender_agent_role=config.role if config else None,
            )

            # Store the outbound message
            await self._store_outbound(outbound)

            return outbound

        except Exception as e:
            logger.error(f"Agent {agent_name} error: {e}")
            return OutboundMessage(
                channel=message.channel,
                chat_id=message.chat_id,
                content=f"[{agent_name}] Error: {str(e)}",
                sender_agent_name=agent_name,
            )

    async def _store_inbound(self, message: InboundMessage) -> None:
        """Store an inbound message to the database."""
        try:
            msg = Message(
                channel_id=message.chat_id,
                sender_type="human",
                sender_name=message.sender_id,
                content=message.content,
                message_type=message.message_type,
                mentions=message.mentions,
            )
            await self.db.create_message(msg)
        except Exception as e:
            logger.warning(f"Failed to store inbound message: {e}")

    async def _store_outbound(self, message: OutboundMessage) -> None:
        """Store an outbound message to the database."""
        try:
            msg = Message(
                channel_id=message.chat_id,
                sender_id=message.sender_agent_id,
                sender_type="agent",
                sender_name=message.sender_agent_name,
                content=message.content,
                message_type=message.message_type,
            )
            await self.db.create_message(msg)
        except Exception as e:
            logger.warning(f"Failed to store outbound message: {e}")

    async def run(self) -> None:
        """Run the orchestrator, consuming from the bus."""
        self._running = True
        logger.info(
            f"Orchestrator started with {len(self.agents)} agents: "
            f"{list(self.agents.keys())}"
        )

        while self._running:
            try:
                msg = await asyncio.wait_for(
                    self.bus.consume_inbound(), timeout=1.0
                )
                responses = await self.process_message(msg)
                for r in responses:
                    await self.bus.publish_outbound(r)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Orchestrator error: {e}")

    def stop(self) -> None:
        """Stop the orchestrator."""
        self._running = False
        for name, loop in self.agents.items():
            loop.stop()
        logger.info("Orchestrator stopped")
