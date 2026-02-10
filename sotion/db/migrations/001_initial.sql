-- Sotion initial schema
-- Run against Supabase PostgreSQL

-- Agents
CREATE TABLE IF NOT EXISTS agents (
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
CREATE TABLE IF NOT EXISTS channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    channel_type TEXT DEFAULT 'project',
    is_archived BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Channel membership (with pause support for 1:1 mode)
CREATE TABLE IF NOT EXISTS channel_members (
    channel_id UUID REFERENCES channels(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    is_paused BOOLEAN DEFAULT false,
    joined_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (channel_id, agent_id)
);

-- Messages
CREATE TABLE IF NOT EXISTS messages (
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
CREATE TABLE IF NOT EXISTS agent_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    channel_id UUID REFERENCES channels(id),
    summary TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Documents
CREATE TABLE IF NOT EXISTS documents (
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
CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    version INT NOT NULL,
    content TEXT NOT NULL,
    edited_by UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Tasks
CREATE TABLE IF NOT EXISTS tasks (
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
CREATE TABLE IF NOT EXISTS performance_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    event_type TEXT NOT NULL,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Rewards
CREATE TABLE IF NOT EXISTS rewards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    reward_type TEXT NOT NULL,
    amount INT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_documents_channel ON documents(channel_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to, status);
CREATE INDEX IF NOT EXISTS idx_tasks_channel ON tasks(channel_id, status);
CREATE INDEX IF NOT EXISTS idx_performance_agent ON performance_log(agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_updates_agent ON agent_updates(agent_id, created_at DESC);
