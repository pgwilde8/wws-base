"""
Auto-Pilot: AI acts as Digital Dispatcher—counters, accepts, or alerts based on
floor_price and target_price guardrails. Called by inbound_listener on new broker replies.
"""
from typing import Optional, Tuple
from sqlalchemy import text

from app.services.email import send_negotiation_email
from app.services.ai_logic import extract_bid_details


def process_autopilot_logic(
    engine,
    load_id: str,
    email_body: str,
    broker_email: str,
    driver_name: str,
    floor_price: float,
    target_price: float,
) -> str:
    """
    Decides whether to counter, accept, or alert the driver.
    Returns: AUTO_ACCEPTED | AUTO_COUNTERED | BELOW_FLOOR_MANUAL_REQUIRED | NO_PRICE_DETECTED
    """
    details = extract_bid_details(email_body)
    offer = details.get("extracted_offer")

    if offer is None:
        return "NO_PRICE_DETECTED"

    offer_val = float(offer)

    # Get or create negotiation for email tracking
    negotiation_id = _get_or_create_negotiation(engine, load_id, driver_name, offer_val)
    if not negotiation_id:
        return "NO_PRICE_DETECTED"  # Could not resolve trucker

    # CASE 1: Offer is already at or above Target -> AUTO-ACCEPT
    if offer_val >= target_price:
        result = send_negotiation_email(
            to_email=broker_email,
            subject=f"RE: Load {load_id}",
            body="That rate works for us. Please send the rate confirmation over.",
            load_id=load_id,
            negotiation_id=negotiation_id,
            driver_name=driver_name,
            load_source=None,
        )
        if result.get("status") == "success":
            return "AUTO_ACCEPTED"
        return "NO_PRICE_DETECTED"  # Fallback on send failure

    # CASE 2: Offer is below target but above Floor -> AUTO-COUNTER
    if offer_val >= floor_price:
        counter_price = min(offer_val + 100, target_price)
        result = send_negotiation_email(
            to_email=broker_email,
            subject=f"RE: Load {load_id}",
            body=f"We are close. If you can do ${int(counter_price):,}, we can book it right now.",
            load_id=load_id,
            negotiation_id=negotiation_id,
            driver_name=driver_name,
            load_source=None,
        )
        if result.get("status") == "success":
            return "AUTO_COUNTERED"
        return "NO_PRICE_DETECTED"

    # CASE 3: Offer is below floor -> ALERT DRIVER (no email sent)
    return "BELOW_FLOOR_MANUAL_REQUIRED"


def _get_or_create_negotiation(
    engine, load_id: str, driver_name: str, current_rate: float
) -> Optional[int]:
    """Resolve trucker_id from driver_name, then get or create negotiation."""
    driver_name = (driver_name or "").strip().lower()
    if not driver_name:
        return None

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM webwise.trucker_profiles WHERE LOWER(TRIM(display_name)) = :dn"),
            {"dn": driver_name},
        ).first()
        if not row:
            return None
        trucker_id = row[0]

        neg = conn.execute(
            text("""
                SELECT id FROM webwise.negotiations
                WHERE load_id = :load_id AND trucker_id = :trucker_id
                ORDER BY id DESC LIMIT 1
            """),
            {"load_id": load_id, "trucker_id": trucker_id},
        ).first()

        if neg:
            return neg[0]

        r = conn.execute(
            text("""
                INSERT INTO webwise.negotiations (load_id, trucker_id, original_rate, target_rate, status)
                VALUES (:load_id, :trucker_id, :rate, :rate, 'sent')
                RETURNING id
            """),
            {"load_id": load_id, "trucker_id": trucker_id, "rate": current_rate},
        )
        return r.scalar()
