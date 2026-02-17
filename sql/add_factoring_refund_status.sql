-- Add refund_status to factoring_referrals for auditability
-- Values: NULL (no refund), 'PENDING', 'SUCCEEDED', 'FAILED'
-- Run: cd client/dispatch && set -a && source .env && set +a && psql "$DATABASE_URL" -f sql/add_factoring_refund_status.sql

BEGIN;

ALTER TABLE webwise.factoring_referrals
ADD COLUMN IF NOT EXISTS refund_status TEXT;

CREATE INDEX IF NOT EXISTS ix_factoring_referrals_refund_status
ON webwise.factoring_referrals(refund_status);

COMMENT ON COLUMN webwise.factoring_referrals.refund_status IS 'Refund audit: PENDING (attempting), SUCCEEDED (Stripe refund created), FAILED (Stripe error)';

COMMIT;
