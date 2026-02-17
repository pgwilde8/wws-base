-- Weekly invoice batching for drivers who don't use factoring.
-- Run: psql "$DATABASE_URL" -f sql/migrate_weekly_invoice_tracking.sql

BEGIN;

-- 1) platform_revenue_ledger: track which rows are in an invoice batch
ALTER TABLE webwise.platform_revenue_ledger
  ADD COLUMN IF NOT EXISTS invoice_batch_id UUID NULL,
  ADD COLUMN IF NOT EXISTS invoiced_at TIMESTAMPTZ NULL;

CREATE INDEX IF NOT EXISTS ix_platform_revenue_ledger_invoice_batch_id
  ON webwise.platform_revenue_ledger(invoice_batch_id);

CREATE INDEX IF NOT EXISTS ix_platform_revenue_ledger_driver_uninvoiced
  ON webwise.platform_revenue_ledger(driver_mc_number)
  WHERE invoice_batch_id IS NULL AND source_type = 'DISPATCH_FEE';

-- 2) Invoice batch table (one row per driver per week)
CREATE TABLE IF NOT EXISTS webwise.driver_invoice_batches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  driver_mc_number TEXT NOT NULL,

  period_start TIMESTAMPTZ NOT NULL,
  period_end TIMESTAMPTZ NOT NULL,

  total_amount_usd NUMERIC(12,2) NOT NULL,

  stripe_invoice_id TEXT NULL,

  status TEXT NOT NULL DEFAULT 'CREATED',

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at TIMESTAMPTZ NULL,
  paid_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_driver_invoice_batches_mc
  ON webwise.driver_invoice_batches(driver_mc_number);

CREATE INDEX IF NOT EXISTS ix_driver_invoice_batches_status_created
  ON webwise.driver_invoice_batches(status, created_at DESC);

-- 3) Billing method: FACTORING (default) | WEEKLY_INVOICE
ALTER TABLE webwise.trucker_profiles
  ADD COLUMN IF NOT EXISTS billing_method TEXT NULL;

-- 4) Beta application: capture agreement to weekly invoicing
ALTER TABLE webwise.beta_driver_applications
  ADD COLUMN IF NOT EXISTS billing_method TEXT NULL;

COMMIT;
