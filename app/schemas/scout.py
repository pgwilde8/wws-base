from pydantic import BaseModel
from typing import List, Optional


class ScoutUpdate(BaseModel):
    """Payload from Chrome Extension Scout heartbeat."""
    lanes: List[str] = []
    min_rpm: float = 2.45
    active: bool = True
