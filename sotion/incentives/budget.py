"""Token budget tracking for agents."""

from loguru import logger

from sotion.db.queries import DBQueries


class BudgetManager:
    """Tracks and enforces token budgets per agent."""

    def __init__(self, db: DBQueries):
        self.db = db

    async def check_budget(self, agent_id: str) -> tuple[bool, int]:
        """Check if agent has budget remaining. Returns (has_budget, remaining)."""
        agent = await self.db.get_agent(agent_id)
        if not agent:
            return False, 0
        return agent.token_budget > 0, agent.token_budget

    async def deduct_tokens(self, agent_id: str, tokens_used: int) -> int:
        """Deduct tokens from agent's budget. Returns remaining budget."""
        agent = await self.db.get_agent(agent_id)
        if not agent:
            return 0
        new_budget = max(0, agent.token_budget - tokens_used)
        await self.db.update_agent(agent_id, token_budget=new_budget)
        if new_budget == 0:
            logger.warning(f"Agent {agent.name} has exhausted token budget")
        return new_budget

    async def refill_budget(self, agent_id: str, amount: int) -> int:
        """Refill an agent's token budget. Returns new budget."""
        agent = await self.db.get_agent(agent_id)
        if not agent:
            return 0
        new_budget = agent.token_budget + amount
        await self.db.update_agent(agent_id, token_budget=new_budget)
        logger.info(f"Refilled {agent.name} budget by {amount} -> {new_budget}")
        return new_budget
