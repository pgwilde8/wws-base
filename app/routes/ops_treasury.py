"""
Ops routes: treasury visibility.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from sqlalchemy.engine import Engine

from app.core.deps import get_engine, require_admin
from app.services.burn import get_treasury_stats

router = APIRouter(prefix="/ops", tags=["ops"], dependencies=[Depends(require_admin)])


@router.get("/treasury")
def treasury_stats(engine: Engine = Depends(get_engine)):
    stats = get_treasury_stats(engine)
    return {
        "total_revenue_usd": str(stats.total_revenue_usd),
        "total_burned_usd": str(stats.total_burned_usd),
        "last_burn_tx_hash": stats.last_burn_tx_hash,
        "last_burn_at": stats.last_burn_at,
    }
