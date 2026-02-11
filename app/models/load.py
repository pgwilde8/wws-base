"""
Load model - stores raw scrape results from load boards.
Used by Chrome Extension ingestion endpoint.
"""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from .bootstrap_db import Base


class Load(Base):
    """Raw load data from load boards (DAT, Truckstop, etc.)"""
    __tablename__ = "loads"
    __table_args__ = {"schema": "webwise"}

    id = Column(Integer, primary_key=True, index=True)
    ref_id = Column(String, unique=True, index=True)  # The Load Board's ID (e.g. DAT-12345)
    
    origin = Column(String)
    destination = Column(String)
    price = Column(String)  # Keep as string initially to handle "$1,200" vs "1200"
    equipment_type = Column(String)  # Van, Reefer, Flatbed
    pickup_date = Column(String)
    
    status = Column(String, default="NEW")  # NEW, ANALYZED, HIDDEN, WON
    
    # Store the raw scrape data here just in case parsing fails
    raw_data = Column(JSONB)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
