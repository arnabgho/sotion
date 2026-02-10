"""Main FastAPI application for sotion."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from sotion.api.routes import router as api_router
from sotion.api.websocket import websocket_endpoint, ws_manager
from sotion.bus.queue import MessageBus
from sotion.config.loader import load_config
from sotion.db.client import init_supabase, get_supabase
from sotion.db.queries import DBQueries
from sotion.orchestrator import SotionOrchestrator
from sotion.channels.manager import ChannelManager

# Global state
_orchestrator: SotionOrchestrator | None = None
_bus: MessageBus | None = None
_channel_manager: ChannelManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    global _orchestrator, _bus, _channel_manager

    config = load_config()

    # Initialize Supabase
    if config.supabase.url and config.supabase.service_role_key:
        init_supabase(config.supabase.url, config.supabase.service_role_key)
        logger.info("Supabase connected")
    else:
        logger.warning("Supabase not configured — running without persistence")

    # Initialize message bus
    _bus = MessageBus()

    # Initialize LLM provider
    from sotion.providers.litellm_provider import LiteLLMProvider
    provider = LiteLLMProvider(config)

    # Initialize DB queries
    db = DBQueries(get_supabase()) if config.supabase.url else None

    # Initialize orchestrator
    workspace = config.workspace_path
    workspace.mkdir(parents=True, exist_ok=True)

    _orchestrator = SotionOrchestrator(
        bus=_bus,
        provider=provider,
        workspace=workspace,
        db=db,
    )

    # Load agents from database
    if db:
        agents = await db.list_agents(status="active")
        for agent_config in agents:
            await _orchestrator.register_agent(agent_config)

    # Initialize channel manager
    if db:
        _channel_manager = ChannelManager(config, _bus, db)
        await _channel_manager.start_all()

    # Subscribe web channel to outbound messages
    _bus.subscribe_outbound("web", ws_manager.broadcast_outbound)

    # Start orchestrator in background
    orchestrator_task = asyncio.create_task(_orchestrator.run())
    logger.info("Sotion server started")

    yield

    # Shutdown
    if _orchestrator:
        _orchestrator.stop()
    if _channel_manager:
        await _channel_manager.stop_all()
    if _bus:
        _bus.stop()
    orchestrator_task.cancel()
    logger.info("Sotion server stopped")


app = FastAPI(
    title="Sotion",
    description="Slack+Notion hybrid for managing AI agent teams",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API routes
app.include_router(api_router, prefix="/api")


# WebSocket endpoint
@app.websocket("/ws/{channel_id}")
async def ws_route(websocket: WebSocket, channel_id: str):
    await websocket_endpoint(websocket, channel_id, _bus)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "agents": len(_orchestrator.agents) if _orchestrator else 0,
    }


# Message sending endpoint (triggers orchestrator)
@app.post("/api/channels/{channel_id}/send")
async def send_message(channel_id: str, body: dict):
    """Send a message and get agent responses."""
    from sotion.bus.events import InboundMessage

    content = body.get("content", "")
    sender_name = body.get("sender_name", "Human")
    mentions = body.get("mentions", [])

    message_type = "chat"
    if "@here" in content:
        message_type = "standup_request"

    msg = InboundMessage(
        channel="web",
        sender_id=sender_name,
        chat_id=channel_id,
        content=content,
        message_type=message_type,
        mentions=mentions,
    )

    if _orchestrator:
        responses = await _orchestrator.process_message(msg)
        return {
            "responses": [
                {
                    "content": r.content,
                    "sender_name": r.sender_agent_name,
                    "sender_role": r.sender_agent_role,
                }
                for r in responses
            ]
        }
    return {"responses": []}
