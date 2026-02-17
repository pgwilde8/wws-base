-- Ensure trucker_profiles has is_beta (beta drivers bypass Stripe).
-- Run: psql "$DATABASE_URL" -f sql/migrate_trucker_profiles_is_beta.sql
-- (If you already ran create_beta_driver_onboarding.sql, this does nothing — safe.)

BEGIN;

ALTER TABLE webwise.trucker_profiles
ADD COLUMN IF NOT EXISTS is_beta BOOLEAN NOT NULL DEFAULT FALSE;

COMMIT;
