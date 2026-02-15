-- Add message_id column for deduplication via Message-ID header
-- Run: psql "$DATABASE_URL" -f sql/add_messages_message_id.sql

ALTER TABLE webwise.messages ADD COLUMN IF NOT EXISTS message_id TEXT UNIQUE;
