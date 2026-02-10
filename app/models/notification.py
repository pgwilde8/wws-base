from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

from .bootstrap_db import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {"schema": "webwise"}

    id = Column(Integer, primary_key=True, index=True)
    trucker_id = Column(Integer, ForeignKey("webwise.trucker_profiles.id"), nullable=False, index=True)
    message = Column(String(500), nullable=False)
    notif_type = Column(String(50), nullable=False, default="info")  # e.g. NEGOTIATION_DRAFT, LOAD_WON
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
