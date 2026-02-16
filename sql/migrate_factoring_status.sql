-- Run: set -a && source .env && set +a && psql "$DATABASE_URL" -f sql/migrate_factoring_status.sql
-- Adds factoring_status and factored_at to negotiations for tracking packet submissions.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_schema = 'webwise' AND table_name = 'negotiations'
                  AND column_name = 'factoring_status') THEN
        ALTER TABLE webwise.negotiations ADD COLUMN factoring_status VARCHAR(20) DEFAULT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_schema = 'webwise' AND table_name = 'negotiations'
                  AND column_name = 'factored_at') THEN
        ALTER TABLE webwise.negotiations ADD COLUMN factored_at TIMESTAMP DEFAULT NULL;
    END IF;
END $$;
