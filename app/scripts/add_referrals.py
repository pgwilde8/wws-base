from sqlalchemy import create_engine, text
import random
import string

# Database URL
DATABASE_URL = "postgresql://wws-admin:WwsAdmin2026%21@localhost/wws_dispatch_db"

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("🔌 Connecting to Database...")
        
        # 1. Add 'referral_code' (The unique code for each driver)
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code VARCHAR(10) UNIQUE;"))
            print("✅ Added column: referral_code")
        except Exception as e:
            print(f"⚠️ Error: {e}")

        # 2. Add 'referred_by' (Who invited them)
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by VARCHAR(10);"))
            print("✅ Added column: referred_by")
        except Exception as e:
            print(f"⚠️ Error: {e}")
            
        # 3. Generate codes for existing users who don't have one
        try:
            result = conn.execute(text("SELECT id FROM users WHERE referral_code IS NULL"))
            users = result.fetchall()
            for user in users:
                new_code = generate_code()
                conn.execute(text(f"UPDATE users SET referral_code = '{new_code}' WHERE id = {user[0]}"))
            print(f"🎉 Generated codes for {len(users)} existing users.")
        except Exception as e:
            print(f"⚠️ Error generating codes: {e}")

        conn.commit()
        print("🚀 Migration Complete.")

if __name__ == "__main__":
    migrate()