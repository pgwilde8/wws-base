import requests

# The URL of your local API
url = "http://127.0.0.1:8990/loads/upload-bol"

# 1. Fake Data (What the app sends)
payload = {
    "load_id": "LOAD_123",
    "mc_number": "MC_998877"
}

# 2. Fake File (We create a dummy 'BOL' on the fly)
# In real life, this is the image from the camera.
files = {
    "file": ("fake_bol.pdf", b"%PDF-1.4 fake pdf content", "application/pdf")
}

print("🚚 Attempting to upload BOL...")

try:
    response = requests.post(url, data=payload, files=files)
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ SUCCESS! Load Processed.")
        print("------------------------------------------------")
        print(f"📄 Load ID:      {data['load_board_id']}")
        print(f"📎 BOL URL:      {data['bol_url']}")
        print(f"💵 Final Rate:   ${data['final_rate']}")
        print(f"💰 Dispatch Fee: ${data['dispatch_fee_amount']} (This goes to You)")
        print(f"🪙 Token Buy:    ${data['token_buyback_amount']} (This goes to Driver)")
        print(f"🏦 Bank Status:  {data.get('bank_status', 'Not Connected')}")
        print("------------------------------------------------")
    else:
        print(f"\n❌ FAILED: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\n❌ Connection Error: {e}")
    print("Make sure your FastAPI server is running! (uvicorn main:app --reload)")