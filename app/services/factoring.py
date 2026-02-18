import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Configuration (In production, load these from your .env file)
FACTORING_API_URL = "https://api.otrsolutions.com/v1/invoices"  # Example Endpoint
FACTORING_API_KEY = "YOUR_API_KEY_HERE"


def push_invoice_to_factor(load_data: dict, bol_url: str, attachments: Optional[List[Dict[str, str]]] = None):
    """
    Bundles the Load Data + BOL (+ optional RateCon) and prepares it for the Factoring Company.
    If attachments is provided, use it; otherwise fall back to single BOL.
    Returns a mock 'Success' response for now.
    """
    if attachments is None:
        attachments = [{"type": "BOL", "url": bol_url, "note": "Signed Proof of Delivery"}]

    payload = {
        "invoice_date": datetime.now().isoformat(),
        "reference_number": load_data["load_board_id"],
        "debtor": {
            "name": load_data.get("broker_name", "Broker"),
            "address": load_data.get("broker_address", "123 Broker Lane, Logistics City, OH"),
            "mc_number": load_data.get("broker_mc", "123456"),
        },
        "items": [
            {
                "description": f"Freight Charge - {load_data['origin']} to {load_data['destination']}",
                "amount": load_data["final_rate"],
                "quantity": 1,
            }
        ],
        "attachments": attachments,
        "payment_instructions": {
            "carrier_payout": load_data["final_rate"] - load_data["dispatch_fee_amount"],
            "dispatch_fee_deduction": load_data["dispatch_fee_amount"],
            "remit_fee_to": "Green Candle Dispatch LLC",
        },
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
        "message": "Invoice received. Funding scheduled for 2:00 PM EST.",
    }


def send_packet_to_factor(engine, load_id: str, trucker_id: int, user_id: int) -> Dict[str, Any]:
    """
    Gather BOL + RateCon from load_documents, build factoring packet, push to factor.
    Marks negotiation as factoring_status='SENT', factored_at=now().
    Returns: {ok: bool, message: str, candle_reward: float, final_rate: float}
    """
    from sqlalchemy import text
    from sqlalchemy.exc import ProgrammingError

    if not engine or not load_id or not trucker_id:
        return {"ok": False, "message": "Missing parameters", "candle_reward": 0}

    with engine.begin() as conn:
        # 1. Gather documents (BOL required; RateCon optional). Prefer bucket+key; fallback to file_url.
        doc_rows = conn.execute(
            text("""
                SELECT doc_type, file_url, bucket, file_key FROM webwise.load_documents
                WHERE load_id = :load_id AND trucker_id = :tid
                AND doc_type IN ('BOL', 'RATECON')
                ORDER BY doc_type, created_at DESC
            """),
            {"load_id": load_id, "tid": trucker_id},
        ).fetchall()

    from app.services.storage import get_presigned_url

    def doc_url(r):
        if getattr(r, "bucket", None) and getattr(r, "file_key", None):
            return get_presigned_url(r.bucket, r.file_key)
        return r.file_url

    bol_urls = [doc_url(r) for r in doc_rows if r.doc_type == "BOL"]
    ratecon_urls = [doc_url(r) for r in doc_rows if r.doc_type == "RATECON"]

    if not bol_urls:
        return {"ok": False, "message": "Upload BOL first before sending to factoring.", "candle_reward": 0}

    attachments = []
    for url in bol_urls[:2]:  # Max 2 BOLs
        attachments.append({"type": "BOL", "url": url, "note": "Proof of Delivery"})
    for url in ratecon_urls[:1]:  # Max 1 RateCon
        attachments.append({"type": "RateCon", "url": url, "note": "Rate Confirmation"})

    with engine.begin() as conn:
        # 2. Get negotiation (load data)
        try:
            neg = conn.execute(
                text("""
                    SELECT n.final_rate, n.origin, n.destination, n.factoring_status
                    FROM webwise.negotiations n
                    WHERE n.load_id = :load_id AND n.trucker_id = :tid AND n.status = 'won'
                """),
                {"load_id": load_id, "tid": trucker_id},
            ).first()
        except ProgrammingError:
            neg = conn.execute(
                text("""
                    SELECT n.final_rate, n.origin, n.destination, NULL as factoring_status
                    FROM webwise.negotiations n
                    WHERE n.load_id = :load_id AND n.trucker_id = :tid AND n.status = 'won'
                """),
                {"load_id": load_id, "tid": trucker_id},
            ).first()
        if not neg:
            return {"ok": False, "message": "Load not found or not won.", "candle_reward": 0}
        factoring_status = getattr(neg, "factoring_status", None) or ""
        if factoring_status == "SENT":
            return {"ok": True, "message": "Already sent to factoring.", "candle_reward": 0, "final_rate": float(neg.final_rate or 0)}

        final_rate = float(neg.final_rate or 0)
        if final_rate <= 0:
            return {"ok": False, "message": "Invalid load rate.", "candle_reward": 0}

        dispatch_fee = final_rate * 0.02

        # 3. Get user's factoring company
        user_row = conn.execute(
            text("SELECT factoring_company FROM webwise.users u JOIN webwise.trucker_profiles tp ON tp.user_id = u.id WHERE tp.id = :tid"),
            {"tid": trucker_id},
        ).first()
        factoring_co = (user_row.factoring_company or "").strip() if user_row else ""

    load_data = {
        "load_board_id": load_id,
        "broker_name": "Broker",
        "origin": neg.origin or "Unknown",
        "destination": neg.destination or "Unknown",
        "final_rate": final_rate,
        "dispatch_fee_amount": round(dispatch_fee, 2),
    }

    result = push_invoice_to_factor(load_data, bol_urls[0], attachments=attachments)

    if result.get("status") != "success":
        return {"ok": False, "message": result.get("message", "Factoring push failed."), "candle_reward": 0}

    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE webwise.negotiations
                    SET factoring_status = 'SENT', factored_at = now(), updated_at = now()
                    WHERE load_id = :load_id AND trucker_id = :tid AND status = 'won'
                """),
                {"load_id": load_id, "tid": trucker_id},
            )
    except ProgrammingError:
        pass  # Columns may not exist yet; run migrate_factoring_status.sql

    candle_reward = round(dispatch_fee * 0.21, 2)
    return {
        "ok": True,
        "message": result.get("message", "Packet sent to factoring."),
        "candle_reward": candle_reward,
        "final_rate": final_rate,
    }