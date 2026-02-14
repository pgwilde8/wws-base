-- Email candidates per broker: many emails per MC, with source and confidence.
-- Run after webwise.brokers exists: psql "$DATABASE_URL" -f sql/create_webwise_broker_emails.sql

CREATE TABLE IF NOT EXISTS webwise.broker_emails (
  id BIGSERIAL PRIMARY KEY,
  mc_number VARCHAR(20) NOT NULL REFERENCES webwise.brokers(mc_number) ON DELETE CASCADE,
  email TEXT NOT NULL,
  source TEXT NOT NULL,                 -- carrier_packet | website | reply | fmcsa | manual
  confidence NUMERIC(4,3) NOT NULL DEFAULT 0.300,
  evidence TEXT NULL,                   -- filename, url, snippet
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (mc_number, email)
);

CREATE INDEX IF NOT EXISTS idx_broker_emails_mc ON webwise.broker_emails(mc_number);
CREATE INDEX IF NOT EXISTS idx_broker_emails_email ON webwise.broker_emails(email);
