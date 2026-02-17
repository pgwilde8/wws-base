"""
Stripe Checkout for Small Fleet Setup: $25/truck, quantity 1–5.
Creates Checkout Session with dynamic price_data (no pre-created product needed).
"""
import os
from typing import Optional

import stripe

STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY")
stripe.api_key = STRIPE_SECRET

PRICE_PER_TRUCK_CENTS = 2500  # $25.00
MIN_TRUCKS = 1
MAX_TRUCKS = 5


def create_setup_checkout_session(
    user_id: int,
    truck_count: int,
    success_url: str,
    cancel_url: str,
    *,
    customer_email: Optional[str] = None,
) -> Optional[str]:
    """
    Create Stripe Checkout Session for Small Fleet Setup.
    Returns session.url for redirect, or None if Stripe is not configured.
    """
    if not STRIPE_SECRET:
        return None
    truck_count = max(MIN_TRUCKS, min(MAX_TRUCKS, int(truck_count)))
    session = stripe.checkout.Session.create(
        mode="payment",
        client_reference_id=str(user_id),
        metadata={"truck_count": str(truck_count)},
        customer_email=customer_email,
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Small Fleet Setup",
                        "description": f"One-time setup fee: $25 per truck. {truck_count} truck{'s' if truck_count > 1 else ''}. Includes $CANDLE credits for AI dispatch automation.",
                        "images": [],
                    },
                    "unit_amount": PRICE_PER_TRUCK_CENTS,
                },
                "quantity": truck_count,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return session.url if session else None


def retrieve_and_verify_session(session_id: str) -> Optional[dict]:
    """
    Retrieve Checkout Session and verify payment_status is 'paid'.
    Returns metadata dict with user_id, truck_count, payment_intent_id if valid; else None.
    """
    if not STRIPE_SECRET or not session_id:
        return None
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status != "paid":
            return None
        user_id = session.client_reference_id
        truck_count = int(session.metadata.get("truck_count", "1") or "1")
        truck_count = max(MIN_TRUCKS, min(MAX_TRUCKS, truck_count))
        payment_intent_id = session.payment_intent if hasattr(session, 'payment_intent') else None
        return {
            "user_id": int(user_id),
            "truck_count": truck_count,
            "payment_intent_id": payment_intent_id,
        }
    except Exception:
        return None
