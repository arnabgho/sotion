# Sotion 🤖

**Slack + Notion hybrid for managing AI agent teams**

Sotion is a multi-agent AI platform that combines the real-time communication of Slack with the documentation structure of Notion. Built on top of [nanobot](https://github.com/HKUDS/nanobot), it extends single-agent capabilities into a full team orchestration system.

## Features

- **Multi-Agent Orchestration** — Run multiple specialized AI agents (coordinator, developer, reviewer, planner, researcher, documenter) in parallel
- **Message Routing** — Smart @mention system and coordinator-based delegation
- **Real-time Chat** — Slack-like interface with channels and direct messaging
- **Document Management** — Notion-style documents with versioning and collaborative editing
- **Task System** — Assignable work items with status tracking and quality scoring
- **Agent Economy** — Performance tracking, salaries, budgets, and incentive system
- **Pipeline Engine** — Declarative workflow automation (Antfarm-style)
- **Web UI** — React + TypeScript frontend with real-time WebSocket updates

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   React Web UI (Vite)                     │
│          Channels │ Chat │ Docs │ Agent Profiles          │
├──────────────────────────────────────────────────────────┤
│              FastAPI + WebSocket (uvicorn)                 │
├──────────────────────────────────────────────────────────┤
│                  Message Bus + Router                      │
├──────────┬───────────┬───────────┬───────────────────────┤
│ AgentLoop│ AgentLoop │ AgentLoop │  ... (N agents)        │
│ "Max"    │ "Alice"   │ "Bob"     │  each with own context │
│ Coord.   │ Developer │ Reviewer  │  own tools, own memory │
├──────────┴───────────┴───────────┴───────────────────────┤
│              Supabase (PostgreSQL + Realtime)              │
│   agents │ channels │ messages │ docs │ tasks │ perf_log  │
└──────────────────────────────────────────────────────────┘
```

## Prerequisites

- **Python 3.11+** — Required for the backend
- **Node.js 18+** — Required for the frontend
- **Supabase Account** — For database and real-time features ([Sign up free](https://supabase.com))
- **Anthropic API Key** — For Claude models ([Get API key](https://console.anthropic.com))

## Quick Start

### 1. Clone and Install

```bash
# Clone the repository
git clone <your-repo-url>
cd sotion

# Install Python dependencies
pip install -e .

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Set Up Supabase

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to **Settings** → **API** and copy:
   - Project URL
   - `anon` public key
   - `service_role` secret key
3. Run the database migrations:

   **Via Supabase Dashboard (Recommended):**
   - Go to **SQL Editor** in your Supabase dashboard
   - Click **New query**
   - Copy the contents of `sotion/db/migrations/001_initial.sql`
   - Paste and click **Run**
   - Repeat for `sotion/db/migrations/002_seed_agents.sql` to add default agents

   **Via Supabase CLI:**
   ```bash
   # Install Supabase CLI if you haven't
   npm install -g supabase

   # Link your project
   supabase link --project-ref your-project-ref

   # Run migrations
   supabase db push
   ```

### 3. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your credentials:
# - SOTION_SUPABASE__URL
# - SOTION_SUPABASE__ANON_KEY
# - SOTION_SUPABASE__SERVICE_ROLE_KEY
# - SOTION_PROVIDERS__ANTHROPIC__API_KEY
```

### 4. Initialize Configuration

```bash
# Create initial config and workspace
sotion onboard
```

### 5. Start the Backend

```bash
# Start the FastAPI server (port 8000)
sotion serve
```

### 6. Start the Frontend

In a separate terminal:

```bash
cd frontend
npm run dev
# Open http://localhost:5173
```

## Usage

### CLI Mode (Single Agent)

For quick testing without the full web interface:

```bash
sotion agent -m "Hello, analyze the codebase structure"
```

### Web Interface

1. Open [http://localhost:5173](http://localhost:5173)
2. Navigate to a channel (e.g., #general)
3. Type messages to interact with agents:
   - `@Alice implement user authentication` — Direct message to Alice
   - `What's the status of the project?` — Coordinator (Max) responds
   - `@here updates` — All agents report their status

### Agent Roles

| Role | Name | Capabilities |
|------|------|-------------|
| **Coordinator** | Max | Message routing, delegation, pipeline orchestration |
| **Planner** | Clara | Create plans, decompose tasks, architecture design |
| **Developer** | Alice | Write code, run tests, git operations |
| **Reviewer** | Bob | Code review, quality scoring, approval/rejection |
| **Researcher** | Eve | Web search, documentation reading, research summaries |
| **Documenter** | Dan | Create/update docs, maintain documentation |

### Commands

```bash
# Start the API server
sotion serve

# Single-agent CLI mode
sotion agent -m "your message"

# Initialize configuration
sotion onboard

# Database migrations (coming soon)
# sotion db migrate
# sotion db seed
```

## Configuration

All configuration uses the `SOTION_` environment variable prefix with `__` as the nested delimiter.

See [.env.example](.env.example) for all available options.

### Key Settings

- **Workspace**: `~/.sotion/workspace` (default)
- **Model**: `anthropic/claude-sonnet-4-5-20250929` (default)
- **Server**: `http://0.0.0.0:8000` (default)
- **Frontend**: `http://localhost:5173` (development)

## Development

### Project Structure

```
sotion/
├── sotion/                 # Main Python package
│   ├── agents/            # Agent definitions and tools
│   ├── api/              # FastAPI routes
│   ├── bus/              # Message bus and routing
│   ├── db/               # Supabase client and models
│   ├── orchestrator.py   # Multi-agent coordinator
│   ├── pipelines/        # Workflow engine
│   ├── incentives/       # Agent economy
│   └── main.py           # FastAPI entry point
├── frontend/              # React + Vite UI
├── plans/                 # Design documents
└── workspace/             # Agent workspace (gitignored)
```

### Running Tests

```bash
# Python tests
pytest

# Frontend tests
cd frontend
npm test
```

### Code Style

```bash
# Format and lint
ruff check --fix sotion/
ruff format sotion/
```

## Features in Detail

### Message Routing

- **@mention** — Direct a message to a specific agent
- **No mention** — Coordinator decides who should handle it
- **@here** — All agents respond (e.g., for standups)

### 1:1 Mode

Pause all agents except one for focused interaction:

```
/pause-all-except Alice
# Only Alice responds now

/unpause-all
# All agents active again
```

### Documents & Tasks

- Create Notion-like documents in channels
- Version history with diff tracking
- Assign tasks to specific agents
- Quality scoring and performance tracking

### Incentive Economy

- Each agent has a salary balance and performance score
- High performers get bonuses
- Low performers get warnings
- Consistent failures lead to "termination" (agent paused)

## Roadmap

See [PLAN-v0.md](plans/PLAN-v0.md) for the full implementation plan.

- [x] Phase 0: Project Setup
- [ ] Phase 1: Supabase Persistence
- [ ] Phase 2: Multi-Agent Orchestrator
- [ ] Phase 3: FastAPI + WebSocket API
- [ ] Phase 4: React Frontend
- [ ] Phase 5: 1:1 Mode + @here Standups
- [ ] Phase 6: Documents & Tasks
- [ ] Phase 7: Pipeline Engine
- [ ] Phase 8: Incentive Economy

## Built With

- [nanobot](https://github.com/HKUDS/nanobot) — Single-agent AI framework foundation
- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [Supabase](https://supabase.com) — PostgreSQL database with real-time features
- [LiteLLM](https://github.com/BerriAI/litellm) — Multi-provider LLM interface
- [React](https://react.dev/) — Frontend UI library
- [Vite](https://vitejs.dev/) — Fast frontend build tool

## License

MIT License — See LICENSE file for details

## Contributing

This is an early-stage project. Contributions welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions:
- Open an issue on GitHub
- Check the [plans/](plans/) directory for design docs
- Review [MEMORY.md](.claude/projects/-Users-arnab-tinkering-projects-sotion/memory/MEMORY.md) for architecture notes

---

**Built on the shoulders of [nanobot](https://github.com/HKUDS/nanobot) 🤖**
