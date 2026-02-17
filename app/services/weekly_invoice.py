"""
Weekly invoice batching for drivers who use WEEKLY_INVOICE billing (no factoring).
Accumulates uninvoiced DISPATCH_FEE rows from platform_revenue_ledger into driver_invoice_batches.
Run via cron/APScheduler (e.g. every Sunday night).
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Engine


def create_weekly_invoice_batches(
    engine: Engine,
    *,
    period_days: int = 7,
) -> List[Dict[str, Any]]:
    """
    Find drivers on WEEKLY_INVOICE with uninvoiced DISPATCH_FEE rows;
    create one batch per driver and assign ledger rows to it.
    Returns list of created batches: [{ batch_id, driver_mc_number, total_amount_usd }, ...].
    """
    if not engine:
        return []
    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=period_days)
    created: List[Dict[str, Any]] = []

    try:
        with engine.begin() as conn:
            # Only drivers with billing_method = WEEKLY_INVOICE and uninvoiced DISPATCH_FEE
            rows = conn.execute(
                text("""
                    SELECT prl.driver_mc_number,
                           SUM(prl.gross_amount_usd) AS total
                    FROM webwise.platform_revenue_ledger prl
                    JOIN webwise.trucker_profiles tp ON tp.mc_number = prl.driver_mc_number
                    WHERE prl.invoice_batch_id IS NULL
                      AND prl.source_type = 'DISPATCH_FEE'
                      AND tp.billing_method = 'WEEKLY_INVOICE'
                    GROUP BY prl.driver_mc_number
                    HAVING SUM(prl.gross_amount_usd) > 0
                """),
            ).mappings().all()

            for row in rows:
                mc = row["driver_mc_number"]
                total = row["total"]
                if not mc or (total or 0) <= 0:
                    continue

                batch_row = conn.execute(
                    text("""
                        INSERT INTO webwise.driver_invoice_batches
                        (driver_mc_number, period_start, period_end, total_amount_usd, status)
                        VALUES (:mc, :period_start, :period_end, :total, 'CREATED')
                        RETURNING id, driver_mc_number, total_amount_usd
                    """),
                    {
                        "mc": mc,
                        "period_start": period_start,
                        "period_end": period_end,
                        "total": total,
                    },
                ).mappings().one()

                batch_id = batch_row["id"]
                conn.execute(
                    text("""
                        UPDATE webwise.platform_revenue_ledger
                        SET invoice_batch_id = :batch_id,
                            invoiced_at = NOW()
                        WHERE driver_mc_number = :mc
                          AND invoice_batch_id IS NULL
                          AND source_type = 'DISPATCH_FEE'
                    """),
                    {"batch_id": batch_id, "mc": mc},
                )

                created.append({
                    "batch_id": str(batch_id),
                    "driver_mc_number": mc,
                    "total_amount_usd": float(total),
                })
    except Exception:
        raise

    return created
