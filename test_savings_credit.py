#!/usr/bin/env python3
"""Direct test of credit_driver_savings function"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.tokenomics import credit_driver_savings

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    sys.exit(1)

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)

print("🧪 Testing credit_driver_savings function directly...")
print(f"📊 Database: {DATABASE_URL.split('@')[-1]}")

db = SessionLocal()
try:
    result = credit_driver_savings(
        db=db,
        load_id="LOAD_TEST_DIRECT",
        mc_number="MC_TEST_001",
        fee_usd=60.00
    )
    
    if result:
        print("✅ SUCCESS: Savings credited!")
        
        # Verify it was inserted
        from sqlalchemy import text
        check = db.execute(text("""
            SELECT * FROM webwise.driver_savings_ledger 
            WHERE load_id = 'LOAD_TEST_DIRECT'
        """))
        row = check.fetchone()
        if row:
            print(f"✅ Verified: Entry found with ID {row[0]}")
            print(f"   MC: {row[1]}, Load: {row[2]}, USD: ${row[3]}, CANDLE: {row[4]}")
        else:
            print("❌ ERROR: Entry not found after insert!")
    else:
        print("❌ FAILED: Function returned False")
        
except Exception as e:
    print(f"❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
