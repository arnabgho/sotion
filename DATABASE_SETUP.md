# Database Setup Guide

This guide will help you set up the Supabase database for Sotion.

## Prerequisites

- A Supabase account (free tier works fine)
- Project created in Supabase dashboard

## Step 1: Get Your Supabase Credentials

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard)
2. Select your project (or create a new one)
3. Navigate to **Settings** → **API**
4. Copy these values:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **anon public** key
   - **service_role** secret key (⚠️ keep this secret!)

## Step 2: Configure Environment Variables

Edit your `.env` file:

```bash
SOTION_SUPABASE__URL=https://your-project.supabase.co
SOTION_SUPABASE__ANON_KEY=your-anon-key-here
SOTION_SUPABASE__SERVICE_ROLE_KEY=your-service-role-key-here
```

## Step 3: Run Database Migrations

### Option A: Via Supabase Dashboard (Easiest)

1. In your Supabase dashboard, click **SQL Editor** in the left sidebar
2. Click **+ New query**

3. **First Migration** (Create Tables):
   - Open `sotion/db/migrations/001_initial.sql` in a text editor
   - Copy all the SQL
   - Paste into the Supabase SQL Editor
   - Click **Run** (or press Ctrl/Cmd + Enter)
   - Wait for "Success. No rows returned"

4. **Second Migration** (Seed Default Agents):
   - Open `sotion/db/migrations/002_seed_agents.sql`
   - Copy all the SQL
   - Paste into a new query in Supabase SQL Editor
   - Click **Run**
   - You should see "Success" with 6 agents created

### Option B: Via Supabase CLI

```bash
# Install Supabase CLI
npm install -g supabase

# Login to Supabase
supabase login

# Link your project (find project ref in dashboard URL or settings)
supabase link --project-ref your-project-ref

# Run migrations
supabase db push
```

## Step 4: Verify Setup

Back in the Supabase dashboard:

1. Go to **Table Editor**
2. You should see these tables:
   - `agents` (should have 6 rows: Max, Alice, Bob, Clara, Eve, Dan)
   - `channels` (should have 1 row: general)
   - `channel_members` (should have 6 rows)
   - `messages`
   - `documents`
   - `tasks`
   - `performance_log`
   - `rewards`
   - `agent_updates`
   - `document_versions`

## Step 5: Test the Server

```bash
sotion serve
```

You should see:
```
🧠 Starting sotion server on 0.0.0.0:8000...
INFO:     Supabase client initialized
INFO:     Supabase connected
INFO:     Sotion server started
```

Visit:
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Default Agents Created

| Name | Role | Avatar | Capabilities |
|------|------|--------|--------------|
| Max | Coordinator | 🎯 | Delegates, routes messages, starts pipelines |
| Alice | Developer | 👩‍💻 | Writes code, runs tests, git operations |
| Bob | Reviewer | 🔍 | Code review, quality scoring, security |
| Clara | Planner | 📋 | Creates plans, task decomposition |
| Eve | Researcher | 🔬 | Web search, documentation research |
| Dan | Documenter | 📝 | Creates and maintains documentation |

## Troubleshooting

### "Could not find the table 'public.agents'"

**Cause**: Database migrations not run yet.

**Solution**: Follow Step 3 above to run the migrations.

### "relation 'agents' already exists"

**Cause**: You've already run the migrations.

**Solution**: This is fine! The migrations use `IF NOT EXISTS` so they're safe to run multiple times.

### "permission denied for table agents"

**Cause**: Using anon key instead of service_role key.

**Solution**: Make sure you set `SOTION_SUPABASE__SERVICE_ROLE_KEY` in your `.env` file, not the anon key.

### Server starts but no agents appear

**Cause**: Seed migration not run.

**Solution**: Run `002_seed_agents.sql` in Supabase SQL Editor.

### "Supabase not configured — running without persistence"

**Cause**: Missing Supabase credentials in `.env` file.

**Solution**: Set all three Supabase env vars:
- `SOTION_SUPABASE__URL`
- `SOTION_SUPABASE__ANON_KEY`
- `SOTION_SUPABASE__SERVICE_ROLE_KEY`

## Next Steps

Once your database is set up:

1. Start the server: `sotion serve`
2. Start the frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173
4. Start chatting with your AI team! 🎉

## Advanced: Resetting the Database

If you need to start fresh:

```sql
-- ⚠️ WARNING: This deletes all data!
DROP TABLE IF EXISTS rewards CASCADE;
DROP TABLE IF EXISTS performance_log CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS document_versions CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS agent_updates CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS channel_members CASCADE;
DROP TABLE IF EXISTS channels CASCADE;
DROP TABLE IF EXISTS agents CASCADE;
```

Then run the migrations again from Step 3.
