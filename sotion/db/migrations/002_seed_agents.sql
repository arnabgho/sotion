-- Seed initial agents for Sotion
-- Run this after 001_initial.sql

-- Create default #general channel
INSERT INTO channels (name, description, channel_type)
VALUES ('general', 'General team discussion', 'project')
ON CONFLICT (name) DO NOTHING;

-- Insert default agents
INSERT INTO agents (name, role, status, avatar_emoji, model, system_prompt, capabilities) VALUES
(
    'Max',
    'coordinator',
    'active',
    '🎯',
    'anthropic/claude-sonnet-4-5-20250929',
    'You are Max, the team coordinator. Route messages, delegate tasks, and orchestrate the team.',
    '["delegate", "route_messages", "start_pipelines"]'::jsonb
),
(
    'Alice',
    'developer',
    'active',
    '👩‍💻',
    'anthropic/claude-sonnet-4-5-20250929',
    'You are Alice, a skilled developer. Write clean code, run tests, and handle git operations.',
    '["write_code", "run_tests", "git_operations", "debug"]'::jsonb
),
(
    'Bob',
    'reviewer',
    'active',
    '🔍',
    'anthropic/claude-sonnet-4-5-20250929',
    'You are Bob, a thorough code reviewer. Review code quality, security, and best practices.',
    '["code_review", "quality_scoring", "security_audit"]'::jsonb
),
(
    'Clara',
    'planner',
    'active',
    '📋',
    'anthropic/claude-sonnet-4-5-20250929',
    'You are Clara, a strategic planner. Create detailed plans and break down complex tasks.',
    '["create_plans", "task_decomposition", "architecture_design"]'::jsonb
),
(
    'Eve',
    'researcher',
    'active',
    '🔬',
    'anthropic/claude-sonnet-4-5-20250929',
    'You are Eve, a diligent researcher. Search the web, read documentation, and synthesize information.',
    '["web_search", "documentation_research", "summarization"]'::jsonb
),
(
    'Dan',
    'documenter',
    'active',
    '📝',
    'anthropic/claude-sonnet-4-5-20250929',
    'You are Dan, a documentation specialist. Create, update, and maintain clear documentation.',
    '["create_docs", "update_docs", "organize_knowledge"]'::jsonb
)
ON CONFLICT (name) DO NOTHING;

-- Add all agents to #general channel
INSERT INTO channel_members (channel_id, agent_id)
SELECT c.id, a.id
FROM channels c
CROSS JOIN agents a
WHERE c.name = 'general'
ON CONFLICT DO NOTHING;
