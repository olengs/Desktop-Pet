CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION ai_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
  IF to_regclass('public.ai_game_stats') IS NULL
     AND to_regclass('public.ai_traits') IS NOT NULL THEN
    ALTER TABLE ai_traits RENAME TO ai_game_stats;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'ai_game_history'
      AND column_name = 'stats'
  ) AND NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'ai_game_history'
      AND column_name = 'averaged_stats'
  ) THEN
    ALTER TABLE ai_game_history RENAME COLUMN stats TO averaged_stats;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'ai_game_stats'
      AND column_name = 'scores'
  ) AND NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'ai_game_stats'
      AND column_name = 'averaged_stats'
  ) THEN
    ALTER TABLE ai_game_stats RENAME COLUMN scores TO averaged_stats;
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS ai_users (
  user_id TEXT PRIMARY KEY,
  display_name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS ai_users_set_updated_at ON ai_users;
CREATE TRIGGER ai_users_set_updated_at
BEFORE UPDATE ON ai_users
FOR EACH ROW
EXECUTE FUNCTION ai_set_updated_at();

CREATE TABLE IF NOT EXISTS ai_chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL REFERENCES ai_users(user_id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'text',
  request_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ai_chat_messages_user_created_idx
ON ai_chat_messages (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS ai_game_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL REFERENCES ai_users(user_id) ON DELETE CASCADE,
  game_name TEXT NOT NULL,
  averaged_stats JSONB NOT NULL DEFAULT '{}'::jsonb,
  event_type TEXT,
  match_id TEXT,
  summary TEXT,
  source TEXT NOT NULL DEFAULT 'desktop_pet',
  request_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ai_game_history_user_created_idx
ON ai_game_history (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ai_game_history_game_name_idx
ON ai_game_history (game_name);

DROP INDEX IF EXISTS ai_game_history_stats_gin_idx;
CREATE INDEX IF NOT EXISTS ai_game_history_averaged_stats_gin_idx
ON ai_game_history USING GIN (averaged_stats);

CREATE TABLE IF NOT EXISTS ai_game_stats (
  user_id TEXT NOT NULL REFERENCES ai_users(user_id) ON DELETE CASCADE,
  game_name TEXT NOT NULL,
  averaged_stats JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, game_name)
);

DROP INDEX IF EXISTS ai_traits_scores_gin_idx;
CREATE INDEX IF NOT EXISTS ai_game_stats_averaged_stats_gin_idx
ON ai_game_stats USING GIN (averaged_stats);

DROP TRIGGER IF EXISTS ai_traits_set_updated_at ON ai_game_stats;
DROP TRIGGER IF EXISTS ai_game_stats_set_updated_at ON ai_game_stats;
CREATE TRIGGER ai_game_stats_set_updated_at
BEFORE UPDATE ON ai_game_stats
FOR EACH ROW
EXECUTE FUNCTION ai_set_updated_at();

CREATE TABLE IF NOT EXISTS ai_memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL REFERENCES ai_users(user_id) ON DELETE CASCADE,
  memory_type TEXT NOT NULL,
  game_name TEXT,
  summary TEXT NOT NULL,
  summary_hash TEXT GENERATED ALWAYS AS (md5(summary)) STORED,
  traits_affected JSONB,
  source_type TEXT NOT NULL DEFAULT 'manual',
  source_id UUID,
  importance DOUBLE PRECISION NOT NULL DEFAULT 0.5,
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
  times_observed INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ,
  last_used_at TIMESTAMPTZ,
  CONSTRAINT ai_memories_importance_range CHECK (importance >= 0 AND importance <= 1),
  CONSTRAINT ai_memories_confidence_range CHECK (confidence >= 0 AND confidence <= 1),
  CONSTRAINT ai_memories_times_observed_positive CHECK (times_observed > 0),
  CONSTRAINT ai_memories_unique_summary UNIQUE (user_id, memory_type, source_type, summary_hash)
);

CREATE INDEX IF NOT EXISTS ai_memories_user_updated_idx
ON ai_memories (user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS ai_memories_game_name_idx
ON ai_memories (game_name);

CREATE INDEX IF NOT EXISTS ai_memories_traits_affected_gin_idx
ON ai_memories USING GIN (traits_affected);

DROP TRIGGER IF EXISTS ai_memories_set_updated_at ON ai_memories;
CREATE TRIGGER ai_memories_set_updated_at
BEFORE UPDATE ON ai_memories
FOR EACH ROW
EXECUTE FUNCTION ai_set_updated_at();
