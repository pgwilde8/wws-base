-- Add secondary_phone column to webwise.brokers table
-- Run with: psql "$DATABASE_URL" -f sql/add_secondary_phone.sql

ALTER TABLE webwise.brokers 
ADD COLUMN IF NOT EXISTS secondary_phone VARCHAR(50);

COMMENT ON COLUMN webwise.brokers.secondary_phone IS 'Additional phone number for brokers with multiple contact lines';
