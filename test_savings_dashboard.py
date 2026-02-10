#!/usr/bin/env python3
"""Test the driver savings dashboard endpoint"""
import requests
import json

# The URL of your local API
url = "http://127.0.0.1:8990/savings/dashboard/MC_998877"

print("💰 Testing Driver Savings Dashboard...")
print(f"📡 Requesting: {url}\n")

try:
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ SUCCESS! Dashboard Data Retrieved.")
        print("=" * 60)
        print(f"🚛 MC Number:        {data['mc_number']}")
        print(f"💎 Total Balance:    {data['total_candle_balance']:.4f} $CANDLE")
        print(f"🔒 Locked Balance:   {data['locked_balance']:.4f} $CANDLE")
        print(f"✅ Unlocked Balance: {data['unlocked_balance']:.4f} $CANDLE")
        
        if data['next_vesting_date']:
            print(f"📅 Next Vesting:     {data['next_vesting_date']}")
            if data['days_until_unlock'] is not None:
                print(f"⏰ Days Until Unlock: {data['days_until_unlock']} days")
        else:
            print("📅 Next Vesting:     No locked tokens")
        
        print(f"\n📋 Recent Transactions ({data['transaction_count']}):")
        print("-" * 60)
        
        for i, tx in enumerate(data['recent_transactions'], 1):
            print(f"\n{i}. Load: {tx['load_id']}")
            print(f"   Amount: {tx['amount_candle']:.4f} $CANDLE (${tx['amount_usd']:.2f} USD)")
            print(f"   Earned: {tx['earned_date']}")
            print(f"   Unlocks: {tx['unlocks_date']}")
            print(f"   Status: {tx['status']}")
            if tx['tx_hash']:
                print(f"   TX Hash: {tx['tx_hash']}")
        
        print("\n" + "=" * 60)
        print("\n📊 Full JSON Response:")
        print(json.dumps(data, indent=2))
        
    else:
        print(f"\n❌ FAILED: {response.status_code}")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("\n❌ Connection Error: Could not connect to server")
    print("   Make sure your FastAPI server is running:")
    print("   uvicorn app.main:app --host 0.0.0.0 --port 8990 --reload")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
