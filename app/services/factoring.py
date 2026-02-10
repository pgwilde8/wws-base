import json
from datetime import datetime

# Configuration (In production, load these from your .env file)
FACTORING_API_URL = "https://api.otrsolutions.com/v1/invoices" # Example Endpoint
FACTORING_API_KEY = "YOUR_API_KEY_HERE"

def push_invoice_to_factor(load_data: dict, bol_url: str):
    """
    Bundles the Load Data + BOL and prepares it for the Factoring Company.
    Returns a mock 'Success' response for now.
    """
    
    # 1. The "Funding Packet"
    # This is the industry-standard format for factoring APIs
    payload = {
        "invoice_date": datetime.now().isoformat(),
        "reference_number": load_data['load_board_id'],
        "debtor": {
            "name": load_data['broker_name'],
            "address": "123 Broker Lane, Logistics City, OH", # You would pull this from DB
            "mc_number": "123456"
        },
        "items": [
            {
                "description": f"Freight Charge - {load_data['origin']} to {load_data['destination']}",
                "amount": load_data['final_rate'],
                "quantity": 1
            }
        ],
        "attachments": [
            {
                "type": "BOL",
                "url": bol_url,
                "note": "Signed Proof of Delivery"
            }
        ],
        # 2. The "Split" Instruction (Crucial for your 2%)
        # This tells the bank to split the payment automatically.
        "payment_instructions": {
            "carrier_payout": load_data['final_rate'] - load_data['dispatch_fee_amount'],
            "dispatch_fee_deduction": load_data['dispatch_fee_amount'],
            "remit_fee_to": "Green Candle Dispatch LLC"
        }
    }

    # --- LOGGING THE TRANSACTION ---
    print(f"\n🚀 BANK BRIDGE: Sending Invoice #{load_data['load_board_id']}...")
    print("------------------------------------------------")
    print(json.dumps(payload, indent=2))
    print("------------------------------------------------")
    
    # --- SIMULATION MODE ---
    # In real life: response = requests.post(FACTORING_API_URL, json=payload, headers=...)
    # For now, we simulate a "200 OK" from the bank.
    
    return {
        "status": "success",
        "bank_transaction_id": "TXN_99887766",
        "message": "Invoice received. Funding scheduled for 2:00 PM EST."
    }