"""
Claim Request Model - Tracks driver requests to claim vested tokens.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
import enum
from .bootstrap_db import Base


class ClaimStatus(enum.Enum):
    PENDING = "pending"      # Driver submitted request, awaiting admin approval
    APPROVED = "approved"   # Admin approved, ready to process payment
    PAID = "paid"           # Tokens sent to wallet (tx_hash filled)
    REJECTED = "rejected"   # Admin rejected the claim


class ClaimRequest(Base):
    """Tracks driver claim requests for vested tokens."""
    __tablename__ = "claim_requests"
    __table_args__ = {"schema": "webwise"}

    id = Column(Integer, primary_key=True, index=True)
    trucker_id = Column(Integer, ForeignKey("webwise.trucker_profiles.id"), nullable=False, index=True)
    
    # Claim Details
    amount_candle = Column(Float, nullable=False)  # Amount of $CANDLE requested
    wallet_address = Column(String(255), nullable=False)  # Solana/Ethereum address
    
    # Status Tracking
    status = Column(Enum(ClaimStatus), default=ClaimStatus.PENDING)
    
    # Blockchain Proof (filled after payment)
    tx_hash = Column(String(66), nullable=True)  # Transaction hash when paid
    
    # Timestamps
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
