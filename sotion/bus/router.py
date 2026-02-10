"""Message router: resolves ownership of inbound messages."""

import re
from typing import TYPE_CHECKING

from loguru import logger

from sotion.bus.events import InboundMessage

if TYPE_CHECKING:
    from sotion.agent.loop import AgentLoop


# Pattern for @mentions: @AgentName
MENTION_PATTERN = re.compile(r"@(\w+)")


class MessageRouter:
    """
    Routes messages to the correct agent(s).

    Rules:
    1. @here -> all non-paused agents respond (standup)
    2. @AgentName -> that agent owns the message
    3. No mention -> coordinator handles it
    """

    def __init__(self, coordinator_name: str = "Max"):
        self.coordinator_name = coordinator_name

    def parse_mentions(self, content: str) -> list[str]:
        """Extract @mentions from message content."""
        return MENTION_PATTERN.findall(content)

    def resolve_owner(
        self,
        message: InboundMessage,
        agents: dict[str, "AgentLoop"],
        active_agent_names: list[str] | None = None,
    ) -> tuple[str, list[str]]:
        """
        Determine which agent(s) should handle a message.

        Args:
            message: The inbound message.
            agents: Dict of agent name -> AgentLoop.
            active_agent_names: Names of non-paused agents in the channel.

        Returns:
            Tuple of (routing_mode, agent_names) where routing_mode is one of:
            - 'broadcast': all listed agents respond concurrently
            - 'single': only the first listed agent responds
            - 'coordinator': coordinator handles routing
        """
        mentions = message.mentions or self.parse_mentions(message.content)
        active = active_agent_names or list(agents.keys())

        # @here -> broadcast to all active agents
        if "@here" in message.content:
            logger.info(f"@here broadcast to {len(active)} agents")
            return "broadcast", active

        # @AgentName -> route to that agent
        if mentions:
            matched = []
            for name in mentions:
                # Case-insensitive match
                for agent_name in agents:
                    if agent_name.lower() == name.lower() and agent_name in active:
                        matched.append(agent_name)
                        break
            if matched:
                logger.info(f"Routed to mentioned agent(s): {matched}")
                return "single", matched

        # No mention -> coordinator
        if self.coordinator_name in agents and self.coordinator_name in active:
            logger.info(f"No mention, routing to coordinator: {self.coordinator_name}")
            return "coordinator", [self.coordinator_name]

        # Fallback: first active agent
        if active:
            logger.warning(f"Coordinator not found, falling back to: {active[0]}")
            return "single", [active[0]]

        logger.error("No agents available to handle message")
        return "single", []
