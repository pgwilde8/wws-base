-- Store bucket + key only (not public URL). Backend generates URLs dynamically.
-- Run: psql "$DATABASE_URL" -f sql/migrate_load_documents_bucket_key.sql

BEGIN;

-- Add bucket and file_key; keep file_url for legacy/backfill and optional display URL cache
ALTER TABLE webwise.load_documents
  ADD COLUMN IF NOT EXISTS bucket VARCHAR(255),
  ADD COLUMN IF NOT EXISTS file_key TEXT;

-- Allow file_url to be null for rows that only have bucket+key
ALTER TABLE webwise.load_documents ALTER COLUMN file_url DROP NOT NULL;

-- Backfill file_key from existing file_url (parse key from DO Spaces URL or path)
UPDATE webwise.load_documents
SET
  bucket = COALESCE(bucket, (regexp_match(file_url, 'https?://[^/]+/([^/]+)/'))[1]),
  file_key = COALESCE(file_key, (regexp_match(file_url, 'https?://[^/]+/[^/]+/(.+)$'))[1])
WHERE file_url IS NOT NULL AND file_url <> ''
  AND (file_key IS NULL OR file_key = '')
  AND (file_url LIKE '%digitaloceanspaces.com%' OR file_url LIKE '%/dispatch/%');

-- If bucket still null, set default; app uses DO_SPACES_BUCKET from env
UPDATE webwise.load_documents SET bucket = 'greencandle' WHERE bucket IS NULL AND file_key IS NOT NULL;

COMMIT;
