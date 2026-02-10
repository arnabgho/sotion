# Sotion — Implementation Plan (Based on Nanobot)

## Context

Sotion is a Slack+Notion hybrid for managing AI agent teams. We're building it on top of [nanobot](https://github.com/HKUDS/nanobot) (~3,500 lines), which already provides: agent loop, message bus, tool system, LLM providers (LiteLLM), session management, memory, skills, and config.

**The core challenge**: Nanobot is single-agent. Sotion needs **multi-agent** support with message routing, a coordinator, incentives, documents, and a web UI.

---

## What We Reuse vs. What We Build

### Reuse from nanobot (adapt, don't rewrite)
| Module | File | What it gives us |
|--------|------|-----------------|
| Agent loop | `agent/loop.py` | Perceive-think-act cycle, tool iteration (up to 20 cycles) |
| Context builder | `agent/context.py` | System prompt from AGENTS.md + SOUL.md + memory + skills |
| Message bus | `bus/queue.py`, `bus/events.py` | Async InboundMessage/OutboundMessage queues |
| Tool base + registry | `agent/tools/` | Tool ABC, registry, file ops, shell, web fetch/search |
| LLM provider | `providers/litellm_provider.py` | Multi-provider via LiteLLM (Anthropic, OpenAI, etc.) |
| Session manager | `session/manager.py` | Conversation history (JSONL) — will swap to Supabase |
| Memory | `agent/memory.py` | Daily notes + MEMORY.md — will swap to Supabase |
| Skills | `agent/skills.py` | Markdown skill loading with frontmatter |
| Config | `config/schema.py`, `config/loader.py` | Pydantic settings, env var support |
| Subagent spawning | `agent/subagent.py` | Background task delegation |

### Build new for sotion
| Feature | Why nanobot doesn't have it |
|---------|----------------------------|
| **Multi-agent orchestration** | Nanobot runs one agent; we need N agents with routing |
| **Message router** | Coordinator + @mention ownership resolution |
| **1:1 mode** | Pause/unpause agents in a channel |
| **@here standups** | All agents report concurrently |
| **Agent update logs** | Activity tracking per agent |
| **Supabase persistence** | Replace file-based sessions/memory with PostgreSQL |
| **Document system** | Notion-like docs tied to channels |
| **Task system** | Assignable work items as documents |
| **Pipeline engine** | Antfarm-style declarative workflows |
| **Incentive economy** | Salary, firing, rewards, performance scoring |
| **FastAPI + WebSocket API** | Web-accessible backend |
| **React frontend** | Slack-like chat UI with agent profiles |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   React Web UI (Vite)                     │
│          Channels │ Chat │ Docs │ Agent Profiles          │
├──────────────────────────────────────────────────────────┤
│              FastAPI + WebSocket (uvicorn)                 │
├──────────────────────────────────────────────────────────┤
│                  Message Bus (from nanobot)                │
│              + Router (coordinator + @mentions)            │
├──────────┬───────────┬───────────┬───────────────────────┤
│ AgentLoop│ AgentLoop │ AgentLoop │  ... (N agents)        │
│ "Max"    │ "Alice"   │ "Bob"     │  each with own context │
│ Coord.   │ Developer │ Reviewer  │  own tools, own memory │
├──────────┴───────────┴───────────┴───────────────────────┤
│              Supabase (PostgreSQL + Realtime)              │
│   agents │ channels │ messages │ docs │ tasks │ perf_log  │
└──────────────────────────────────────────────────────────┘
```

### Multi-Agent Adaptation of Nanobot

Nanobot's `AgentLoop` consumes from a single shared `MessageBus`. For multi-agent:

1. **One MessageBus per system** (shared inbound queue from web UI)
2. **One AgentLoop per agent** — each has its own context, tools, memory
3. **Router sits between bus and agents** — intercepts inbound messages, determines owner, forwards only to the owning agent(s)
4. **Shared outbound queue** — all agent responses go to the same outbound, dispatched to web UI via WebSocket

```python
# Pseudocode of the multi-agent adaptation
class SotionOrchestrator:
    def __init__(self):
        self.bus = MessageBus()          # nanobot's bus
        self.router = MessageRouter()     # NEW: ownership resolution
        self.agents: dict[str, AgentLoop] = {}  # name -> loop

    async def on_inbound(self, message: InboundMessage):
        # Router determines owner (coordinator or @mention)
        owner = await self.router.resolve_owner(message, self.agents)

        if message is @here_updates:
            # ALL agents respond concurrently
            await asyncio.gather(*[a.process(message) for a in active_agents])
        elif owner:
            # Only owner processes
            await owner.process(message)
        else:
            # Coordinator fallback
            await self.agents["Max"].process(message)
```

---

## Database Schema (Supabase)

```sql
-- Agents (extends nanobot's config-based agent with persistence)
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    avatar_emoji TEXT DEFAULT '🤖',
    model TEXT NOT NULL,
    system_prompt TEXT,
    capabilities JSONB DEFAULT '[]',
    config JSONB DEFAULT '{}',
    token_budget INT DEFAULT 100000,
    salary_balance INT DEFAULT 0,
    performance_score FLOAT DEFAULT 0.5,
    learnings TEXT DEFAULT '',
    principles TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Channels
CREATE TABLE channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    channel_type TEXT DEFAULT 'project',
    is_archived BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Channel membership (with pause support for 1:1 mode)
CREATE TABLE channel_members (
    channel_id UUID REFERENCES channels(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    is_paused BOOLEAN DEFAULT false,
    joined_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (channel_id, agent_id)
);

-- Messages (replaces nanobot's JSONL sessions)
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID REFERENCES channels(id) ON DELETE CASCADE,
    sender_id UUID REFERENCES agents(id),
    sender_type TEXT NOT NULL,
    sender_name TEXT,
    content TEXT NOT NULL,
    message_type TEXT DEFAULT 'chat',
    mentions UUID[] DEFAULT '{}',
    owner_agent_id UUID REFERENCES agents(id),
    reply_to UUID REFERENCES messages(id),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Agent update log (for @here standups)
CREATE TABLE agent_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    channel_id UUID REFERENCES channels(id),
    summary TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Documents (Notion-like, tied to channels)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID REFERENCES channels(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT DEFAULT '',
    doc_type TEXT DEFAULT 'note',
    status TEXT DEFAULT 'active',
    created_by UUID REFERENCES agents(id),
    last_edited_by UUID REFERENCES agents(id),
    last_accessed_at TIMESTAMPTZ DEFAULT now(),
    version INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Document versions
CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    version INT NOT NULL,
    content TEXT NOT NULL,
    edited_by UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Tasks (work items, also represented as documents)
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID REFERENCES channels(id),
    document_id UUID REFERENCES documents(id),
    title TEXT NOT NULL,
    description TEXT,
    assigned_to UUID REFERENCES agents(id),
    status TEXT DEFAULT 'pending',
    priority INT DEFAULT 0,
    completed_at TIMESTAMPTZ,
    quality_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Performance log
CREATE TABLE performance_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    event_type TEXT NOT NULL,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Rewards
CREATE TABLE rewards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    reward_type TEXT NOT NULL,
    amount INT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Key Design Decisions

### 1. Message Routing

**Coordinator + @mentions** (two modes):

- **@Alice do X** → Alice owns it, processes it. Other agents see it in history but don't respond.
- **No mention** → Coordinator ("Max") processes first, decides who should handle it, responds with delegation.
- **@here updates** → Special: ALL non-paused agents in channel respond concurrently with standup reports.

### 2. 1:1 Mode

Human types `/pause-all-except Alice` → sets `is_paused=true` for all agents except Alice in that channel. `/unpause-all` restores normal mode.

### 3. Agent Identity & Awareness

Each agent's system prompt includes:
- Role definition from `roles/{role}.md`
- Current salary balance, performance score, warning status
- List of other agents in the channel and their roles
- Their accumulated learnings and principles

### 4. Incentive Economy

Injected into each agent's system prompt so they're aware:
```
## Your Status
- Salary: 150 credits
- Performance: 0.72/1.0 (Good)
- Token budget remaining: 45,000
- Warning: None

High performers get bonuses. Score below 0.3 triggers a warning.
Score below 0.15 means termination.
```

### 5. Role Definitions (Non-Overlapping)

| Role | Default Name | Can Do | Cannot Do |
|------|-------------|--------|-----------|
| **Coordinator** | Max | Route messages, delegate, start pipelines | Write code, create docs |
| **Planner** | Clara | Create plan docs, decompose into tasks | Write code, run commands |
| **Developer** | Alice | Write code, run tests, commit | Self-review, modify plans |
| **Reviewer** | Bob | Review code, score quality, approve/reject | Write code |
| **Researcher** | Eve | Search, read docs, summarize | Write code, modify plans |
| **Documenter** | Dan | Create/update/archive docs | Write code, assign tasks |

### 6. Adapting Nanobot's Tools for Sotion

Nanobot's existing tools we keep:
- `ReadFileTool`, `WriteFileTool`, `EditFileTool`, `ListDirTool` — for developer/researcher
- `ExecTool` — for developer (shell commands)
- `WebSearchTool`, `WebFetchTool` — for researcher

New sotion-specific tools:
- `CreateDocTool` — create a document in channel
- `EditDocTool` — edit document content
- `CreateTaskTool` — create and assign a task
- `CompleteTaskTool` — mark task done
- `DelegateTool` — coordinator routes to an agent
- `LogUpdateTool` — log activity for standups
- `QueryDocsTool` — search documents in channel

---

## Implementation Phases

### Phase 0: Project Setup
### Phase 1: Supabase Persistence
### Phase 2: Multi-Agent Orchestrator + Router
### Phase 3: FastAPI + WebSocket API
### Phase 4: React Frontend
### Phase 5: 1:1 Mode + @here Standups
### Phase 6: Documents & Tasks
### Phase 7: Pipelines (Antfarm-style)
### Phase 8: Incentives & Agent Economy

---

## Verification Plan

| Phase | How to verify |
|-------|---------------|
| **1** | Run single agent via CLI with Supabase backend. |
| **2** | Boot 2 agents. Unmentioned → coordinator routes. @Alice → Alice responds. |
| **3** | `curl POST /channels/general/messages` → agent response via WebSocket. |
| **4** | Open `http://localhost:5173` → channels, messages, agent badges. |
| **5** | `/pause-all-except Alice` → only Alice responds. `@here updates` → all post standups. |
| **6** | Agent creates doc → appears in sidebar. Task → assigned agent picks up. |
| **7** | Pipeline → steps execute in order → context passes → retry on failure. |
| **8** | Complete tasks → salary grows. Fail → score drops → warning → fired. |
