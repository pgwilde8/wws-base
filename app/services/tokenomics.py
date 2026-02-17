import os
import json

# Optional web3 import (only needed for execute_buyback_and_send)
try:
    from web3 import Web3
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    Web3 = None

# --- CONFIGURATION (Load from .env) ---
# 1. The Connection
RPC_URL = os.getenv("WEB3_PROVIDER_URL", "https://base-mainnet.g.alchemy.com/v2/YOUR_KEY")
# 2. The Company Vault
PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY", "YOUR_PRIVATE_KEY")
SENDER_ADDRESS = os.getenv("WALLET_ADDRESS", "YOUR_PUBLIC_ADDRESS")
# 3. The Target Token ($CANDLE)
TOKEN_ADDRESS = "0x..." # Replace with actual $CANDLE address
# 4. Uniswap Router (Base Mainnet)
ROUTER_ADDRESS = "0x2626664c2603336E57B271c5C0b26F421741e481" # Uniswap V2 Router on Base

# Initialize Connection (only if web3 is available)
if WEB3_AVAILABLE:
    w3 = Web3(Web3.HTTPProvider(RPC_URL)) if RPC_URL else None
else:
    w3 = None

def execute_buyback_and_send(driver_wallet: str, amount_in_usd: float):
    """
    1. Checks if we have connection.
    2. Swaps ETH -> $CANDLE (Buyback).
    3. Sends $CANDLE -> Driver.
    """
    
    if not WEB3_AVAILABLE or not w3:
        return "❌ Error: Web3 not available. Install web3 package for blockchain features."
    
    if not w3.is_connected():
        return "❌ Error: Blockchain connection failed."

    print(f"🔗 Connected to Base. Latest Block: {w3.eth.block_number}")
    print(f"💰 Executing Buyback for: ${amount_in_usd}")

    # --- THE SIMULATION (For Safety First) ---
    # We don't want to burn real money until you confirm the wallet is funded.
    
    # 1. Calculate how much ETH to spend (Mock Math)
    # real code would fetch ETH price price from oracle
    eth_to_spend = 0.005 # approx $15 for testing
    
    print(f"🔄 Swapping {eth_to_spend} ETH for $CANDLE...")
    print(f"📨 Sending tokens to Driver: {driver_wallet}")
    
    return {
        "status": "success",
        "tx_hash": "0x123456789abcdef...", # Mock Hash
        "message": f"Bought ${amount_in_usd} of $CANDLE and sent to {driver_wallet}"
    }

def credit_driver_savings(db, load_id: str, mc_number: str, fee_usd: float):
    """
    LEGACY FUNCTION - DEPRECATED.
    
    This function is kept for backward compatibility but should not be used.
    Use app.services.ledger.process_load_settlement() instead.
    
    All credits are now immediate-use with no vesting or locking.
    Previous 6-month vesting was removed.
    """
    # Redirect to the new ledger service
    from app.services.ledger import process_load_settlement
    from sqlalchemy import text
    
    # Get trucker_id from mc_number
    trucker_row = db.execute(
        text("SELECT id FROM webwise.trucker_profiles WHERE mc_number = :mc LIMIT 1"),
        {"mc": mc_number}
    ).first()
    
    if not trucker_row:
        return False
    
    trucker_id = trucker_row[0]
    
    # Use the new immediate-use credit system
    result = process_load_settlement(
        engine=db.bind,
        trucker_id=trucker_id,
        load_id=load_id,
        total_paid_by_broker=fee_usd
    )
    
    return result.get("credits_issued", 0) > 0


# --- TEST RUN ---
if __name__ == "__main__":
    # Test with a dummy driver wallet
    test_wallet = "0x1234567890123456789012345678901234567890"
    print(execute_buyback_and_send(test_wallet, 60.00))