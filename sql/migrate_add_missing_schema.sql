-- Run: psql "$DATABASE_URL" -f sql/migrate_add_missing_schema.sql
-- Adds missing columns and scout_status table for existing databases.

-- 1. trucker_profiles.is_first_login
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'webwise' AND table_name = 'trucker_profiles' AND column_name = 'is_first_login') THEN
        ALTER TABLE webwise.trucker_profiles ADD COLUMN is_first_login BOOLEAN DEFAULT false;
    END IF;
END $$;

-- 2. negotiations.assigned_truck
DO $$ BEGIN
    ALTER TABLE webwise.negotiations ADD COLUMN assigned_truck VARCHAR(20);
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- 3. scout_status table
CREATE TABLE IF NOT EXISTS webwise.scout_status (
    trucker_id INTEGER PRIMARY KEY REFERENCES webwise.trucker_profiles(id) ON DELETE CASCADE,
    lanes TEXT,
    min_rpm FLOAT,
    active BOOLEAN DEFAULT false,
    updated_at TIMESTAMP DEFAULT now()
);
