"""
Ledger Service: Service credits from the 2% dispatch fee.
SEC-safe: dollar-blind—uses fixed percentages only. No hardcoded $38 or $13.
"""
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import text

# --- GLOBAL CONSTANTS (SEC-SAFE, DOLLAR-BLIND) ---
DISPATCH_FEE_RATE = Decimal("0.02")       # 2% of load paid to platform
DRIVER_REBATE_RATIO = Decimal("0.2105")   # 21.05% of fee returned as service credits

# Internal split (for reporting only):
PLATFORM_PROFIT_RATIO = Decimal("0.3158")   # 31.58%
TREASURY_RATIO = Decimal("0.2632")          # 26.32%
AI_RESERVE_RATIO = Decimal("0.2105")        # 21.05%
# DRIVER_REBATE_RATIO = 21.05%


def _calculate_fee_split(total_paid: Decimal) -> Dict[str, Decimal]:
    """Compute 2% fee, driver rebate, and infra allocation. Works for any load amount."""
    actual_fee = total_paid * DISPATCH_FEE_RATE
    return {
        "gross_fee": actual_fee,
        "driver_credits_usd": actual_fee * DRIVER_REBATE_RATIO,
        "infra_allocation": actual_fee * AI_RESERVE_RATIO,  # AI/OpenAI/Twilio reserve (21.05%)
    }


def estimate_credits_for_load(load_amount: float) -> Dict[str, float]:
    """
    Preview-only: estimates credits for a load (no DB write).
    Use for UI display (e.g. "Estimated Credits to Earn").
    1 CANDLE = $1 service value (fixed).
    """
    total = Decimal(str(load_amount))
    split = _calculate_fee_split(total)
    credits = round(float(split["driver_credits_usd"]), 2)
    return {"credits_usd": credits, "credits_candle": credits}


def process_load_settlement(
    engine,
    trucker_id: int,
    load_id: str,
    total_paid_by_broker: float,
) -> Dict[str, Any]:
    """
    Called when a load is settled (e.g. driver accepts). Calculates the 2% fee,
    splits into operating buckets, and credits the driver's ledger.

    Returns: {gross_fee, credits_issued, credits_usd, infra_allocation}
    """
    if not engine or not trucker_id or not load_id or total_paid_by_broker <= 0:
        return {"gross_fee": 0, "credits_issued": 0, "credits_usd": 0, "infra_allocation": 0}

    total_paid = Decimal(str(total_paid_by_broker))
    split = _calculate_fee_split(total_paid)
    driver_credits_usd = float(split["driver_credits_usd"])
    if driver_credits_usd <= 0:
        return {"gross_fee": 0, "credits_issued": 0, "credits_usd": 0, "infra_allocation": 0}

    # 1 CANDLE = $1 service value (fixed, no speculation)
    credits_candle = round(driver_credits_usd, 2)
    if credits_candle <= 0:
        return {"gross_fee": float(split["gross_fee"]), "credits_issued": 0, "credits_usd": driver_credits_usd, "infra_allocation": 0}

    try:
        with engine.begin() as conn:
            mc_row = conn.execute(
                text("SELECT mc_number FROM webwise.trucker_profiles WHERE id = :tid"),
                {"tid": trucker_id},
            ).first()
            if not mc_row or not mc_row[0]:
                return {"gross_fee": float(split["gross_fee"]), "credits_issued": 0, "credits_usd": driver_credits_usd, "infra_allocation": float(split["infra_allocation"])}
            mc_number = mc_row[0]

            # Immediate-use credits: no vesting. SEC-safe rebate model.
            conn.execute(
                text("""
                    INSERT INTO webwise.driver_savings_ledger
                    (driver_mc_number, load_id, amount_usd, amount_candle, unlocks_at, status)
                    VALUES (:mc, :load_id, :usd, :candle, now(), 'CREDITED')
                """),
                {
                    "mc": mc_number,
                    "load_id": load_id,
                    "usd": round(driver_credits_usd, 2),
                    "candle": credits_candle,
                },
            )

        return {
            "gross_fee": round(float(split["gross_fee"]), 2),
            "credits_issued": credits_candle,
            "credits_usd": round(driver_credits_usd, 2),
            "infra_allocation": round(float(split["infra_allocation"]), 2),
        }
    except Exception as e:
        print(f"Ledger process_load_settlement error: {e}")
        return {"gross_fee": 0, "credits_issued": 0, "credits_usd": 0, "infra_allocation": 0}


def issue_load_credits(engine, trucker_id: int, load_id: str, load_amount: float) -> float:
    """
    Convenience wrapper: issues credits for an accepted load.
    Returns credits (CANDLE) issued, or 0 on failure.
    """
    result = process_load_settlement(engine, trucker_id, load_id, load_amount)
    return result.get("credits_issued", 0) or 0.0


def issue_service_credits(engine, trucker_id: int, load_id: str, total_paid: float) -> float:
    """
    Issues immediate-use service credits (rebate from 2% fee).
    No vesting. Available for automation immediately.
    Alias for issue_load_credits.
    """
    return issue_load_credits(engine, trucker_id, load_id, total_paid)


# Premium feature costs (CANDLE)
AUTOPILOT_COST = 3.0  # Charged only when load is successfully BOOKED
OUTBOUND_EMAIL_COST = 0.1  # Per send from Terminal
AI_VOICE_CALL_COST = 0.5  # Per escalation attempt
