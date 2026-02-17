-- Factoring Referrals Table
-- Tracks referrals to Century Finance (and future factoring partners)

BEGIN;

CREATE TABLE IF NOT EXISTS webwise.factoring_referrals (
    id SERIAL PRIMARY KEY,
    
    -- Driver information
    trucker_id INTEGER REFERENCES webwise.trucker_profiles(id) ON DELETE SET NULL,
    driver_mc_number TEXT,
    
    -- Contact information
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    cell_phone TEXT NOT NULL,
    secondary_phone TEXT,
    company_name TEXT,
    
    -- Factoring details
    number_of_trucks INTEGER NOT NULL,
    interested_fuel_card BOOLEAN DEFAULT false,
    
    -- Optional fields (helpful for Alma)
    estimated_monthly_volume NUMERIC(12,2),
    current_factoring_company TEXT,
    preferred_funding_speed TEXT, -- 'same-day' or 'next-day'
    
    -- Referral tracking
    referral_code TEXT NOT NULL DEFAULT 'GREEN CANDLE',
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, CONTACTED, SIGNED, DECLINED
    
    -- Metadata
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    contacted_at TIMESTAMPTZ,
    signed_at TIMESTAMPTZ,
    notes TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_factoring_referrals_trucker_id
ON webwise.factoring_referrals(trucker_id);

CREATE INDEX IF NOT EXISTS ix_factoring_referrals_mc_number
ON webwise.factoring_referrals(driver_mc_number);

CREATE INDEX IF NOT EXISTS ix_factoring_referrals_status
ON webwise.factoring_referrals(status);

CREATE INDEX IF NOT EXISTS ix_factoring_referrals_submitted_at
ON webwise.factoring_referrals(submitted_at DESC);

COMMENT ON TABLE webwise.factoring_referrals IS 'Tracks referrals to factoring partners (Century Finance, etc.)';
COMMENT ON COLUMN webwise.factoring_referrals.referral_code IS 'Referral code for tracking (e.g., GREEN CANDLE, GC-REF-MC123)';
COMMENT ON COLUMN webwise.factoring_referrals.status IS 'PENDING = submitted, CONTACTED = Alma reached out, SIGNED = driver signed up, DECLINED = driver declined';

COMMIT;
