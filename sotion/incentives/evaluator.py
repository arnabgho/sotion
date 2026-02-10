"""Performance evaluator: rolling scores, warnings, firing, bonuses."""

from loguru import logger

from sotion.db.queries import DBQueries
from sotion.db.models import Reward


WARNING_THRESHOLD = 0.3
FIRING_THRESHOLD = 0.15
BONUS_THRESHOLD = 0.8
SALARY_PER_CYCLE = 10
BONUS_AMOUNT = 50


class PerformanceEvaluator:
    """Evaluates agent performance and applies consequences."""

    def __init__(self, db: DBQueries):
        self.db = db

    async def evaluate_agent(self, agent_id: str) -> dict:
        """
        Evaluate an agent's performance based on recent logs.

        Returns a dict with score, status, and any actions taken.
        """
        logs = await self.db.get_performance_logs(agent_id, limit=50)
        agent = await self.db.get_agent(agent_id)
        if not agent:
            return {"error": "Agent not found"}

        # Calculate rolling score
        scores = []
        for log in logs:
            if log.event_type == "task_completed":
                qs = log.details.get("quality_score")
                scores.append(qs if qs is not None else 0.7)
            elif log.event_type == "task_failed":
                scores.append(0.0)
            elif log.event_type == "review_score":
                scores.append(log.details.get("score", 0.5))

        if not scores:
            return {
                "agent_name": agent.name,
                "score": agent.performance_score,
                "status": agent.status,
                "action": "none",
            }

        new_score = sum(scores) / len(scores)
        action = "none"

        # Apply consequences
        if new_score < FIRING_THRESHOLD and agent.status != "fired":
            await self.db.update_agent(agent_id, status="fired", performance_score=new_score)
            action = "fired"
            logger.warning(f"Agent {agent.name} FIRED (score: {new_score:.2f})")
        elif new_score < WARNING_THRESHOLD and agent.status != "warning":
            await self.db.update_agent(agent_id, status="warning", performance_score=new_score)
            action = "warning"
            logger.warning(f"Agent {agent.name} WARNING (score: {new_score:.2f})")
        elif new_score >= BONUS_THRESHOLD:
            await self.db.update_agent(agent_id, performance_score=new_score, status="active")
            # Award bonus
            reward = Reward(
                agent_id=agent_id,
                reward_type="bonus",
                amount=BONUS_AMOUNT,
                reason=f"High performance score: {new_score:.2f}",
            )
            await self.db.create_reward(reward)
            new_salary = agent.salary_balance + BONUS_AMOUNT
            await self.db.update_agent(agent_id, salary_balance=new_salary)
            action = "bonus"
            logger.info(f"Agent {agent.name} BONUS +{BONUS_AMOUNT} (score: {new_score:.2f})")
        else:
            await self.db.update_agent(agent_id, performance_score=new_score, status="active")

        return {
            "agent_name": agent.name,
            "score": new_score,
            "status": agent.status if action == "none" else action,
            "action": action,
        }

    async def pay_salary(self, agent_id: str) -> int:
        """Pay the regular salary cycle to an agent. Returns new balance."""
        agent = await self.db.get_agent(agent_id)
        if not agent or agent.status == "fired":
            return 0

        new_balance = agent.salary_balance + SALARY_PER_CYCLE
        await self.db.update_agent(agent_id, salary_balance=new_balance)

        reward = Reward(
            agent_id=agent_id,
            reward_type="salary",
            amount=SALARY_PER_CYCLE,
            reason="Regular salary cycle",
        )
        await self.db.create_reward(reward)
        return new_balance
