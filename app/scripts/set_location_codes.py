"""
Script to set location_code for users (truck stop attribution).
Usage: python -m app.scripts.set_location_codes

Example: Set location_code for a user's referral_code
UPDATE webwise.users SET location_code = 'LOMBARDI_01' WHERE referral_code = 'ABC123';
"""
import os
from pathlib import Path
from sqlalchemy import create_engine, text

# Load .env
try:
    from dotenv import load_dotenv
    base_dir = Path(__file__).resolve().parent.parent.parent
    load_dotenv(base_dir / ".env")
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not set in environment")
    exit(1)

engine = create_engine(DATABASE_URL, echo=True)

# Example: Set location codes for specific referral codes
# You can modify this to match your truck stop codes
LOCATION_MAPPING = {
    # "REFERRAL_CODE": "LOCATION_CODE"
    # "ABC123": "LOMBARDI_01",
    # "XYZ789": "PITCHER_02",
}

def set_location_codes():
    """Set location_code for users based on referral_code mapping."""
    if not LOCATION_MAPPING:
        print("⚠️  No location mappings defined. Edit LOCATION_MAPPING in this script.")
        print("\nExample:")
        print('  LOCATION_MAPPING = {')
        print('      "ABC123": "LOMBARDI_01",')
        print('      "XYZ789": "PITCHER_02",')
        print('  }')
        return
    
    with engine.begin() as conn:
        for referral_code, location_code in LOCATION_MAPPING.items():
            result = conn.execute(text("""
                UPDATE webwise.users
                SET location_code = :location_code
                WHERE referral_code = :referral_code
            """), {
                "referral_code": referral_code,
                "location_code": location_code
            })
            updated = result.rowcount
            if updated > 0:
                print(f"✅ Set {referral_code} → {location_code} ({updated} user(s))")
            else:
                print(f"⚠️  No user found with referral_code: {referral_code}")

if __name__ == "__main__":
    print("📍 Setting Location Codes for Referral Attribution")
    print("=" * 50)
    set_location_codes()
    print("=" * 50)
    print("✅ Done. Check your admin dashboard to see location codes in the leaderboard.")
