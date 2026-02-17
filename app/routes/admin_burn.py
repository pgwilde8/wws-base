"""
Admin burn routes: create/list/reserve/execute burn batches.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy.engine import Engine

from app.core.deps import get_engine, require_admin
from app.models.treasury import BurnBatchStatus
from app.services.burn import (
    create_batch,
    reserve_burn_for_batch,
    execute_batch,
    get_batch,
    list_batches,
)

router = APIRouter(prefix="/admin/burn", tags=["admin-burn"], dependencies=[Depends(require_admin)])


class CreateBatchIn(BaseModel):
    period_start: datetime
    period_end: datetime
    burn_rate_bps: int = Field(default=1000, ge=1, le=5000)  # default 10%, cap 50%


class CreateBatchOut(BaseModel):
    batch_id: uuid.UUID
    status: str


@router.post("/batches", response_model=CreateBatchOut)
def create_burn_batch(body: CreateBatchIn, engine: Engine = Depends(get_engine)):
    batch_id = create_batch(
        engine,
        period_start=body.period_start,
        period_end=body.period_end,
        burn_rate_bps=body.burn_rate_bps,
    )
    return CreateBatchOut(batch_id=batch_id, status="CREATED")


@router.get("/batches")
def list_burn_batches(
    limit: int = 25,
    status_filter: str | None = None,
    engine: Engine = Depends(get_engine),
):
    status = BurnBatchStatus(status_filter) if status_filter else None
    batches = list_batches(engine, limit=limit, status=status)
    return [
        {
            "id": b.id,
            "period_start": b.period_start,
            "period_end": b.period_end,
            "burn_rate_bps": b.burn_rate_bps,
            "usd_reserved": str(b.usd_reserved),
            "usd_spent": str(b.usd_spent) if b.usd_spent is not None else None,
            "candle_burned": str(b.candle_burned) if b.candle_burned is not None else None,
            "swap_tx_hash": b.swap_tx_hash,
            "burn_tx_hash": b.burn_tx_hash,
            "status": b.status,
            "created_at": b.created_at,
            "executed_at": b.executed_at,
        }
        for b in batches
    ]


@router.get("/batches/{batch_id}")
def get_one_batch(batch_id: uuid.UUID, engine: Engine = Depends(get_engine)):
    b = get_batch(engine, batch_id)
    if not b:
        raise HTTPException(status_code=404, detail="batch not found")
    return {
        "id": b.id,
        "period_start": b.period_start,
        "period_end": b.period_end,
        "burn_rate_bps": b.burn_rate_bps,
        "usd_reserved": str(b.usd_reserved),
        "usd_spent": str(b.usd_spent) if b.usd_spent is not None else None,
        "candle_burned": str(b.candle_burned) if b.candle_burned is not None else None,
        "swap_tx_hash": b.swap_tx_hash,
        "burn_tx_hash": b.burn_tx_hash,
        "status": b.status,
        "created_at": b.created_at,
        "executed_at": b.executed_at,
    }


class ReserveIn(BaseModel):
    burn_rate_bps: int | None = Field(default=None, ge=1, le=5000)


@router.post("/batches/{batch_id}/reserve")
def reserve_batch(batch_id: uuid.UUID, body: ReserveIn, engine: Engine = Depends(get_engine)):
    try:
        total = reserve_burn_for_batch(engine, batch_id=batch_id, burn_rate_bps=body.burn_rate_bps)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"batch_id": batch_id, "usd_reserved": str(total), "status": "RESERVED"}


class ExecuteIn(BaseModel):
    swap_tx_hash: str | None = None
    burn_tx_hash: str | None = None
    usd_spent: Decimal
    candle_burned: Decimal


@router.post("/batches/{batch_id}/execute")
def execute_one_batch(batch_id: uuid.UUID, body: ExecuteIn, engine: Engine = Depends(get_engine)):
    try:
        execute_batch(
            engine,
            batch_id=batch_id,
            swap_tx_hash=body.swap_tx_hash,
            burn_tx_hash=body.burn_tx_hash,
            usd_spent=body.usd_spent,
            candle_burned=body.candle_burned,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"batch_id": batch_id, "status": "BURNED"}
