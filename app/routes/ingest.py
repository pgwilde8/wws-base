from fastapi import APIRouter, HTTPException, Depends, Request, Header
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from app.core.deps import get_db, engine
from sqlalchemy import text
import app.crud as crud
from app.schemas.load import LoadCreate

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingest")

router = APIRouter()

def analyze_profitability(load: LoadCreate):
    try:
        clean_price = load.price.replace("$", "").replace(",", "").strip()
        price_num = float(clean_price)
        if price_num >= 2000:
            return True, price_num
        return False, price_num
    except:
        return False, 0


def get_trucker_by_api_key(api_key: Optional[str]) -> Optional[int]:
    """Get trucker_id from API key. Returns None if invalid."""
    if not api_key or not engine:
        return None
    try:
        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT id FROM webwise.trucker_profiles WHERE scout_api_key = :api_key"),
                {"api_key": api_key}
            ).fetchone()
            return row.id if row else None
    except Exception as e:
        logger.error(f"Error looking up API key: {e}")
        return None

@router.post("/loads", status_code=200)
def ingest_loads(
    loads: List[LoadCreate], 
    db: Session = Depends(get_db),
    request: Request = None,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Ingest loads from Chrome Extension.
    Requires API key authentication via X-API-Key header.
    """
    # Authenticate via API key
    trucker_id = get_trucker_by_api_key(x_api_key)
    
    if not trucker_id:
        logger.warning("⚠️ [INGEST] Unauthorized request - missing or invalid API key")
        raise HTTPException(status_code=401, detail="Invalid or missing API key. Please configure your Scout Extension.")
    
    logger.info(f"📥 [INGEST] Received payload batch of {len(loads)} loads from trucker_id={trucker_id}")

    new_count = 0
    high_value_count = 0

    for load_data in loads:
        # Deduplicate
        existing_load = crud.get_load_by_ref(db, ref_id=load_data.ref_id)
        if existing_load:
            continue

        # Analyze
        is_winner, numeric_price = analyze_profitability(load_data)

        if is_winner:
            logger.info(f"🔥 HOT LOAD: {load_data.origin} -> {load_data.destination} (${numeric_price})")
            high_value_count += 1

        # Save with discoverer tracking
        crud.create_load(db=db, load=load_data, discovered_by_id=trucker_id)
        new_count += 1

    return {
        "status": "success", 
        "new": new_count, 
        "hot": high_value_count,
        "message": f"Processed {new_count} loads. {high_value_count} high-value loads detected."
    }
