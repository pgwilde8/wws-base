"""
Onboarding Service: Finalizes driver setup after Stripe payment.
Tiered: Solo ($25/10 $CANDLE) vs Small Fleet ($99/50 $CANDLE).
"""
from sqlalchemy import text
from decimal import Decimal
from typing import Literal
import os

EMAIL_DOMAIN = os.getenv("EMAIL_DOMAIN", "gcdloads.com")

# Tiered starter fuel: scale "gas" to engine size
TIER_STARTER = {
    "SOLO": Decimal("10.0"),   # $25 setup, 1 truck
    "FLEET": Decimal("50.0"),  # $99 setup, up to 5 trucks
}
TIER_LOAD_ID = {
    "SOLO": "STARTER_PACK",
    "FLEET": "FLEET_STARTER_PACK",
}


def onboard_new_driver(
    engine,
    user_id: int,
    mc_number: str,
    dot_number: str,
    email_handle: str,
    tier: Literal["SOLO", "FLEET"] = "SOLO",
):
    """
    Finalizes driver setup after Stripe payment.
    1. Creates or updates Trucker Profile
    2. Assigns GCD Dispatch Identity: {email_handle}@{EMAIL_DOMAIN}
    3. Issues tiered Starter Fuel: 10.0 (Solo) or 50.0 (Fleet)
    Returns: (dispatch_email, trucker_id, starter_credits)
    """
    tier_key = "FLEET" if tier.upper() == "FLEET" else "SOLO"
    starter_credits = float(TIER_STARTER[tier_key])
    load_id = TIER_LOAD_ID[tier_key]

    dispatch_email = f"{email_handle}@{EMAIL_DOMAIN}"
    display_name = email_handle.strip().lower()

    with engine.begin() as conn:
        # 1. Upsert Trucker Profile (by user_id)
        row = conn.execute(
            text("SELECT id FROM webwise.trucker_profiles WHERE user_id = :uid"),
            {"uid": user_id},
        ).first()
        if row:
            trucker_id = row[0]
            conn.execute(
                text("""
                    UPDATE webwise.trucker_profiles
                    SET mc_number = :mc, dot_number = :dot, display_name = :dn,
                        updated_at = now(), is_first_login = true
                    WHERE user_id = :uid
                """),
                {"mc": mc_number, "dot": dot_number, "dn": display_name, "uid": user_id},
            )
        else:
            r = conn.execute(
                text("""
                    INSERT INTO webwise.trucker_profiles (user_id, display_name, mc_number, dot_number, is_first_login)
                    VALUES (:uid, :dn, :mc, :dot, true)
                    RETURNING id
                """),
                {"uid": user_id, "dn": display_name, "mc": mc_number, "dot": dot_number},
            )
            trucker_id = r.scalar()

        # 2. Issue tiered Starter Credit (STARTER_PACK vs FLEET_STARTER_PACK for back-office)
        conn.execute(
            text("""
                INSERT INTO webwise.driver_savings_ledger
                (driver_mc_number, load_id, amount_usd, amount_candle, unlocks_at, status)
                VALUES (:mc, :load_id, :usd, :candle, now(), 'CREDITED')
            """),
            {
                "mc": mc_number,
                "load_id": load_id,
                "usd": starter_credits,
                "candle": starter_credits,
            },
        )

    return dispatch_email, trucker_id, starter_credits