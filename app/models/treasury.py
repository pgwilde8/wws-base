"""
SQLAlchemy models for platform treasury + burn (webwise schema).
Option B: plain String columns (no Postgres enums); Python enums for validation.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.bootstrap_db import Base


class RevenueSourceType(str, enum.Enum):
    DISPATCH_FEE = "DISPATCH_FEE"
    FACTOR_REFERRAL = "FACTOR_REFERRAL"
    CALL_PACK = "CALL_PACK"
    AUTOMATION_PURCHASE = "AUTOMATION_PURCHASE"
    BROKER_SUBSCRIPTION = "BROKER_SUBSCRIPTION"


class RevenueLedgerStatus(str, enum.Enum):
    RECORDED = "RECORDED"
    RESERVED = "RESERVED"
    BURNED = "BURNED"
    VOID = "VOID"


class BurnBatchStatus(str, enum.Enum):
    CREATED = "CREATED"
    RESERVED = "RESERVED"
    FUNDED = "FUNDED"
    SWAPPED = "SWAPPED"
    BURNED = "BURNED"
    FAILED = "FAILED"


class TreasuryWalletName(str, enum.Enum):
    TREASURY = "TREASURY"
    BURN_EXECUTOR = "BURN_EXECUTOR"
    BURN_ADDRESS = "BURN_ADDRESS"


class PlatformRevenueLedger(Base):
    __tablename__ = "platform_revenue_ledger"
    __table_args__ = (
        Index(
            "uq_platform_revenue_ledger_source_ref_not_null",
            "source_ref",
            unique=True,
            postgresql_where=text("source_ref IS NOT NULL"),
        ),
        Index("ix_platform_revenue_ledger_created_at", "created_at"),
        Index("ix_platform_revenue_ledger_status", "status"),
        Index("ix_platform_revenue_ledger_burn_batch_id", "burn_batch_id"),
        Index("ix_platform_revenue_ledger_status_created_at", "status", "created_at"),
        {"schema": "webwise"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)

    load_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    driver_mc_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    gross_amount_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    burn_reserved_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    treasury_reserved_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))

    burn_batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="RECORDED")

    burn_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )


class BurnBatch(Base):
    __tablename__ = "burn_batches"
    __table_args__ = (
        Index("ix_burn_batches_created_at", "created_at"),
        Index("ix_burn_batches_status", "status"),
        {"schema": "webwise"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    burn_rate_bps: Mapped[int] = mapped_column(Integer, nullable=False)

    usd_reserved: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    usd_spent: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    candle_burned: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)

    swap_tx_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    burn_tx_hash: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="CREATED")

    chain: Mapped[str] = mapped_column(String(20), nullable=False, default="base")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TreasuryWallet(Base):
    __tablename__ = "treasury_wallets"
    __table_args__ = (
        Index("uq_treasury_wallets_wallet_name_chain", "wallet_name", "chain", unique=True),
        {"schema": "webwise"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    wallet_name: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    chain: Mapped[str] = mapped_column(String(20), nullable=False, default="base")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
