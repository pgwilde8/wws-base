"""Driver/truck profile for attributing Wins and Green Candle contribution per trucker."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .bootstrap_db import Base


class TruckerProfile(Base):
    """One per driver/truck. Links to webwise.users; negotiations reference this for per-driver revenue."""
    __tablename__ = "trucker_profiles"
    __table_args__ = {"schema": "webwise"}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("webwise.users.id"), nullable=True, index=True)  # optional until auth is required

    display_name = Column(String(120), nullable=False)       # "Mike J." or company name
    carrier_name = Column(String(200), nullable=True)       # Fleet/carrier
    truck_identifier = Column(String(80), nullable=True)     # Unit #, plate, or "Truck 1"
    mc_number = Column(String(50), nullable=True)           # MC if applicable
    dot_number = Column(String(50), nullable=True)          # DOT number if applicable
    authority_type = Column(String(10), default="MC")      # 'MC' or 'DOT' - which identifier is primary
    reward_tier = Column(String(20), default="STANDARD")     # 'STANDARD' (75/25) or 'INCENTIVE' (90/10)
    wallet_address = Column(String(255), nullable=True)     # Solana/Ethereum wallet for token claims
    scout_api_key = Column(String(64), unique=True, nullable=True, index=True)  # API key for Scout extension

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # negotiations = relationship("Negotiation", back_populates="trucker")  # when ORM is used
