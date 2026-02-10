#!/usr/bin/env python3
"""Create a test client user for accessing savings-view"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from app.core.deps import hash_password, engine
from sqlalchemy import text

if not engine:
    print("❌ Database engine not available. Check DATABASE_URL in .env")
    sys.exit(1)

# Test client credentials
test_email = 'driver@test.com'
test_password = 'test123'
test_mc = 'MC_998877'

password_hash = hash_password(test_password)

with engine.begin() as conn:
    # Check if user exists
    check = conn.execute(text('SELECT id FROM webwise.users WHERE email = :email'), {'email': test_email}).first()
    
    if check:
        print(f'✅ User {test_email} already exists')
        user_id = check.id
    else:
        # Create user
        result = conn.execute(text('''
            INSERT INTO webwise.users (email, password_hash, role, is_active)
            VALUES (:email, :password_hash, 'client', true)
            RETURNING id
        '''), {'email': test_email, 'password_hash': password_hash})
        user_id = result.one().id
        print(f'✅ Created user: {test_email}')
    
    # Check/create trucker profile
    profile_check = conn.execute(text('SELECT id FROM webwise.trucker_profiles WHERE user_id = :uid'), {'uid': user_id}).first()
    
    if not profile_check:
        conn.execute(text('''
            INSERT INTO webwise.trucker_profiles (user_id, display_name, mc_number, carrier_name)
            VALUES (:user_id, :display_name, :mc_number, :carrier_name)
        '''), {
            'user_id': user_id,
            'display_name': 'Test Driver',
            'mc_number': test_mc,
            'carrier_name': 'Test Carrier'
        })
        print(f'✅ Created trucker profile with MC: {test_mc}')
    else:
        print(f'✅ Trucker profile already exists')

print(f'\n{"="*60}')
print(f'✅ LOGIN CREDENTIALS:')
print(f'{"="*60}')
print(f'   Email:    {test_email}')
print(f'   Password: {test_password}')
print(f'   MC Number: {test_mc}')
print(f'{"="*60}')
print(f'\n🌐 Login URL: http://134.199.241.56:8990/login/client')
print(f'📊 Savings View: http://134.199.241.56:8990/savings-view')
