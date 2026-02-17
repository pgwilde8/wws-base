-- Beta driver activation tracking: see where drivers drop off.
-- Run: psql "$DATABASE_URL" -f sql/migrate_beta_activation.sql
--
-- Stages: APPROVED | LOGGED_IN | PROFILE_COMPLETED | FIRST_SCOUT | FIRST_NEGOTIATION
--        | FIRST_LOAD_WON | FIRST_LOAD_FUNDED | ACTIVE

BEGIN;

ALTER TABLE webwise.trucker_profiles
  ADD COLUMN IF NOT EXISTS beta_onboarded_at TIMESTAMPTZ NULL,
  ADD COLUMN IF NOT EXISTS beta_last_activity_at TIMESTAMPTZ NULL,
  ADD COLUMN IF NOT EXISTS beta_activation_stage TEXT DEFAULT 'APPROVED';

CREATE INDEX IF NOT EXISTS ix_trucker_profiles_is_beta
  ON webwise.trucker_profiles (is_beta, beta_activation_stage);

COMMIT;
