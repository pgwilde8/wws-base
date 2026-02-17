-- sql/create_beta_driver_onboarding.sql
-- Beta onboarding: application intake + admin approval path (no Stripe)

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS webwise;

-- 1) Add is_beta flag to trucker_profiles (so beta drivers can bypass Stripe)
ALTER TABLE webwise.trucker_profiles
ADD COLUMN IF NOT EXISTS is_beta BOOLEAN NOT NULL DEFAULT FALSE;

-- 2) Beta driver applications table (public intake)
CREATE TABLE IF NOT EXISTS webwise.beta_driver_applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- applicant contact
  full_name TEXT NOT NULL,
  email TEXT NOT NULL,
  phone TEXT NOT NULL,

  -- trucking identity
  mc_number VARCHAR(50) NOT NULL,
  carrier_name TEXT NULL,
  truck_type TEXT NULL,
  preferred_lanes TEXT NULL,
  factoring_company TEXT NULL,

  notes TEXT NULL,

  status TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING | APPROVED | REJECTED
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  decided_at TIMESTAMPTZ NULL,
  decided_by_user_id UUID NULL,

  -- link to created account on approval (optional convenience)
  created_user_id UUID NULL,
  created_trucker_profile_id UUID NULL
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS ix_beta_driver_applications_status_created_at
  ON webwise.beta_driver_applications (status, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_beta_driver_applications_mc_number
  ON webwise.beta_driver_applications (mc_number);

CREATE INDEX IF NOT EXISTS ix_beta_driver_applications_email
  ON webwise.beta_driver_applications (email);

-- Prevent duplicate pending applications for same email / mc_number
-- (Drivers can re-apply after REJECTED if you want)
CREATE UNIQUE INDEX IF NOT EXISTS uq_beta_driver_app_email_pending
  ON webwise.beta_driver_applications (email)
  WHERE status = 'PENDING';

CREATE UNIQUE INDEX IF NOT EXISTS uq_beta_driver_app_mc_pending
  ON webwise.beta_driver_applications (mc_number)
  WHERE status = 'PENDING';

COMMIT;
