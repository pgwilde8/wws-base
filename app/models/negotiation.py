from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from .bootstrap_db import Base # Adjust based on your actual Base location

class NegotiationStatus(enum.Enum):
    PENDING = "pending"     # AI drafted, waiting for driver or broker
    SENT = "sent"           # Email/SMS actually sent to broker
    REPLIED = "replied"     # Broker responded
    WON = "won"             # Rate agreed, load booked
    LOST = "lost"           # Broker gave it to someone else or rejected price

class Negotiation(Base):
    __tablename__ = "negotiations"
    __table_args__ = {"schema": "webwise"}

    id = Column(Integer, primary_key=True, index=True)
    load_id = Column(String, index=True)  # External ID from Load Board (DAT/Mock)
    
    # Negotiation Details
    origin = Column(String)
    destination = Column(String)
    original_rate = Column(Float)         # What the broker posted
    target_rate = Column(Float)           # What the AI asked for
    final_rate = Column(Float, nullable=True) # The "Win" price
    
    # AI Content
    ai_draft_subject = Column(String)
    ai_draft_body = Column(Text)
    broker_reply = Column(Text, nullable=True)
    
    # Meta
    status = Column(Enum(NegotiationStatus), default=NegotiationStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Per-driver attribution (Green Candle contribution)
    trucker_id = Column(Integer, ForeignKey("webwise.trucker_profiles.id"), nullable=True, index=True)