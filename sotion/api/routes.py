"""REST API routes for sotion."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sotion.db.client import get_supabase
from sotion.db.queries import DBQueries
from sotion.db.models import Channel, Agent, Message, ChannelMember

router = APIRouter()


def _get_db() -> DBQueries:
    return DBQueries(get_supabase())


# --- Request/Response models ---

class SendMessageRequest(BaseModel):
    content: str
    sender_name: str = "Human"


class CreateChannelRequest(BaseModel):
    name: str
    description: str | None = None
    channel_type: str = "project"


class CreateAgentRequest(BaseModel):
    name: str
    role: str
    model: str = "anthropic/claude-sonnet-4-5-20250929"
    avatar_emoji: str = "\U0001f916"
    capabilities: list[str] = []
    config: dict[str, Any] = {}


class PauseRequest(BaseModel):
    except_agent_id: str | None = None


# --- Channel endpoints ---

@router.get("/channels")
async def list_channels():
    db = _get_db()
    channels = await db.list_channels()
    return [c.model_dump(mode="json") for c in channels]


@router.post("/channels")
async def create_channel(req: CreateChannelRequest):
    db = _get_db()
    channel = Channel(name=req.name, description=req.description, channel_type=req.channel_type)
    result = await db.create_channel(channel)
    return result.model_dump(mode="json")


@router.get("/channels/{channel_id}")
async def get_channel(channel_id: str):
    db = _get_db()
    channel = await db.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel.model_dump(mode="json")


@router.get("/channels/{channel_id}/messages")
async def get_channel_messages(channel_id: str, limit: int = 50):
    db = _get_db()
    messages = await db.get_channel_messages(channel_id, limit=limit)
    return [m.model_dump(mode="json") for m in messages]


@router.get("/channels/{channel_id}/members")
async def get_channel_members(channel_id: str):
    db = _get_db()
    members = await db.get_channel_members(channel_id)
    return [m.model_dump(mode="json") for m in members]


@router.post("/channels/{channel_id}/members/{agent_id}")
async def add_channel_member(channel_id: str, agent_id: str):
    db = _get_db()
    member = ChannelMember(channel_id=channel_id, agent_id=agent_id)
    result = await db.add_member(member)
    return result.model_dump(mode="json")


@router.post("/channels/{channel_id}/pause")
async def pause_agents(channel_id: str, req: PauseRequest):
    db = _get_db()
    if req.except_agent_id:
        await db.pause_all_except(channel_id, req.except_agent_id)
        return {"status": "paused_all_except", "except_agent_id": req.except_agent_id}
    else:
        await db.unpause_all(channel_id)
        return {"status": "all_unpaused"}


# --- Agent endpoints ---

@router.get("/agents")
async def list_agents():
    db = _get_db()
    agents = await db.list_agents()
    return [a.model_dump(mode="json") for a in agents]


@router.post("/agents")
async def create_agent(req: CreateAgentRequest):
    db = _get_db()
    agent = Agent(
        name=req.name,
        role=req.role,
        model=req.model,
        avatar_emoji=req.avatar_emoji,
        capabilities=req.capabilities,
        config=req.config,
    )
    result = await db.create_agent(agent)
    return result.model_dump(mode="json")


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    db = _get_db()
    agent = await db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.model_dump(mode="json")


# --- Document endpoints ---

@router.get("/channels/{channel_id}/documents")
async def list_documents(channel_id: str, doc_type: str | None = None):
    db = _get_db()
    docs = await db.list_channel_documents(channel_id, doc_type)
    return [d.model_dump(mode="json") for d in docs]


@router.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    db = _get_db()
    doc = await db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc.model_dump(mode="json")


# --- Task endpoints ---

@router.get("/channels/{channel_id}/tasks")
async def list_tasks(channel_id: str, status: str | None = None):
    db = _get_db()
    tasks = await db.list_tasks(channel_id=channel_id, status=status)
    return [t.model_dump(mode="json") for t in tasks]


@router.get("/agents/{agent_id}/tasks")
async def list_agent_tasks(agent_id: str, status: str | None = None):
    db = _get_db()
    tasks = await db.list_tasks(assigned_to=agent_id, status=status)
    return [t.model_dump(mode="json") for t in tasks]
