-- Legacy prototype tables may exist in older hackathon databases.
DROP TABLE IF EXISTS ai_chat_summaries CASCADE;
DROP TABLE IF EXISTS ai_chat_messages CASCADE;
DROP TABLE IF EXISTS ai_users CASCADE;

DROP FUNCTION IF EXISTS ai_set_updated_at() CASCADE;
