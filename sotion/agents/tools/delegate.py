"""DelegateTool: coordinator routes a message to a specific agent."""

from typing import Any, Callable, Awaitable

from sotion.agent.tools.base import Tool


class DelegateTool(Tool):
    """Tool for the coordinator to delegate a task to another agent."""

    def __init__(
        self,
        delegate_callback: Callable[[str, str], Awaitable[str]] | None = None,
        available_agents: list[str] | None = None,
    ):
        self._delegate_callback = delegate_callback
        self._available_agents = available_agents or []

    @property
    def name(self) -> str:
        return "delegate"

    @property
    def description(self) -> str:
        agents_str = ", ".join(self._available_agents) if self._available_agents else "any registered agent"
        return (
            f"Delegate a task to another agent on the team. "
            f"Available agents: {agents_str}. "
            f"Use this when a message should be handled by a specialist."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Name of the agent to delegate to (e.g., 'Alice', 'Bob')",
                },
                "task": {
                    "type": "string",
                    "description": "Description of the task to delegate",
                },
            },
            "required": ["agent_name", "task"],
        }

    async def execute(self, agent_name: str = "", task: str = "", **kwargs: Any) -> str:
        if not agent_name or not task:
            return "Error: agent_name and task are required"

        if self._available_agents and agent_name not in self._available_agents:
            return (
                f"Error: Agent '{agent_name}' not found. "
                f"Available agents: {', '.join(self._available_agents)}"
            )

        if self._delegate_callback:
            result = await self._delegate_callback(agent_name, task)
            return result

        return f"Delegated to @{agent_name}: {task}"
