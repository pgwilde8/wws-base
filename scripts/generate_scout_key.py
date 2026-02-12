#!/usr/bin/env python3
"""Generate a Scout API key for a trucker. Usage: python3 scripts/generate_scout_key.py [trucker_id]"""
import os
import sys
import secrets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.core.deps import engine
from sqlalchemy import text

if not engine:
    print("❌ Database engine not available. Check DATABASE_URL in .env")
    sys.exit(1)

# Optional: pass trucker_id as first arg, else use first trucker
trucker_id_arg = sys.argv[1] if len(sys.argv) > 1 else None

with engine.begin() as conn:
    if trucker_id_arg:
        row = conn.execute(
            text("SELECT id, display_name, mc_number FROM webwise.trucker_profiles WHERE id = :id"),
            {"id": int(trucker_id_arg)}
        ).fetchone()
    else:
        row = conn.execute(
            text("SELECT id, display_name, mc_number FROM webwise.trucker_profiles ORDER BY id LIMIT 1")
        ).fetchone()

    if not row:
        print("❌ No trucker profile found.")
        sys.exit(1)

    trucker_id, display_name, mc_number = row[0], row[1], row[2]
    new_key = secrets.token_hex(32)

    conn.execute(
        text("UPDATE webwise.trucker_profiles SET scout_api_key = :key, updated_at = now() WHERE id = :id"),
        {"key": new_key, "id": trucker_id}
    )

print("\n" + "=" * 60)
print("NEW SCOUT API KEY")
print("=" * 60)
print(f"Trucker: {display_name} (id={trucker_id}, MC={mc_number})")
print(f"\n{new_key}\n")
print("=" * 60)
print("Paste this key into the Green Candle Scout extension popup and click SAVE.")
print("=" * 60 + "\n")
