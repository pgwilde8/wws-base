-- Run: psql "$DATABASE_URL" -f sql/migrate_load_documents.sql
-- Creates load_documents table for BOL / RateCon / Lumper tracking.

CREATE TABLE IF NOT EXISTS webwise.load_documents (
    id SERIAL PRIMARY KEY,
    load_id VARCHAR(100) NOT NULL,
    trucker_id INTEGER REFERENCES webwise.trucker_profiles(id) ON DELETE CASCADE,
    doc_type VARCHAR(20) NOT NULL DEFAULT 'BOL',  -- BOL, RateCon, Lumper
    file_url TEXT NOT NULL,
    processed BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_load_documents_load_id ON webwise.load_documents(load_id);
CREATE INDEX IF NOT EXISTS idx_load_documents_trucker_id ON webwise.load_documents(trucker_id);
