"""Performance tracker: logs task completions, failures, token usage."""

from sotion.db.queries import DBQueries
from sotion.db.models import PerformanceLog


class PerformanceTracker:
    """Tracks agent performance events."""

    def __init__(self, db: DBQueries):
        self.db = db

    async def log_task_completed(
        self, agent_id: str, task_id: str, quality_score: float | None = None
    ) -> None:
        log = PerformanceLog(
            agent_id=agent_id,
            event_type="task_completed",
            details={"task_id": task_id, "quality_score": quality_score},
        )
        await self.db.log_performance(log)

    async def log_task_failed(self, agent_id: str, task_id: str, reason: str = "") -> None:
        log = PerformanceLog(
            agent_id=agent_id,
            event_type="task_failed",
            details={"task_id": task_id, "reason": reason},
        )
        await self.db.log_performance(log)

    async def log_review_score(
        self, agent_id: str, task_id: str, score: float
    ) -> None:
        log = PerformanceLog(
            agent_id=agent_id,
            event_type="review_score",
            details={"task_id": task_id, "score": score},
        )
        await self.db.log_performance(log)

    async def log_token_usage(
        self, agent_id: str, tokens_used: int, model: str
    ) -> None:
        log = PerformanceLog(
            agent_id=agent_id,
            event_type="token_usage",
            details={"tokens_used": tokens_used, "model": model},
        )
        await self.db.log_performance(log)
