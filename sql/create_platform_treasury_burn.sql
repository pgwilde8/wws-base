-- webwise platform treasury + burn tables
-- Requires: pgcrypto for gen_random_uuid()

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS webwise;

-- -------------------------------
-- platform_revenue_ledger
-- -------------------------------
CREATE TABLE IF NOT EXISTS webwise.platform_revenue_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    source_type VARCHAR(50) NOT NULL,
    source_ref TEXT NULL,

    load_id TEXT NULL,
    driver_mc_number VARCHAR(50) NULL,

    gross_amount_usd NUMERIC(12,2) NOT NULL,

    burn_reserved_usd NUMERIC(12,2) NOT NULL DEFAULT 0,
    treasury_reserved_usd NUMERIC(12,2) NOT NULL DEFAULT 0,

    burn_batch_id UUID NULL,

    status VARCHAR(50) NOT NULL DEFAULT 'RECORDED',

    burn_eligible BOOLEAN NOT NULL DEFAULT true,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Unique on source_ref when not null
CREATE UNIQUE INDEX IF NOT EXISTS uq_platform_revenue_ledger_source_ref_not_null
ON webwise.platform_revenue_ledger (source_ref)
WHERE source_ref IS NOT NULL;

-- Indexes
CREATE INDEX IF NOT EXISTS ix_platform_revenue_ledger_created_at
ON webwise.platform_revenue_ledger (created_at DESC);

CREATE INDEX IF NOT EXISTS ix_platform_revenue_ledger_status
ON webwise.platform_revenue_ledger (status);

CREATE INDEX IF NOT EXISTS ix_platform_revenue_ledger_burn_batch_id
ON webwise.platform_revenue_ledger (burn_batch_id);

-- Reserve scan by period (status + created_at)
CREATE INDEX IF NOT EXISTS ix_platform_revenue_ledger_status_created_at
ON webwise.platform_revenue_ledger (status, created_at DESC);

-- -------------------------------
-- burn_batches
-- -------------------------------
CREATE TABLE IF NOT EXISTS webwise.burn_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    period_start TIMESTAMPTZ NOT NULL,
    period_end   TIMESTAMPTZ NOT NULL,

    burn_rate_bps INT NOT NULL,

    usd_reserved NUMERIC(12,2) NOT NULL DEFAULT 0,
    usd_spent    NUMERIC(12,2) NULL,

    candle_burned NUMERIC(18,8) NULL,

    swap_tx_hash TEXT NULL,
    burn_tx_hash TEXT NULL,

    status VARCHAR(50) NOT NULL DEFAULT 'CREATED',

    chain VARCHAR(20) NOT NULL DEFAULT 'base',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    executed_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_burn_batches_created_at
ON webwise.burn_batches (created_at DESC);

CREATE INDEX IF NOT EXISTS ix_burn_batches_status
ON webwise.burn_batches (status);

-- -------------------------------
-- treasury_wallets
-- -------------------------------
CREATE TABLE IF NOT EXISTS webwise.treasury_wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    wallet_name VARCHAR(50) NOT NULL,
    address TEXT NOT NULL,

    chain VARCHAR(20) NOT NULL DEFAULT 'base',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Unique on (wallet_name, chain)
CREATE UNIQUE INDEX IF NOT EXISTS uq_treasury_wallets_wallet_name_chain
ON webwise.treasury_wallets (wallet_name, chain);

-- FK: ledger.burn_batch_id -> burn_batches.id (soft: SET NULL on delete)
ALTER TABLE webwise.platform_revenue_ledger
  ADD CONSTRAINT fk_platform_revenue_ledger_burn_batch
  FOREIGN KEY (burn_batch_id)
  REFERENCES webwise.burn_batches(id)
  ON DELETE SET NULL;

COMMIT;
