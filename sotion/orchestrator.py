"""Multi-agent orchestrator: manages N agent loops with message routing."""

import asyncio
from datetime import datetime
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
from sotion.agents.tools import (
    DelegateTool,
    LogUpdateTool,
    CreateDocTool,
    EditDocTool,
    QueryDocsTool,
    CreateTaskTool,
    CompleteTaskTool,
)


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

    def _load_role_prompt(self, role: str) -> str | None:
        """Load role-specific prompt from markdown file."""
        roles_dir = Path(__file__).parent / "agents" / "roles"
        role_file = roles_dir / f"{role}.md"

        if not role_file.exists():
            logger.warning(f"Role file not found: {role_file}")
            return None

        try:
            return role_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to load role file {role_file}: {e}")
            return None

    async def _build_team_roster(self, channel_id: str | None = None) -> list[dict[str, str]]:
        """Build team roster for agent context."""
        roster = []

        if channel_id and self.db:
            # Get agents in this channel
            members = await self.db.get_channel_members(channel_id, include_paused=True)
            for member in members:
                agent_config = next(
                    (c for c in self.agent_configs.values() if c.id == member.agent_id),
                    None
                )
                if agent_config:
                    roster.append({
                        "name": agent_config.name,
                        "role": agent_config.role,
                        "status": "paused" if member.is_paused else agent_config.status,
                    })
        else:
            # Use all registered agents
            for agent_config in self.agent_configs.values():
                roster.append({
                    "name": agent_config.name,
                    "role": agent_config.role,
                    "status": agent_config.status,
                })

        return roster

    def _build_economy_status(self, agent_config: Agent) -> dict[str, Any]:
        """Build economy status dict for agent context."""
        return {
            "salary_balance": agent_config.salary_balance,
            "performance_score": agent_config.performance_score,
            "token_budget": agent_config.token_budget,
            "status": agent_config.status,
        }

    def _register_sotion_tools(
        self, loop: AgentLoop, agent_config: Agent, allowed_tools: list[str]
    ) -> None:
        """Register Sotion-specific tools based on role."""

        # Delegate tool (coordinator only)
        if "delegate" in allowed_tools:
            available_agents = [
                name for name in self.agent_configs.keys()
                if name != agent_config.name
            ]
            delegate_tool = DelegateTool(
                delegate_callback=None,  # TODO: implement in future
                available_agents=available_agents,
            )
            loop.tools.register(delegate_tool)

        # Log update tool
        if "log_update" in allowed_tools:
            log_tool = LogUpdateTool(
                db=self.db,
                agent_id=agent_config.id,
                channel_id="",  # Set per-message
            )
            loop.tools.register(log_tool)

        # Document tools
        if "create_doc" in allowed_tools:
            create_doc_tool = CreateDocTool(
                db=self.db,
                channel_id="",  # Set per-message
                agent_id=agent_config.id,
            )
            loop.tools.register(create_doc_tool)

        if "edit_doc" in allowed_tools:
            edit_doc_tool = EditDocTool(
                db=self.db,
                agent_id=agent_config.id,
            )
            loop.tools.register(edit_doc_tool)

        if "query_docs" in allowed_tools:
            query_docs_tool = QueryDocsTool(
                db=self.db,
                channel_id="",  # Set per-message
            )
            loop.tools.register(query_docs_tool)

        # Task tools
        if "create_task" in allowed_tools:
            create_task_tool = CreateTaskTool(
                db=self.db,
                channel_id="",  # Set per-message
            )
            loop.tools.register(create_task_tool)

        if "complete_task" in allowed_tools:
            complete_task_tool = CompleteTaskTool(db=self.db)
            loop.tools.register(complete_task_tool)

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

        # Load role-specific prompt
        role_prompt = self._load_role_prompt(agent_config.role)

        # Build team roster (all registered agents initially)
        team_roster = await self._build_team_roster(channel_id=None)

        # Build economy status
        economy_status = self._build_economy_status(agent_config)

        # Set agent identity
        loop.context.set_agent_identity(
            name=agent_config.name,
            role=agent_config.role,
            role_prompt=role_prompt,
            team_roster=team_roster,
            economy_status=economy_status,
        )

        # Configure tools based on role
        allowed_tools = ROLE_TOOLS.get(agent_config.role, [])

        # Register Sotion-specific tools
        self._register_sotion_tools(loop, agent_config, allowed_tools)

        # Remove non-allowed default tools
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
        mode, target_names, metadata = self.router.resolve_owner(
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
            is_standup = metadata.get("is_standup", False)

            # Inject standup prompt if this is a standup request
            if is_standup:
                logger.info("Processing standup request")
                standup_prompt = """
This is a standup request. Please provide a brief update on your recent work:

1. **What you've worked on recently** (last 24-48 hours)
2. **Current tasks** (what you're doing now)
3. **Blockers or questions** (if any)

Use the `log_update` tool to record your update, then respond with a summary.
Format your response as:

**[Your Name] - [Your Role]**
- Recent: [brief summary]
- Current: [current task]
- Blockers: [any issues or "None"]
"""
                # Create modified message with standup prompt
                standup_message = InboundMessage(
                    content=f"{standup_prompt}\n\nOriginal request: {message.content}",
                    channel=message.channel,
                    chat_id=message.chat_id,
                    sender_name=message.sender_name,
                    mentions=message.mentions,
                )
                message = standup_message

            # All target agents respond concurrently
            responses = await asyncio.gather(
                *[
                    self._agent_process(name, message)
                    for name in target_names
                    if name in self.agents
                ],
                return_exceptions=True,
            )

            # Aggregate standup responses into single report
            if is_standup:
                standup_report = await self._format_standup_report(
                    responses, message.chat_id
                )
                return [
                    OutboundMessage(
                        channel=message.channel,
                        chat_id=message.chat_id,
                        content=standup_report,
                        sender_agent_name="System",
                        message_type="standup_response",
                    )
                ]

            # Regular broadcast: return individual responses
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

        config = self.agent_configs.get(agent_name)
        if not config:
            return None

        # Update context on Sotion tools that need it
        # LogUpdateTool: set_context(agent_id, channel_id)
        log_tool = loop.tools.get("log_update")
        if log_tool and hasattr(log_tool, "set_context"):
            log_tool.set_context(config.id, message.chat_id)

        # CreateDocTool: set_context(channel_id, agent_id)
        create_doc_tool = loop.tools.get("create_doc")
        if create_doc_tool and hasattr(create_doc_tool, "set_context"):
            create_doc_tool.set_context(message.chat_id, config.id)

        # EditDocTool: set_context(agent_id)
        edit_doc_tool = loop.tools.get("edit_doc")
        if edit_doc_tool and hasattr(edit_doc_tool, "set_context"):
            edit_doc_tool.set_context(config.id)

        # QueryDocsTool: set_context(channel_id)
        query_docs_tool = loop.tools.get("query_docs")
        if query_docs_tool and hasattr(query_docs_tool, "set_context"):
            query_docs_tool.set_context(message.chat_id)

        # CreateTaskTool: set_context(channel_id)
        create_task_tool = loop.tools.get("create_task")
        if create_task_tool and hasattr(create_task_tool, "set_context"):
            create_task_tool.set_context(message.chat_id)

        try:
            response_text = await loop.process_direct(
                content=message.content,
                session_key=f"{message.chat_id}:{agent_name}",
                channel=message.channel,
                chat_id=message.chat_id,
            )

            outbound = OutboundMessage(
                channel=message.channel,
                chat_id=message.chat_id,
                content=response_text,
                sender_agent_id=config.id,
                sender_agent_name=agent_name,
                sender_agent_role=config.role,
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

    async def _format_standup_report(
        self, responses: list, channel_id: str
    ) -> str:
        """Format agent responses into a standup report."""
        report_lines = [
            "## 📊 Team Standup Report\n",
            f"*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n",
        ]

        # Get recent log_update entries
        updates_by_agent = {}
        if self.db:
            try:
                recent_updates = await self.db.get_recent_agent_updates(
                    channel_id=channel_id,
                    hours=48,  # Last 48 hours
                )

                # Group by agent
                for update in recent_updates:
                    agent_name = None
                    # Find agent name by ID
                    for name, config in self.agent_configs.items():
                        if str(config.id) == str(update.agent_id):
                            agent_name = name
                            break

                    if agent_name:
                        if agent_name not in updates_by_agent:
                            updates_by_agent[agent_name] = []
                        updates_by_agent[agent_name].append(update)
            except Exception as e:
                logger.error(f"Failed to get recent updates: {e}")

        # Process each response
        for response in responses:
            if isinstance(response, Exception):
                continue

            if isinstance(response, OutboundMessage):
                agent_name = response.sender_agent_name
                agent_config = self.agent_configs.get(agent_name)

                if not agent_config:
                    continue

                report_lines.append(f"\n### {agent_name} ({agent_config.role})")

                # Include logged updates
                if updates_by_agent.get(agent_name):
                    report_lines.append("\n**Recent Updates:**")
                    for update in updates_by_agent[agent_name][:3]:  # Last 3
                        report_lines.append(f"- {update.summary}")

                # Include agent's standup response
                report_lines.append(f"\n{response.content}\n")

        report_lines.append("\n---\n*Use `log_update` tool to record your progress*")

        return "\n".join(report_lines)

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
