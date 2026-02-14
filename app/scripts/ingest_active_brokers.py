import os
from pathlib import Path

# Load .env before app imports so DATABASE_URL is set
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass

import requests
from sqlalchemy import text
from app.core.deps import SessionLocal

# API: FMCSA Carrier All With History (6eyk-hxee)
# Keys: docket_number (MC...), broker_stat ('A'=Active), legal_name, dba_name, dot_number,
#       bus_city, bus_state_code, bus_street_po, bus_zip_code (no phone in this dataset)
API_URL = "https://data.transportation.gov/resource/6eyk-hxee.json"
BATCH_SIZE = 5000

def ingest_brokers():
    db = SessionLocal()
    base_params = {
        "$where": "broker_stat = 'A'",
        "$limit": BATCH_SIZE,
        "$$app_token": os.getenv("DOT_API_TOKEN"),
    }
    upsert_query = text("""
        INSERT INTO webwise.brokers (
            mc_number, dot_number, company_name, dba_name,
            phy_street, phy_city, phy_state, phy_zip, source
        ) VALUES (
            :mc, :dot, :name, :dba, :street, :city, :state, :zip, 'fmcsa_api'
        ) ON CONFLICT (mc_number) DO UPDATE SET
            dot_number = EXCLUDED.dot_number,
            company_name = EXCLUDED.company_name,
            dba_name = EXCLUDED.dba_name,
            phy_street = EXCLUDED.phy_street,
            phy_city = EXCLUDED.phy_city,
            phy_state = EXCLUDED.phy_state,
            phy_zip = EXCLUDED.phy_zip,
            updated_at = CURRENT_TIMESTAMP
    """)
    total_upserted = 0
    offset = 0

    try:
        print("📡 Fetching active brokers from FMCSA API (paginated)...")
        while True:
            params = {**base_params, "$offset": offset}
            response = requests.get(API_URL, params=params)
            response.raise_for_status()
            brokers = response.json()
            if not brokers:
                break

            for b in brokers:
                raw_mc = str(b.get("docket_number") or "").strip().upper()
                mc_number = raw_mc.replace("MC", "").strip() if raw_mc else ""
                if not mc_number or mc_number == "NONE":
                    continue
                db.execute(upsert_query, {
                    "mc": mc_number,
                    "dot": b.get("dot_number"),
                    "name": (b.get("legal_name") or "Unknown").strip() or "Unknown",
                    "dba": (b.get("dba_name") or "").strip() or None,
                    "street": (b.get("bus_street_po") or "").strip() or None,
                    "city": (b.get("bus_city") or "").strip() or None,
                    "state": (b.get("bus_state_code") or "").strip() or None,
                    "zip": (b.get("bus_zip_code") or "").strip() or None,
                })
                total_upserted += 1

            db.commit()
            print(f"   Offset {offset}: upserted {len(brokers)} (total so far: {total_upserted})")
            if len(brokers) < BATCH_SIZE:
                break
            offset += BATCH_SIZE

        print(f"🚀 Done. Total active brokers upserted: {total_upserted}.")

    except Exception as e:
        print(f"❌ Ingestion failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    ingest_brokers()