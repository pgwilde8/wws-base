#!/usr/bin/env python3
"""Quick script to verify loads were ingested"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

print("🔍 Checking webwise.loads table...\n")

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT ref_id, origin, destination, price, status, created_at 
        FROM webwise.loads 
        ORDER BY created_at DESC 
        LIMIT 10
    """))
    
    rows = result.fetchall()
    
    if not rows:
        print("❌ No loads found in database")
    else:
        print(f"✅ Found {len(rows)} load(s):\n")
        print(f"{'Ref ID':<20} {'Origin':<20} {'Destination':<20} {'Price':<10} {'Status':<10}")
        print("-" * 90)
        for row in rows:
            ref_id = row[0] or "N/A"
            origin = row[1] or "N/A"
            dest = row[2] or "N/A"
            price = row[3] or "N/A"
            status = row[4] or "N/A"
            print(f"{ref_id:<20} {origin:<20} {dest:<20} {price:<10} {status:<10}")
