"""Task tools: create and complete assignable work items."""

from typing import Any

from sotion.agent.tools.base import Tool
from sotion.db.queries import DBQueries
from sotion.db.models import Task


class CreateTaskTool(Tool):
    """Tool to create and assign a task."""

    def __init__(self, db: DBQueries | None = None, channel_id: str = ""):
        self._db = db
        self._channel_id = channel_id

    def set_context(self, channel_id: str) -> None:
        self._channel_id = channel_id

    @property
    def name(self) -> str:
        return "create_task"

    @property
    def description(self) -> str:
        return "Create a new task and optionally assign it to an agent."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task title"},
                "description": {"type": "string", "description": "Task description"},
                "assigned_to": {
                    "type": "string",
                    "description": "Agent ID to assign to (optional)",
                },
                "priority": {
                    "type": "integer",
                    "description": "Priority (0=low, 1=medium, 2=high)",
                    "minimum": 0,
                    "maximum": 2,
                },
            },
            "required": ["title"],
        }

    async def execute(
        self,
        title: str = "",
        description: str = "",
        assigned_to: str | None = None,
        priority: int = 0,
        **kwargs: Any,
    ) -> str:
        if not self._db:
            return "Error: Database not configured"

        task = Task(
            channel_id=self._channel_id or None,
            title=title,
            description=description,
            assigned_to=assigned_to,
            priority=priority,
        )
        result = await self._db.create_task(task)
        assigned_str = f", assigned to {assigned_to}" if assigned_to else ""
        return f"Task created: '{result.title}' (id: {result.id}{assigned_str})"


class CompleteTaskTool(Tool):
    """Tool to mark a task as completed."""

    def __init__(self, db: DBQueries | None = None):
        self._db = db

    @property
    def name(self) -> str:
        return "complete_task"

    @property
    def description(self) -> str:
        return "Mark a task as completed, optionally with a quality score."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to complete"},
                "quality_score": {
                    "type": "number",
                    "description": "Quality score (0.0-1.0)",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
            },
            "required": ["task_id"],
        }

    async def execute(
        self, task_id: str = "", quality_score: float | None = None, **kwargs: Any
    ) -> str:
        if not self._db:
            return "Error: Database not configured"

        result = await self._db.complete_task(task_id, quality_score)
        if result:
            score_str = f" (quality: {quality_score:.1f})" if quality_score is not None else ""
            return f"Task completed: '{result.title}'{score_str}"
        return f"Error: Task '{task_id}' not found"
