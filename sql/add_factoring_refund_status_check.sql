-- Add CHECK constraint on refund_status (optional safety)
-- Run: cd client/dispatch && set -a && source .env && set +a && psql "$DATABASE_URL" -f sql/add_factoring_refund_status_check.sql

BEGIN;

ALTER TABLE webwise.factoring_referrals
DROP CONSTRAINT IF EXISTS chk_factoring_referrals_refund_status;

ALTER TABLE webwise.factoring_referrals
ADD CONSTRAINT chk_factoring_referrals_refund_status
CHECK (refund_status IS NULL OR refund_status IN ('PENDING', 'SUCCEEDED', 'FAILED'));

COMMIT;
