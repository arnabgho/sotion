"""CRUD operations for Supabase tables."""

from datetime import datetime, timedelta
from typing import Any

from loguru import logger
from supabase import Client

from sotion.db.models import (
    Agent,
    Channel,
    ChannelMember,
    Message,
    AgentUpdate,
    Document,
    DocumentVersion,
    Task,
    PerformanceLog,
    Reward,
)


class DBQueries:
    """Database query layer wrapping Supabase client."""

    def __init__(self, client: Client):
        self.client = client

    # --- Agents ---

    async def create_agent(self, agent: Agent) -> Agent:
        data = agent.model_dump(mode="json")
        result = self.client.table("agents").insert(data).execute()
        return Agent(**result.data[0])

    async def get_agent(self, agent_id: str) -> Agent | None:
        result = self.client.table("agents").select("*").eq("id", agent_id).execute()
        return Agent(**result.data[0]) if result.data else None

    async def get_agent_by_name(self, name: str) -> Agent | None:
        result = self.client.table("agents").select("*").eq("name", name).execute()
        return Agent(**result.data[0]) if result.data else None

    async def list_agents(self, status: str | None = None) -> list[Agent]:
        query = self.client.table("agents").select("*")
        if status:
            query = query.eq("status", status)
        result = query.execute()
        return [Agent(**row) for row in result.data]

    async def update_agent(self, agent_id: str, **fields: Any) -> Agent | None:
        fields["updated_at"] = datetime.now().isoformat()
        result = self.client.table("agents").update(fields).eq("id", agent_id).execute()
        return Agent(**result.data[0]) if result.data else None

    # --- Channels ---

    async def create_channel(self, channel: Channel) -> Channel:
        data = channel.model_dump(mode="json")
        result = self.client.table("channels").insert(data).execute()
        return Channel(**result.data[0])

    async def get_channel(self, channel_id: str) -> Channel | None:
        result = self.client.table("channels").select("*").eq("id", channel_id).execute()
        return Channel(**result.data[0]) if result.data else None

    async def get_channel_by_name(self, name: str) -> Channel | None:
        result = self.client.table("channels").select("*").eq("name", name).execute()
        return Channel(**result.data[0]) if result.data else None

    async def list_channels(self, include_archived: bool = False) -> list[Channel]:
        """Get all project channels (excludes DMs)."""
        query = self.client.table("channels").select("*").eq("channel_type", "project")
        if not include_archived:
            query = query.eq("is_archived", False)
        result = query.execute()
        return [Channel(**row) for row in result.data]

    async def list_dms(self, limit: int = 50) -> list[Channel]:
        """Get all DM conversations."""
        result = (
            self.client.table("channels")
            .select("*")
            .eq("channel_type", "dm")
            .eq("is_archived", False)
            .limit(limit)
            .execute()
        )
        return [Channel(**row) for row in result.data]

    async def find_dm_by_agent(self, agent_id: str) -> Channel | None:
        """Find existing DM with a specific agent."""
        result = (
            self.client.table("channels")
            .select("*")
            .eq("channel_type", "dm")
            .eq("dm_participant_agent_id", agent_id)
            .limit(1)
            .execute()
        )
        return Channel(**result.data[0]) if result.data else None

    # --- Channel Members ---

    async def add_member(self, member: ChannelMember) -> ChannelMember:
        data = member.model_dump(mode="json")
        result = self.client.table("channel_members").insert(data).execute()
        return ChannelMember(**result.data[0])

    async def get_channel_members(
        self, channel_id: str, include_paused: bool = True
    ) -> list[ChannelMember]:
        query = self.client.table("channel_members").select("*").eq("channel_id", channel_id)
        if not include_paused:
            query = query.eq("is_paused", False)
        result = query.execute()
        return [ChannelMember(**row) for row in result.data]

    async def set_member_paused(
        self, channel_id: str, agent_id: str, is_paused: bool
    ) -> None:
        self.client.table("channel_members").update({"is_paused": is_paused}).eq(
            "channel_id", channel_id
        ).eq("agent_id", agent_id).execute()

    async def pause_all_except(self, channel_id: str, except_agent_id: str) -> None:
        """Pause all agents in a channel except one (for 1:1 mode)."""
        members = await self.get_channel_members(channel_id)
        for m in members:
            is_paused = m.agent_id != except_agent_id
            await self.set_member_paused(channel_id, m.agent_id, is_paused)

    async def unpause_all(self, channel_id: str) -> None:
        """Unpause all agents in a channel."""
        members = await self.get_channel_members(channel_id)
        for m in members:
            await self.set_member_paused(channel_id, m.agent_id, False)

    # --- Messages ---

    async def create_message(self, message: Message) -> Message:
        data = message.model_dump(mode="json")
        result = self.client.table("messages").insert(data).execute()
        return Message(**result.data[0])

    async def get_channel_messages(
        self, channel_id: str, limit: int = 50, before: datetime | None = None
    ) -> list[Message]:
        query = (
            self.client.table("messages")
            .select("*")
            .eq("channel_id", channel_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if before:
            query = query.lt("created_at", before.isoformat())
        result = query.execute()
        return [Message(**row) for row in reversed(result.data)]

    async def get_message(self, message_id: str) -> Message | None:
        result = self.client.table("messages").select("*").eq("id", message_id).execute()
        return Message(**result.data[0]) if result.data else None

    # --- Agent Updates ---

    async def create_update(self, update: AgentUpdate) -> AgentUpdate:
        data = update.model_dump(mode="json")
        result = self.client.table("agent_updates").insert(data).execute()
        return AgentUpdate(**result.data[0])

    async def get_agent_updates(
        self, agent_id: str, channel_id: str | None = None, limit: int = 10
    ) -> list[AgentUpdate]:
        query = self.client.table("agent_updates").select("*").eq("agent_id", agent_id)
        if channel_id:
            query = query.eq("channel_id", channel_id)
        result = query.order("created_at", desc=True).limit(limit).execute()
        return [AgentUpdate(**row) for row in result.data]

    async def get_recent_agent_updates(
        self, channel_id: str, hours: int = 48
    ) -> list[AgentUpdate]:
        """Get recent agent updates for a channel within the last N hours."""
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        query = (
            self.client.table("agent_updates")
            .select("*")
            .eq("channel_id", channel_id)
            .gte("created_at", cutoff_time)
            .order("created_at", desc=True)
        )
        result = query.execute()
        return [AgentUpdate(**row) for row in result.data]

    # --- Documents ---

    async def create_document(self, doc: Document) -> Document:
        data = doc.model_dump(mode="json")
        result = self.client.table("documents").insert(data).execute()
        return Document(**result.data[0])

    async def get_document(self, doc_id: str) -> Document | None:
        result = self.client.table("documents").select("*").eq("id", doc_id).execute()
        return Document(**result.data[0]) if result.data else None

    async def list_channel_documents(
        self, channel_id: str, doc_type: str | None = None
    ) -> list[Document]:
        query = (
            self.client.table("documents")
            .select("*")
            .eq("channel_id", channel_id)
            .eq("status", "active")
        )
        if doc_type:
            query = query.eq("doc_type", doc_type)
        result = query.order("updated_at", desc=True).execute()
        return [Document(**row) for row in result.data]

    async def update_document(
        self, doc_id: str, content: str, edited_by: str
    ) -> Document | None:
        now = datetime.now().isoformat()
        # Get current version
        doc = await self.get_document(doc_id)
        if not doc:
            return None
        new_version = doc.version + 1

        # Save version snapshot
        version = DocumentVersion(
            document_id=doc_id,
            version=doc.version,
            content=doc.content,
            edited_by=edited_by,
        )
        self.client.table("document_versions").insert(
            version.model_dump(mode="json")
        ).execute()

        # Update document
        result = (
            self.client.table("documents")
            .update({
                "content": content,
                "last_edited_by": edited_by,
                "version": new_version,
                "updated_at": now,
            })
            .eq("id", doc_id)
            .execute()
        )
        return Document(**result.data[0]) if result.data else None

    # --- Tasks ---

    async def create_task(self, task: Task) -> Task:
        data = task.model_dump(mode="json")
        result = self.client.table("tasks").insert(data).execute()
        return Task(**result.data[0])

    async def get_task(self, task_id: str) -> Task | None:
        result = self.client.table("tasks").select("*").eq("id", task_id).execute()
        return Task(**result.data[0]) if result.data else None

    async def list_tasks(
        self,
        channel_id: str | None = None,
        assigned_to: str | None = None,
        status: str | None = None,
    ) -> list[Task]:
        query = self.client.table("tasks").select("*")
        if channel_id:
            query = query.eq("channel_id", channel_id)
        if assigned_to:
            query = query.eq("assigned_to", assigned_to)
        if status:
            query = query.eq("status", status)
        result = query.order("priority", desc=True).execute()
        return [Task(**row) for row in result.data]

    async def complete_task(
        self, task_id: str, quality_score: float | None = None
    ) -> Task | None:
        now = datetime.now().isoformat()
        fields: dict[str, Any] = {
            "status": "completed",
            "completed_at": now,
            "updated_at": now,
        }
        if quality_score is not None:
            fields["quality_score"] = quality_score
        result = self.client.table("tasks").update(fields).eq("id", task_id).execute()
        return Task(**result.data[0]) if result.data else None

    # --- Performance Log ---

    async def log_performance(self, log: PerformanceLog) -> PerformanceLog:
        data = log.model_dump(mode="json")
        result = self.client.table("performance_log").insert(data).execute()
        return PerformanceLog(**result.data[0])

    async def get_performance_logs(
        self, agent_id: str, limit: int = 50
    ) -> list[PerformanceLog]:
        result = (
            self.client.table("performance_log")
            .select("*")
            .eq("agent_id", agent_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [PerformanceLog(**row) for row in result.data]

    # --- Rewards ---

    async def create_reward(self, reward: Reward) -> Reward:
        data = reward.model_dump(mode="json")
        result = self.client.table("rewards").insert(data).execute()
        return Reward(**result.data[0])

    async def get_agent_rewards(self, agent_id: str, limit: int = 50) -> list[Reward]:
        result = (
            self.client.table("rewards")
            .select("*")
            .eq("agent_id", agent_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [Reward(**row) for row in result.data]
