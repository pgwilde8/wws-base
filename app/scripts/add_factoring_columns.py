from sqlalchemy import create_engine, text

# Your specific connection string
DATABASE_URL = "postgresql://wws-admin:WwsAdmin2026%21@localhost/wws_dispatch_db"

def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("🔌 Connecting to Database...")
        
        # 1. Add 'factoring_company' column (Stores who they use, e.g., "RTS")
        try:
            conn.execute(text("ALTER TABLE webwise.users ADD COLUMN IF NOT EXISTS factoring_company VARCHAR(255);"))
            print("✅ Added column: factoring_company")
        except Exception as e:
            print(f"⚠️ Error adding factoring_company: {e}")

        # 2. Add 'referral_status' column (Stores 'OTR_REQUESTED' or 'EXISTING')
        try:
            conn.execute(text("ALTER TABLE webwise.users ADD COLUMN IF NOT EXISTS referral_status VARCHAR(50) DEFAULT 'NONE';"))
            print("✅ Added column: referral_status")
        except Exception as e:
            print(f"⚠️ Error adding referral_status: {e}")
            
        conn.commit()
        print("🚀 Migration Complete. Database is ready for the new form.")

if __name__ == "__main__":
    migrate()