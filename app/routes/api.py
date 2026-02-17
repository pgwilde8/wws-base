"""
API routes for external integrations (Chrome Extension Scout, etc.).
"""
from fastapi import APIRouter, HTTPException, Header
from typing import Optional

from app.schemas.scout import ScoutUpdate
from app.core.deps import engine
from app.services.beta_activation import update_beta_activity, STAGE_FIRST_SCOUT
from sqlalchemy import text

router = APIRouter(prefix="/api", tags=["api"])


def _get_trucker_by_api_key(api_key: Optional[str]) -> Optional[int]:
    """Resolve X-API-Key to trucker_id."""
    if not api_key or not engine:
        return None
    try:
        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT id FROM webwise.trucker_profiles WHERE scout_api_key = :api_key"),
                {"api_key": api_key}
            ).fetchone()
            return row[0] if row else None
    except Exception:
        return None


@router.post("/scout/heartbeat")
async def scout_heartbeat(
    payload: ScoutUpdate,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Chrome Extension Scout sends heartbeat: lanes, min_rpm, active.
    Stores in scout_status table. Requires X-API-Key header.
    """
    trucker_id = _get_trucker_by_api_key(x_api_key)
    if not trucker_id:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    lanes_str = ", ".join(payload.lanes) if payload.lanes else ""
    if not engine:
        return {"status": "received", "warning": "Database unavailable"}

    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO webwise.scout_status (trucker_id, lanes, min_rpm, active, updated_at)
                    VALUES (:tid, :lanes, :min_rpm, :active, now())
                    ON CONFLICT (trucker_id) DO UPDATE SET
                        lanes = EXCLUDED.lanes,
                        min_rpm = EXCLUDED.min_rpm,
                        active = EXCLUDED.active,
                        updated_at = now()
                """),
                {
                    "tid": trucker_id,
                    "lanes": lanes_str,
                    "min_rpm": payload.min_rpm,
                    "active": payload.active,
                },
            )
        update_beta_activity(engine, trucker_id=trucker_id, new_stage=STAGE_FIRST_SCOUT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "received"}
