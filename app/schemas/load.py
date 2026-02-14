from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class LoadStatus(str, Enum):
    DETECTED = "detected"
    WON = "won"
    DELIVERED = "delivered"
    PENDING_DOCS = "pending_docs"
    READY_FOR_FUNDING = "ready_for_funding"
    FUNDED = "funded"

# The "Base" is what we share across the app
class LoadBase(BaseModel):
    load_board_id: str
    mc_number: str
    broker_name: str
    origin: str
    destination: str
    final_rate: float

# The "Response" is what we send back to the frontend/app
class LoadResponse(LoadBase):
    id: int
    status: LoadStatus
    bol_url: Optional[str] = None
    dispatch_fee_amount: float = 0.0
    token_buyback_amount: float = 0.0
    created_at: datetime
    bank_status: Optional[str] = None  # Factoring company response

    class Config:
        from_attributes = True


# Ingestion schema for Chrome Extension scraping
class LoadIngestionBase(BaseModel):
    ref_id: str
    origin: str
    destination: str
    price: str
    equipment_type: str
    pickup_date: Optional[str] = None
    load_source: Optional[str] = None  # e.g., 'trucksmarter', 'dat', 'truckstop'


class LoadCreate(LoadIngestionBase):
    pass