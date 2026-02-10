-- Add DM support to channels table
-- Phase 5.5: Proper DM architecture

-- Add dm_participant_agent_id field to channels table
ALTER TABLE channels
ADD COLUMN IF NOT EXISTS dm_participant_agent_id UUID REFERENCES agents(id);

-- Add index for DM lookups (performance optimization)
CREATE INDEX IF NOT EXISTS idx_channels_dm_participant
ON channels(dm_participant_agent_id)
WHERE channel_type = 'dm';

-- Add index on channel_type for faster filtering
CREATE INDEX IF NOT EXISTS idx_channels_type
ON channels(channel_type);

-- Optional: Migrate existing "paused channel mode" to proper DMs
-- This converts channels where all-but-one agents are paused into DM type
-- Uncomment if you want to migrate existing data:

/*
UPDATE channels SET
  channel_type = 'dm',
  dm_participant_agent_id = (
    SELECT agent_id
    FROM channel_members
    WHERE channel_id = channels.id
      AND NOT is_paused
    LIMIT 1
  )
WHERE id IN (
  SELECT channel_id
  FROM channel_members
  GROUP BY channel_id
  HAVING COUNT(*) FILTER (WHERE NOT is_paused) = 1
    AND COUNT(*) > 1
);
*/
