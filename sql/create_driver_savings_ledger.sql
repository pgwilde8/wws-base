-- Driver Savings Ledger Table
-- This table implements the "Golden Handcuffs" mechanism:
-- Drivers earn $CANDLE tokens but must wait 6 months before claiming them.

CREATE TABLE IF NOT EXISTS webwise.driver_savings_ledger (
    id SERIAL PRIMARY KEY,
    
    -- WHO: The Driver
    driver_mc_number VARCHAR(20) NOT NULL,
    
    -- WHAT: The Job that paid them
    load_id VARCHAR(50) NOT NULL,
    
    -- THE VALUE:
    amount_usd DECIMAL(10, 2) NOT NULL,    -- e.g., $60.00
    amount_candle DECIMAL(18, 4) NOT NULL, -- e.g., 60.0000 (1:1 peg for now) or calculated
    
    -- THE LOCK (Jersey Hustle Logic):
    earned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    unlocks_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '6 months'),
    
    -- STATUS:
    -- 'LOCKED': Still in the 6-month window
    -- 'VESTED': Time is up, they can claim
    -- 'CLAIMED': You sent the crypto to their wallet
    status VARCHAR(20) DEFAULT 'LOCKED',
    
    -- PROOF:
    tx_hash VARCHAR(66) -- The blockchain receipt (filled only after they claim)
);

-- Index for speed so the dashboard loads fast
CREATE INDEX IF NOT EXISTS idx_driver_mc ON webwise.driver_savings_ledger(driver_mc_number);
