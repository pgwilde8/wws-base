-- Migration: Purge vesting logic, align with Automation Fuel model
-- Run: set -a && source .env && set +a && psql "$DATABASE_URL" -f sql/migrate_automation_fuel.sql
--
-- Changes:
-- 1. Migrate all LOCKED rows to CREDITED (immediate availability)
-- 2. No schema change to unlocks_at (column kept for compatibility)

BEGIN;

-- Migrate LOCKED -> CREDITED so all credits are immediately available
UPDATE webwise.driver_savings_ledger
SET status = 'CREDITED', unlocks_at = COALESCE(earned_at, NOW())
WHERE status = 'LOCKED';

COMMIT;
