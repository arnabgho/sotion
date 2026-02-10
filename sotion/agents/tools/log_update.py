"""LogUpdateTool: agents record activity for standup reports."""

from typing import Any

from sotion.agent.tools.base import Tool
from sotion.db.queries import DBQueries
from sotion.db.models import AgentUpdate


class LogUpdateTool(Tool):
    """Tool for agents to log their activity."""

    def __init__(self, db: DBQueries | None = None, agent_id: str = "", channel_id: str = ""):
        self._db = db
        self._agent_id = agent_id
        self._channel_id = channel_id

    def set_context(self, agent_id: str, channel_id: str) -> None:
        self._agent_id = agent_id
        self._channel_id = channel_id

    @property
    def name(self) -> str:
        return "log_update"

    @property
    def description(self) -> str:
        return (
            "Log a progress update or activity summary. "
            "These logs are used for @here standup reports."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "A concise summary of what you did or accomplished",
                },
            },
            "required": ["summary"],
        }

    async def execute(self, summary: str = "", **kwargs: Any) -> str:
        if not self._db:
            return "Error: Database not configured"
        if not self._agent_id or not self._channel_id:
            return "Error: Agent/channel context not set"

        update = AgentUpdate(
            agent_id=self._agent_id,
            channel_id=self._channel_id,
            summary=summary,
        )
        await self._db.create_update(update)
        return f"Update logged: {summary[:100]}"
