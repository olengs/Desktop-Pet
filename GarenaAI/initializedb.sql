CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION ai_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS ai_users (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  display_name TEXT NOT NULL UNIQUE,
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
  user_id UUID NOT NULL REFERENCES ai_users(user_id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'text',
  request_id TEXT,
  summarized_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ai_chat_messages_user_created_idx
ON ai_chat_messages (user_id, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS ai_chat_messages_user_unsummarized_idx
ON ai_chat_messages (user_id, created_at DESC, id DESC)
WHERE summarized_at IS NULL;

CREATE TABLE IF NOT EXISTS ai_chat_summaries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES ai_users(user_id) ON DELETE CASCADE,
  summary TEXT NOT NULL,
  summarized_message_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ai_chat_summaries_user_created_idx
ON ai_chat_summaries (user_id, created_at DESC, id DESC);

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS game (
  game_id UUID PRIMARY KEY,
  game_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS user_game_data (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES ai_users(user_id),
  game_id UUID NOT NULL REFERENCES game(game_id),
  game_data VECTOR NOT NULL
);

CREATE INDEX IF NOT EXISTS user_game_data_embedding_idx
ON user_game_data USING hnsw (game_data vector_cosine_ops);

CREATE INDEX IF NOT EXISTS user_game_data_user_game_idx
ON user_game_data (user_id, game_id);
