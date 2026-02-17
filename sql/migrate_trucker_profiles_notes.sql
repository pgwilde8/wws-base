-- Add notes to trucker_profiles (stores PaymentIntent id for refund on decline).
-- Run: psql "$DATABASE_URL" -f sql/migrate_trucker_profiles_notes.sql

BEGIN;

ALTER TABLE webwise.trucker_profiles
ADD COLUMN IF NOT EXISTS notes TEXT;

COMMIT;
