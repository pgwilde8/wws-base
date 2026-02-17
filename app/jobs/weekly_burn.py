"""
Weekly burn job (APScheduler-style).
Creates a 7-day burn batch, reserves amounts, optionally executes on-chain (placeholder).
Supports MAX_BURN_USD_PER_BATCH cap and DRY_RUN mode.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.engine import Engine

from app.core.deps import engine
from app.services.burn import create_batch, reserve_burn_for_batch, execute_batch


def run_weekly_burn(
    *,
    burn_rate_bps: int = 1000,
    period_end: datetime | None = None,
    execute_on_chain: bool = False,
    dry_run: bool | None = None,
) -> dict:
    """
    Creates a 7-day burn batch ending at period_end (default now UTC),
    reserves burn amounts, and optionally executes on-chain (placeholder).
    - dry_run: if True, only create+reserve and return totals (no execute). Default from env DRY_RUN.
    - MAX_BURN_USD_PER_BATCH (env): hard cap; if usd_reserved exceeds it, do not execute and report.
    """
    if period_end is None:
        period_end = datetime.now(timezone.utc)

    period_start = period_end - timedelta(days=7)

    if not engine:
        return {"error": "Database not configured"}
    eng: Engine = engine

    dry_run_mode = dry_run if dry_run is not None else (os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes"))
    max_burn_usd_raw = os.getenv("MAX_BURN_USD_PER_BATCH")
    max_burn_usd = Decimal(max_burn_usd_raw).quantize(Decimal("0.01")) if max_burn_usd_raw else None

    batch_id = create_batch(
        eng,
        period_start=period_start,
        period_end=period_end,
        burn_rate_bps=burn_rate_bps,
    )

    usd_reserved = reserve_burn_for_batch(
        eng,
        batch_id=batch_id,
        burn_rate_bps=burn_rate_bps,
    )

    result = {
        "batch_id": str(batch_id),
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "burn_rate_bps": burn_rate_bps,
        "usd_reserved": str(usd_reserved),
        "executed": False,
        "dry_run": dry_run_mode,
    }

    if dry_run_mode:
        result["note"] = "DRY_RUN: create+reserve only; no on-chain execution"
        return result

    if max_burn_usd is not None and usd_reserved > max_burn_usd:
        result["capped"] = True
        result["max_burn_usd_per_batch"] = str(max_burn_usd)
        result["note"] = f"usd_reserved {usd_reserved} exceeds MAX_BURN_USD_PER_BATCH {max_burn_usd}; not executing"
        return result

    if not execute_on_chain:
        return result

    # Placeholder for ChainGateway swap + burn execution.
    swap_tx_hash = "0xSWAP_PLACEHOLDER"
    burn_tx_hash = "0xBURN_PLACEHOLDER"
    usd_spent = Decimal(str(usd_reserved)).quantize(Decimal("0.01"))
    candle_burned = Decimal("0")

    execute_batch(
        eng,
        batch_id=batch_id,
        swap_tx_hash=swap_tx_hash,
        burn_tx_hash=burn_tx_hash,
        usd_spent=usd_spent,
        candle_burned=candle_burned,
    )

    result["executed"] = True
    result["swap_tx_hash"] = swap_tx_hash
    result["burn_tx_hash"] = burn_tx_hash
    result["usd_spent"] = str(usd_spent)
    result["candle_burned"] = str(candle_burned)
    return result


def job_weekly_burn() -> None:
    """Default weekly burn with no on-chain execution (safe by default)."""
    run_weekly_burn(burn_rate_bps=1000, execute_on_chain=False)
