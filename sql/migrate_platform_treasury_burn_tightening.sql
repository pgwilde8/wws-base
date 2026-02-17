-- Tightening migration: FK, reserve-scan index, burn_eligible.
-- Run only if you already have webwise.platform_revenue_ledger and webwise.burn_batches
-- from create_platform_treasury_burn.sql (without these changes).
--
-- Run: set -a && source .env && set +a && psql "$DATABASE_URL" -f sql/migrate_platform_treasury_burn_tightening.sql

BEGIN;

-- 1) burn_eligible: only reserve/burn rows confirmed (e.g. after factoring settlement)
ALTER TABLE webwise.platform_revenue_ledger
  ADD COLUMN IF NOT EXISTS burn_eligible BOOLEAN NOT NULL DEFAULT true;

-- 2) Reserve scan by period (status + created_at)
CREATE INDEX IF NOT EXISTS ix_platform_revenue_ledger_status_created_at
ON webwise.platform_revenue_ledger (status, created_at DESC);

-- 3) burn_batches.chain (multi-chain future)
ALTER TABLE webwise.burn_batches
  ADD COLUMN IF NOT EXISTS chain VARCHAR(20) NOT NULL DEFAULT 'base';

-- 4) FK (skip if already present)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'fk_platform_revenue_ledger_burn_batch'
  ) THEN
    ALTER TABLE webwise.platform_revenue_ledger
      ADD CONSTRAINT fk_platform_revenue_ledger_burn_batch
      FOREIGN KEY (burn_batch_id)
      REFERENCES webwise.burn_batches(id)
      ON DELETE SET NULL;
  END IF;
END $$;

COMMIT;
