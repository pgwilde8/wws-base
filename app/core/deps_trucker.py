"""
Trucker (driver) access: profile loading and Stripe/payment gating.
Single place for the rule: if trucker_profiles.is_beta == true, skip Stripe checks.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.core.deps import current_user, get_engine


def is_beta_driver(profile: Dict[str, Any]) -> bool:
    """Master beta flag: use for banners, support priority, onboarding, feature toggles."""
    return bool(profile.get("is_beta"))


def get_trucker_profile(engine: Engine, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Load trucker profile for user_id. Returns dict with trucker_profile_id, user_id,
    display_name, mc_number, dot_number, is_beta (default False if column missing),
    is_first_login, etc., or None if no profile.
    """
    if not engine:
        return None
    with engine.begin() as conn:
        try:
            row = conn.execute(
                text("""
                    SELECT
                        tp.id AS trucker_profile_id,
                        tp.user_id,
                        tp.display_name,
                        tp.mc_number,
                        tp.dot_number,
                        tp.authority_type,
                        COALESCE(tp.is_beta, false) AS is_beta,
                        tp.is_first_login
                    FROM webwise.trucker_profiles tp
                    WHERE tp.user_id = :user_id
                    LIMIT 1
                """),
                {"user_id": user_id},
            ).mappings().first()
        except Exception:
            row = conn.execute(
                text("""
                    SELECT
                        tp.id AS trucker_profile_id,
                        tp.user_id,
                        tp.display_name,
                        tp.mc_number,
                        tp.dot_number,
                        tp.authority_type,
                        false AS is_beta,
                        false AS is_first_login
                    FROM webwise.trucker_profiles tp
                    WHERE tp.user_id = :user_id
                    LIMIT 1
                """),
                {"user_id": user_id},
            ).mappings().first()
    return dict(row) if row else None


def driver_can_skip_payment(engine: Engine, profile: Dict[str, Any]) -> bool:
    """
    True if driver can skip Stripe/setup payment.
    1) Beta bypass: if trucker_profiles.is_beta == true, skip payment.
    2) Else: must have STARTER_PACK or FLEET_STARTER_PACK in driver_savings_ledger,
       with status in CREDITED/VESTED/CLAIMED (not revoked) and within 180 days.
    Single source of truth so beta bypass is never duplicated.
    """
    if not engine or not profile:
        return False
    if profile.get("is_beta"):
        return True
    mc = (profile.get("mc_number") or "").strip() or (profile.get("dot_number") or "").strip()
    if not mc:
        return False
    with engine.begin() as conn:
        paid = conn.execute(
            text("""
                SELECT 1 FROM webwise.driver_savings_ledger
                WHERE driver_mc_number = :mc
                  AND load_id IN ('STARTER_PACK', 'FLEET_STARTER_PACK')
                  AND status IN ('LOCKED', 'CREDITED', 'VESTED', 'CLAIMED')
                  AND earned_at >= (NOW() - INTERVAL '180 days')
                LIMIT 1
            """),
            {"mc": mc},
        ).first()
    return paid is not None


def require_trucker_profile(
    user: Optional[Dict] = Depends(current_user),
    engine: Engine = Depends(get_engine),
) -> Dict[str, Any]:
    """
    Dependency: require logged-in driver (role client or trucker) with a trucker profile.
    Returns profile dict. Does NOT enforce payment — use driver_can_skip_payment()
    where you gate on Stripe/setup.
    """
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    # Auth uses 'client' for drivers; approve may have used 'trucker' historically — allow both.
    if user.get("role") not in ("client", "trucker"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Driver access required")
    if not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")
    profile = get_trucker_profile(engine, user["id"])
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trucker profile not found")
    return profile
