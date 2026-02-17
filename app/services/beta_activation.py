"""
Beta driver activation: track stage and last activity so we see where drivers drop off.
Only updates rows where is_beta = true.
Stage advancement is deterministic: numeric rank prevents regressions (e.g. LOGGED_IN
never overwrites FIRST_LOAD_FUNDED on dashboard refresh).
ACTIVE is never stored: it is a derived display rule (FIRST_LOAD_FUNDED + activity within 14 days).
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sqlalchemy import text
from sqlalchemy.engine import Engine

# Canonical stage order — advance only when new_rank > current_rank
STAGE_ORDER = {
    "APPROVED": 10,
    "LOGGED_IN": 20,
    "PROFILE_COMPLETED": 30,
    "FIRST_SCOUT": 40,
    "FIRST_NEGOTIATION": 50,
    "FIRST_LOAD_WON": 60,
    "FIRST_LOAD_FUNDED": 70,
    # ACTIVE is never stored; derived in admin UI when FIRST_LOAD_FUNDED + last_activity within 14 days
}

STAGE_APPROVED = "APPROVED"
STAGE_LOGGED_IN = "LOGGED_IN"
STAGE_PROFILE_COMPLETED = "PROFILE_COMPLETED"
STAGE_FIRST_SCOUT = "FIRST_SCOUT"
STAGE_FIRST_NEGOTIATION = "FIRST_NEGOTIATION"
STAGE_FIRST_LOAD_WON = "FIRST_LOAD_WON"
STAGE_FIRST_LOAD_FUNDED = "FIRST_LOAD_FUNDED"
STAGE_ACTIVE = "ACTIVE"  # display only

ACTIVE_DAYS_THRESHOLD = 14  # for "ACTIVE" badge: FIRST_LOAD_FUNDED + activity within N days


def _rank(stage: str | None) -> int:
    if not stage:
        return 0
    return STAGE_ORDER.get(stage, 0)


def update_beta_activity(
    engine: Engine,
    *,
    user_id: int | None = None,
    trucker_id: int | None = None,
    new_stage: str | None = None,
) -> None:
    """
    Update beta_last_activity_at and optionally advance beta_activation_stage.
    Only affects rows with is_beta = true. Pass user_id OR trucker_id.
    Advancement is deterministic: new_stage is written only if its rank > current stage rank.
    ACTIVE is never written; use FIRST_LOAD_FUNDED as the top stored stage.
    """
    if not engine or (not user_id and not trucker_id):
        return
    # Never store ACTIVE in DB
    if new_stage == STAGE_ACTIVE:
        new_stage = STAGE_FIRST_LOAD_FUNDED
    where = "user_id = :uid" if user_id is not None else "id = :tid"
    params: dict = {"uid": user_id} if user_id is not None else {"tid": trucker_id}

    try:
        with engine.begin() as conn:
            if new_stage and new_stage in STAGE_ORDER:
                # Fetch current stage so we only advance, never regress
                current = conn.execute(
                    text(f"""
                        SELECT beta_activation_stage FROM webwise.trucker_profiles
                        WHERE {where} AND is_beta = true
                        LIMIT 1
                    """),
                    params,
                ).first()
                current_stage = (current[0] if current and current[0] else None) or "APPROVED"
                if _rank(new_stage) <= _rank(current_stage):
                    # Touch last_activity only, no stage change
                    conn.execute(
                        text(f"""
                            UPDATE webwise.trucker_profiles
                            SET beta_last_activity_at = NOW(),
                                beta_onboarded_at = COALESCE(beta_onboarded_at, NOW())
                            WHERE {where} AND is_beta = true
                        """),
                        params,
                    )
                    return
                params["new_stage"] = new_stage
                conn.execute(
                    text(f"""
                        UPDATE webwise.trucker_profiles
                        SET beta_last_activity_at = NOW(),
                            beta_onboarded_at = COALESCE(beta_onboarded_at, NOW()),
                            beta_activation_stage = :new_stage
                        WHERE {where} AND is_beta = true
                    """),
                    params,
                )
            else:
                conn.execute(
                    text(f"""
                        UPDATE webwise.trucker_profiles
                        SET beta_last_activity_at = NOW(),
                            beta_onboarded_at = COALESCE(beta_onboarded_at, NOW())
                        WHERE {where} AND is_beta = true
                    """),
                    params,
                )
    except Exception:
        pass  # Columns may not exist; run migrate_beta_activation.sql


def display_stage(stage: str | None, last_activity: datetime | None) -> str:
    """
    Derive display stage for admin UI. ACTIVE = FIRST_LOAD_FUNDED + activity within ACTIVE_DAYS_THRESHOLD.
    """
    if not stage:
        return STAGE_APPROVED
    if stage != STAGE_FIRST_LOAD_FUNDED:
        return stage
    if not last_activity:
        return stage
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=ACTIVE_DAYS_THRESHOLD)
    last_ts = last_activity if last_activity.tzinfo else last_activity.replace(tzinfo=timezone.utc)
    if last_ts >= cutoff:
        return STAGE_ACTIVE
    return stage
