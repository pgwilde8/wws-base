"""
Platform treasury + burn service (ORM-based).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, update, func
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.treasury import (
    PlatformRevenueLedger,
    BurnBatch,
    RevenueSourceType,
    RevenueLedgerStatus,
    BurnBatchStatus,
)


@dataclass(frozen=True)
class TreasuryStats:
    total_revenue_usd: Decimal
    total_burned_usd: Decimal
    last_burn_tx_hash: str | None
    last_burn_at: datetime | None


def _to_decimal(amount: Decimal | float | int | str) -> Decimal:
    if isinstance(amount, Decimal):
        return amount
    return Decimal(str(amount))


def _str_enum(val: RevenueSourceType | str) -> str:
    return val.value if isinstance(val, RevenueSourceType) else str(val)


def record_revenue(
    engine: Engine,
    *,
    source_type: RevenueSourceType | str,
    gross_amount_usd: Decimal | float | int | str,
    source_ref: str | None = None,
    load_id: str | None = None,
    driver_mc_number: str | None = None,
    burn_eligible: bool = True,
) -> uuid.UUID:
    """Insert a revenue row. Idempotency is handled by unique source_ref when provided."""
    st = RevenueSourceType(source_type) if isinstance(source_type, str) else source_type
    amt = _to_decimal(gross_amount_usd).quantize(Decimal("0.01"))

    with Session(engine) as session:
        row = PlatformRevenueLedger(
            source_type=_str_enum(st),
            source_ref=source_ref,
            load_id=load_id,
            driver_mc_number=driver_mc_number,
            gross_amount_usd=amt,
            burn_reserved_usd=Decimal("0.00"),
            treasury_reserved_usd=Decimal("0.00"),
            status=RevenueLedgerStatus.RECORDED.value,
            burn_eligible=burn_eligible,
        )
        session.add(row)
        session.commit()
        return row.id


def confirm_dispatch_settlement(engine: Engine, *, load_id: str) -> int:
    """
    Set burn_eligible=true for RECORDED DISPATCH_FEE rows for this load_id
    (e.g. when factoring webhook confirms settlement). Returns count updated.
    """
    with Session(engine) as session:
        r = session.execute(
            update(PlatformRevenueLedger)
            .where(PlatformRevenueLedger.load_id == load_id)
            .where(PlatformRevenueLedger.source_type == RevenueSourceType.DISPATCH_FEE.value)
            .where(PlatformRevenueLedger.burn_eligible.is_(False))
            .values(burn_eligible=True)
        )
        session.commit()
        return r.rowcount


def create_batch(
    engine: Engine,
    *,
    period_start: datetime,
    period_end: datetime,
    burn_rate_bps: int,
) -> uuid.UUID:
    with Session(engine) as session:
        batch = BurnBatch(
            period_start=period_start,
            period_end=period_end,
            burn_rate_bps=burn_rate_bps,
            usd_reserved=Decimal("0.00"),
            status=BurnBatchStatus.CREATED.value,
        )
        session.add(batch)
        session.commit()
        return batch.id


def reserve_burn_for_batch(
    engine: Engine,
    *,
    batch_id: uuid.UUID,
    burn_rate_bps: int | None = None,
) -> Decimal:
    """
    For RECORDED revenue rows within the batch period:
      - compute burn_reserved_usd = gross_amount_usd * burn_rate
      - attach burn_batch_id
      - set status = RESERVED
    Then update burn_batches.usd_reserved and status=RESERVED.
    Returns usd_reserved total.
    Guardrails: only batch status CREATED; only rows with burn_batch_id IS NULL,
    gross_amount_usd > 0, burn_eligible = true.
    """
    with Session(engine) as session:
        batch = session.get(BurnBatch, batch_id)
        if not batch:
            raise ValueError("batch not found")
        if batch.status != BurnBatchStatus.CREATED.value:
            raise ValueError("batch already reserved or executed; reserve only when status is CREATED")

        rate_bps = burn_rate_bps if burn_rate_bps is not None else batch.burn_rate_bps
        if rate_bps <= 0:
            raise ValueError("burn_rate_bps must be > 0")

        q = (
            select(PlatformRevenueLedger.id, PlatformRevenueLedger.gross_amount_usd)
            .where(PlatformRevenueLedger.status == RevenueLedgerStatus.RECORDED.value)
            .where(PlatformRevenueLedger.burn_batch_id.is_(None))
            .where(PlatformRevenueLedger.burn_eligible.is_(True))
            .where(PlatformRevenueLedger.gross_amount_usd > 0)
            .where(PlatformRevenueLedger.created_at >= batch.period_start)
            .where(PlatformRevenueLedger.created_at < batch.period_end)
        )
        rows = session.execute(q).all()

        total_reserved = Decimal("0.00")
        for rid, gross in rows:
            burn_amt = (Decimal(gross) * Decimal(rate_bps) / Decimal(10_000)).quantize(Decimal("0.01"))
            total_reserved += burn_amt

            session.execute(
                update(PlatformRevenueLedger)
                .where(PlatformRevenueLedger.id == rid)
                .values(
                    burn_reserved_usd=burn_amt,
                    burn_batch_id=batch_id,
                    status=RevenueLedgerStatus.RESERVED.value,
                )
            )

        session.execute(
            update(BurnBatch)
            .where(BurnBatch.id == batch_id)
            .values(
                burn_rate_bps=rate_bps,
                usd_reserved=total_reserved.quantize(Decimal("0.01")),
                status=BurnBatchStatus.RESERVED.value,
            )
        )

        session.commit()
        return total_reserved.quantize(Decimal("0.01"))


def execute_batch(
    engine: Engine,
    *,
    batch_id: uuid.UUID,
    swap_tx_hash: str | None,
    burn_tx_hash: str | None,
    usd_spent: Decimal | float | int | str,
    candle_burned: Decimal | float | int | str,
) -> None:
    """
    Mark batch BURNED and mark linked ledger rows BURNED.
    Chain execution happens elsewhere (ChainGateway); this function is the finalizer.
    """
    usd_spent_d = _to_decimal(usd_spent).quantize(Decimal("0.01"))
    candle_burned_d = _to_decimal(candle_burned)

    with Session(engine) as session:
        batch = session.get(BurnBatch, batch_id)
        if not batch:
            raise ValueError("batch not found")

        session.execute(
            update(PlatformRevenueLedger)
            .where(PlatformRevenueLedger.burn_batch_id == batch_id)
            .where(PlatformRevenueLedger.status == RevenueLedgerStatus.RESERVED.value)
            .values(status=RevenueLedgerStatus.BURNED.value)
        )

        session.execute(
            update(BurnBatch)
            .where(BurnBatch.id == batch_id)
            .values(
                usd_spent=usd_spent_d,
                candle_burned=candle_burned_d,
                swap_tx_hash=swap_tx_hash,
                burn_tx_hash=burn_tx_hash,
                status=BurnBatchStatus.BURNED.value,
                executed_at=func.now(),
            )
        )

        session.commit()


def get_batch(engine: Engine, batch_id: uuid.UUID) -> BurnBatch | None:
    with Session(engine) as session:
        return session.get(BurnBatch, batch_id)


def list_batches(
    engine: Engine,
    *,
    limit: int = 25,
    status: BurnBatchStatus | str | None = None,
) -> list[BurnBatch]:
    with Session(engine) as session:
        stmt = select(BurnBatch).order_by(BurnBatch.created_at.desc()).limit(limit)
        if status is not None:
            st = BurnBatchStatus(status) if isinstance(status, str) else status
            stmt = stmt.where(BurnBatch.status == st.value)
        return list(session.scalars(stmt).all())


def get_treasury_stats(engine: Engine) -> TreasuryStats:
    with Session(engine) as session:
        total_revenue = session.execute(
            select(func.coalesce(func.sum(PlatformRevenueLedger.gross_amount_usd), 0))
            .select_from(PlatformRevenueLedger)
            .where(PlatformRevenueLedger.status != RevenueLedgerStatus.VOID.value)
        ).scalar_one()

        total_burned = session.execute(
            select(func.coalesce(func.sum(PlatformRevenueLedger.burn_reserved_usd), 0))
            .select_from(PlatformRevenueLedger)
            .where(PlatformRevenueLedger.status == RevenueLedgerStatus.BURNED.value)
        ).scalar_one()

        last = session.execute(
            select(BurnBatch.burn_tx_hash, BurnBatch.executed_at)
            .where(BurnBatch.status == BurnBatchStatus.BURNED.value)
            .order_by(BurnBatch.executed_at.desc().nullslast(), BurnBatch.created_at.desc())
            .limit(1)
        ).first()

        last_hash = last[0] if last else None
        last_at = last[1] if last else None

        return TreasuryStats(
            total_revenue_usd=Decimal(total_revenue).quantize(Decimal("0.01")),
            total_burned_usd=Decimal(total_burned).quantize(Decimal("0.01")),
            last_burn_tx_hash=last_hash,
            last_burn_at=last_at,
        )
