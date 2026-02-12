"""Debit Card model for tracking GC Fuel & Fleet Card status."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func

from .bootstrap_db import Base


class DebitCard(Base):
    """Tracks debit card requests and status for drivers."""
    __tablename__ = "debit_cards"
    __table_args__ = {"schema": "webwise"}

    id = Column(Integer, primary_key=True, index=True)
    trucker_id = Column(Integer, ForeignKey("webwise.trucker_profiles.id"), nullable=False, index=True, unique=True)
    
    # Card status: NOT_STARTED, REQUESTED, SHIPPED, ACTIVE
    status = Column(String(20), default="NOT_STARTED", nullable=False)
    
    # Card details (filled when card is shipped/activated)
    card_last_four = Column(String(4), nullable=True)  # Last 4 digits of card
    current_balance_usd = Column(Numeric(10, 2), default=0.0)  # Available balance on card
    
    # Timestamps
    requested_at = Column(DateTime(timezone=True), nullable=True)  # When driver requested card
    shipped_at = Column(DateTime(timezone=True), nullable=True)  # When card was shipped
    activated_at = Column(DateTime(timezone=True), nullable=True)  # When card was activated
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
