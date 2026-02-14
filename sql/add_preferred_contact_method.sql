-- Add preferred_contact_method column to webwise.brokers table
-- Values: 'email' (default), 'phone', 'call_to_book'
-- Run with: psql "$DATABASE_URL" -f sql/add_preferred_contact_method.sql

ALTER TABLE webwise.brokers 
ADD COLUMN IF NOT EXISTS preferred_contact_method VARCHAR(20) DEFAULT 'email';

COMMENT ON COLUMN webwise.brokers.preferred_contact_method IS 'Preferred contact method: email (default), phone, or call_to_book (requires phone call)';

-- Update existing brokers with 'call_to_book' if they have phone but no email
UPDATE webwise.brokers
SET preferred_contact_method = 'call_to_book'
WHERE (primary_phone IS NOT NULL AND primary_phone != '')
  AND (primary_email IS NULL OR primary_email = '');
