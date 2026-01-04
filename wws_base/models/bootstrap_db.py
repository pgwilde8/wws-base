# bootstrap_db.py
import os
from sqlalchemy import create_engine, text
from pathlib import Path

# optional dotenv load
try:
    from dotenv import load_dotenv
    base_dir = Path(__file__).resolve().parent.parent
    load_dotenv(base_dir / ".env")
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in environment")

engine = create_engine(DATABASE_URL, echo=True, future=True)

# This script runs safely even if DB/schema/table already exists
with engine.begin() as conn:
    # Ensure schema exists
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS webwise;"))

    # Create a minimal base table if not exists
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS webwise.projects (
            id SERIAL PRIMARY KEY,
            client_name VARCHAR(120) NOT NULL,
            project_title VARCHAR(200) NOT NULL,
            created_at TIMESTAMP DEFAULT now()
        );
    """))

    # Create testimonials table
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

    # Create users table
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS webwise.users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'admin',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT now(),
            last_login TIMESTAMP
        );
    """))

    # Optional seed row so UI has something to show
    existing = conn.execute(text("SELECT COUNT(*) FROM webwise.projects;")).scalar()

    if existing == 0:
        conn.execute(text("""
            INSERT INTO webwise.projects (client_name, project_title)
            VALUES ('Demo Client', 'Latin Placeholder Project');
        """))

    # Seed admin if none exists
    admin_count = conn.execute(text("SELECT COUNT(*) FROM webwise.users WHERE role='admin';")).scalar()
    if admin_count == 0:
        seed_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        seed_password = os.getenv("ADMIN_PASSWORD", "changeme123")
        try:
            from passlib.hash import bcrypt
            pw_hash = bcrypt.hash(seed_password)
        except Exception as exc:
            raise RuntimeError("passlib[bcrypt] is required to hash the seed admin password; install dependency and retry bootstrap") from exc
        conn.execute(text("""
            INSERT INTO webwise.users (email, password_hash, role, is_active)
            VALUES (:email, :password_hash, 'admin', true)
        """), {"email": seed_email, "password_hash": pw_hash})

    # Seed client if env provided
    client_email = os.getenv("CLIENT_EMAIL")
    client_password = os.getenv("CLIENT_PASSWORD")
    if client_email and client_password:
        existing_client = conn.execute(text("SELECT COUNT(*) FROM webwise.users WHERE email = :email"), {"email": client_email}).scalar()
        if existing_client == 0:
            try:
                from passlib.hash import bcrypt
                client_pw_hash = bcrypt.hash(client_password)
            except Exception as exc:
                raise RuntimeError("passlib[bcrypt] is required to hash the seed client password; install dependency and retry bootstrap") from exc
            conn.execute(text("""
                INSERT INTO webwise.users (email, password_hash, role, is_active)
                VALUES (:email, :password_hash, 'client', true)
            """), {"email": client_email, "password_hash": client_pw_hash})
            print(f"Seeded client user: {client_email}")
        else:
            print(f"Client user already exists: {client_email}; skipping seed")

print("Bootstrap complete: schema 'webwise' and tables 'projects', 'testimonials', and 'users' are ready.")
