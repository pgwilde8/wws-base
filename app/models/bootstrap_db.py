# bootstrap_db.py
# Export Base (and optionally engine) for ORM models. Run this file as a script to create schema and seed.
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

try:
    from dotenv import load_dotenv
    # bootstrap_db.py is in app/models/, so go up 3 levels to project root
    _base_dir = Path(__file__).resolve().parent.parent.parent
    load_dotenv(_base_dir / ".env")
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=True, future=True) if DATABASE_URL else None


def _hash_password(password: str) -> str:
    """Hash for bootstrap seeding. Use bcrypt directly to avoid passlib/bcrypt 4.1+ issues."""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except Exception as e:
        raise RuntimeError("bcrypt is required for bootstrap; pip install bcrypt") from e


def run_bootstrap():
    """Create webwise schema, tables, and seed data. Call when running this file as __main__."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set in environment")
    eng = create_engine(DATABASE_URL, echo=True, future=True)
    with eng.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS webwise;"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS webwise.projects (
                id SERIAL PRIMARY KEY,
                client_name VARCHAR(120) NOT NULL,
                project_title VARCHAR(200) NOT NULL,
                created_at TIMESTAMP DEFAULT now()
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS webwise.testimonials (
                id SERIAL PRIMARY KEY,
                client_name VARCHAR(120) NOT NULL,
                email VARCHAR(200),
                client_location VARCHAR(200),
                website_url VARCHAR(300),
                event_type VARCHAR(100),
                rating INTEGER,
                testimonial_text TEXT NOT NULL,
                is_approved BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT now()
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS webwise.negotiations (
                id SERIAL PRIMARY KEY,
                load_id VARCHAR(64),
                origin VARCHAR(255),
                destination VARCHAR(255),
                original_rate FLOAT,
                target_rate FLOAT,
                final_rate FLOAT,
                ai_draft_subject VARCHAR(500),
                ai_draft_body TEXT,
                broker_reply TEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT now(),
                updated_at TIMESTAMP
            );
        """))
        # Add token usage tracking columns if they don't exist
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_schema = 'webwise' 
                               AND table_name = 'negotiations' 
                               AND column_name = 'ai_prompt_tokens') THEN
                    ALTER TABLE webwise.negotiations ADD COLUMN ai_prompt_tokens INTEGER DEFAULT 0;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_schema = 'webwise' 
                               AND table_name = 'negotiations' 
                               AND column_name = 'ai_completion_tokens') THEN
                    ALTER TABLE webwise.negotiations ADD COLUMN ai_completion_tokens INTEGER DEFAULT 0;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_schema = 'webwise' 
                               AND table_name = 'negotiations' 
                               AND column_name = 'ai_total_tokens') THEN
                    ALTER TABLE webwise.negotiations ADD COLUMN ai_total_tokens INTEGER DEFAULT 0;
                END IF;
            END $$;
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS webwise.users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'admin',
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT now(),
                last_login TIMESTAMP,
                factoring_company VARCHAR(255),
                referral_status VARCHAR(50) DEFAULT 'NONE'
            );
        """))
        # Add columns if they don't exist (for existing databases)
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_schema = 'webwise' 
                               AND table_name = 'users' 
                               AND column_name = 'factoring_company') THEN
                    ALTER TABLE webwise.users ADD COLUMN factoring_company VARCHAR(255);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_schema = 'webwise' 
                               AND table_name = 'users' 
                               AND column_name = 'referral_status') THEN
                    ALTER TABLE webwise.users ADD COLUMN referral_status VARCHAR(50) DEFAULT 'NONE';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_schema = 'webwise' 
                               AND table_name = 'users' 
                               AND column_name = 'location_code') THEN
                    ALTER TABLE webwise.users ADD COLUMN location_code VARCHAR(50);
                    CREATE INDEX IF NOT EXISTS idx_users_location_code ON webwise.users(location_code);
                END IF;
            END $$;
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS webwise.trucker_profiles (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES webwise.users(id),
                display_name VARCHAR(120) NOT NULL,
                carrier_name VARCHAR(200),
                truck_identifier VARCHAR(80),
                mc_number VARCHAR(50),
                created_at TIMESTAMP DEFAULT now(),
                updated_at TIMESTAMP
            );
        """))
        conn.execute(text("""
            DO $$ BEGIN
                ALTER TABLE webwise.negotiations
                ADD COLUMN trucker_id INTEGER REFERENCES webwise.trucker_profiles(id);
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$;
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS webwise.notifications (
                id SERIAL PRIMARY KEY,
                trucker_id INTEGER NOT NULL REFERENCES webwise.trucker_profiles(id),
                message VARCHAR(500) NOT NULL,
                notif_type VARCHAR(50) NOT NULL DEFAULT 'info',
                is_read BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMP DEFAULT now()
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS webwise.loads (
                id SERIAL PRIMARY KEY,
                ref_id VARCHAR(200) UNIQUE NOT NULL,
                origin VARCHAR(200),
                destination VARCHAR(200),
                price VARCHAR(50),
                equipment_type VARCHAR(50),
                pickup_date VARCHAR(100),
                status VARCHAR(50) DEFAULT 'NEW',
                raw_data JSONB,
                created_at TIMESTAMP DEFAULT now(),
                updated_at TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_loads_ref_id ON webwise.loads(ref_id);
            CREATE INDEX IF NOT EXISTS idx_loads_status ON webwise.loads(status);
        """))
        conn.execute(text("""
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
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_driver_mc ON webwise.driver_savings_ledger(driver_mc_number);
        """))
        existing = conn.execute(text("SELECT COUNT(*) FROM webwise.projects;")).scalar()
        if existing == 0:
            conn.execute(text("""
                INSERT INTO webwise.projects (client_name, project_title)
                VALUES ('Demo Client', 'Latin Placeholder Project');
            """))
        admin_count = conn.execute(text("SELECT COUNT(*) FROM webwise.users WHERE role='admin';")).scalar()
        if admin_count == 0:
            seed_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
            seed_password = (os.getenv("ADMIN_PASSWORD") or "changeme123")[:72]
            pw_hash = _hash_password(seed_password)
            conn.execute(text("""
                INSERT INTO webwise.users (email, password_hash, role, is_active)
                VALUES (:email, :password_hash, 'admin', true)
            """), {"email": seed_email, "password_hash": pw_hash})
        client_email = os.getenv("CLIENT_EMAIL")
        client_password = os.getenv("CLIENT_PASSWORD")
        if client_email and client_password:
            existing_client = conn.execute(text("SELECT COUNT(*) FROM webwise.users WHERE email = :email"), {"email": client_email}).scalar()
            if existing_client == 0:
                client_pw_hash = _hash_password((client_password or "")[:72])
                conn.execute(text("""
                    INSERT INTO webwise.users (email, password_hash, role, is_active)
                    VALUES (:email, :password_hash, 'client', true)
                """), {"email": client_email, "password_hash": client_pw_hash})
                print(f"Seeded client user: {client_email}")
    print("Bootstrap complete: schema 'webwise' and tables ready.")


if __name__ == "__main__":
    run_bootstrap()
