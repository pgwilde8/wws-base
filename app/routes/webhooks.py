"""
Webhooks for revenue ingestion into platform_revenue_ledger (MVP-style payloads).
"""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.core.deps import get_engine
from app.services.burn import record_revenue, confirm_dispatch_settlement
from app.services.beta_activation import update_beta_activity, STAGE_FIRST_LOAD_FUNDED
from app.models.treasury import RevenueSourceType

router = APIRouter(tags=["webhooks"])


class StripeRevenueIn(BaseModel):
    amount_cents: int | None = Field(default=None, ge=1)
    amount_usd: Decimal | None = Field(default=None, ge=Decimal("0.01"))
    source_type: str | None = None  # CALL_PACK | AUTOMATION_PURCHASE | BROKER_SUBSCRIPTION
    source_ref: str | None = None  # stripe_charge_id / idempotency_key


class FactoringRevenueIn(BaseModel):
    amount_usd: Decimal | None = Field(default=None, ge=Decimal("0.01"))
    referral_fee_usd: Decimal | None = Field(default=None, ge=Decimal("0.01"))
    settlement_id: str | None = None
    load_id: str | None = None
    driver_mc_number: str | None = None


@router.post("/stripe")
def webhook_stripe(body: StripeRevenueIn, engine: Engine = Depends(get_engine)):
    if body.amount_usd is None and body.amount_cents is None:
        raise HTTPException(status_code=400, detail="amount_usd or amount_cents required")
    if not body.source_ref or not str(body.source_ref).strip():
        raise HTTPException(status_code=400, detail="source_ref required for idempotency (e.g. stripe_charge_id)")

    amount = body.amount_usd
    if amount is None:
        amount = (Decimal(body.amount_cents) / Decimal(100)).quantize(Decimal("0.01"))

    st = body.source_type or RevenueSourceType.AUTOMATION_PURCHASE.value
    if st not in (
        RevenueSourceType.CALL_PACK.value,
        RevenueSourceType.AUTOMATION_PURCHASE.value,
        RevenueSourceType.BROKER_SUBSCRIPTION.value,
    ):
        st = RevenueSourceType.AUTOMATION_PURCHASE.value

    try:
        rid = record_revenue(
            engine,
            source_type=st,
            gross_amount_usd=amount,
            source_ref=body.source_ref,
        )
    except Exception as e:
        return {"status": "ok", "note": f"ignored duplicate or error: {e}"}

    return {"status": "ok", "revenue_id": str(rid)}


@router.post("/factoring")
def webhook_factoring(body: FactoringRevenueIn, engine: Engine = Depends(get_engine)):
    if body.amount_usd is None and body.referral_fee_usd is None:
        raise HTTPException(status_code=400, detail="amount_usd or referral_fee_usd required")

    created = []

    if body.amount_usd is not None:
        rid = record_revenue(
            engine,
            source_type=RevenueSourceType.DISPATCH_FEE.value,
            gross_amount_usd=body.amount_usd,
            source_ref=body.settlement_id,
            load_id=body.load_id,
            driver_mc_number=body.driver_mc_number,
        )
        created.append(str(rid))

    if body.referral_fee_usd is not None:
        rid = record_revenue(
            engine,
            source_type=RevenueSourceType.FACTOR_REFERRAL.value,
            gross_amount_usd=body.referral_fee_usd,
            source_ref=(f"ref-{body.settlement_id}" if body.settlement_id else None),
            load_id=body.load_id,
            driver_mc_number=body.driver_mc_number,
        )
        created.append(str(rid))

    # Confirm dispatch fee as burn-eligible when factoring settles (mark-won rows had burn_eligible=false)
    if body.load_id and str(body.load_id).strip():
        updated = confirm_dispatch_settlement(engine, load_id=str(body.load_id).strip())
        if updated:
            # Beta activation: FIRST_LOAD_FUNDED only for is_beta, matching load, idempotent (rank-based)
            load_id_clean = str(body.load_id).strip()
            mc_clean = str(body.driver_mc_number).strip() if body.driver_mc_number else ""
            if mc_clean and load_id_clean:
                with engine.begin() as conn:
                    # Scope: this load was won by this beta driver (avoid wrong driver / mistyped MC)
                    row = conn.execute(
                        text("""
                            SELECT tp.id FROM webwise.trucker_profiles tp
                            JOIN webwise.negotiations n ON n.trucker_id = tp.id AND n.load_id = :load_id AND n.status = 'won'
                            WHERE tp.mc_number = :mc AND tp.is_beta = true
                            LIMIT 1
                        """),
                        {"mc": mc_clean, "load_id": load_id_clean},
                    ).first()
                    if row:
                        update_beta_activity(engine, trucker_id=row[0], new_stage=STAGE_FIRST_LOAD_FUNDED)
            return {"status": "ok", "revenue_ids": created, "dispatch_confirmed_for_load": body.load_id}

    return {"status": "ok", "revenue_ids": created}
