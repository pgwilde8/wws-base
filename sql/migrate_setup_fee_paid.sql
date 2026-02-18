-- Universal flow: trucker_profiles.setup_fee_paid unlocks dashboard without Century approval.
-- Run: psql "$DATABASE_URL" -f sql/migrate_setup_fee_paid.sql

BEGIN;

ALTER TABLE webwise.trucker_profiles
ADD COLUMN IF NOT EXISTS setup_fee_paid BOOLEAN NOT NULL DEFAULT FALSE;

COMMIT;
