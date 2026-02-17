-- Add payment tracking fields to factoring_referrals for refund capability
-- Run: psql "$DATABASE_URL" -f sql/add_factoring_payment_fields.sql

BEGIN;

ALTER TABLE webwise.factoring_referrals
ADD COLUMN IF NOT EXISTS payment_intent_id TEXT,
ADD COLUMN IF NOT EXISTS refunded_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_factoring_referrals_payment_intent
ON webwise.factoring_referrals(payment_intent_id);

CREATE INDEX IF NOT EXISTS ix_factoring_referrals_refunded_at
ON webwise.factoring_referrals(refunded_at);

COMMENT ON COLUMN webwise.factoring_referrals.payment_intent_id IS 'Stripe PaymentIntent ID for refund capability';
COMMENT ON COLUMN webwise.factoring_referrals.refunded_at IS 'Timestamp when refund was processed (if declined by Century)';

COMMIT;
