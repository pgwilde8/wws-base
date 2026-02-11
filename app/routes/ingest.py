from fastapi import APIRouter, HTTPException, BackgroundTasks, Body
from sqlalchemy import text
import json

from app.core.deps import engine
# from app.services.ai_agent import evaluate_load_profitability # Uncomment when AI is ready

router = APIRouter()


@router.post("/api/ingest/loads")
async def ingest_loads(
    background_tasks: BackgroundTasks,
    loads_data: list = Body(...)
):
    """
    Receives raw load data from the Chrome Extension (Chrome Extension "Side-Saddle" method).
    Expects JSON body: [{'ref_id': '...', 'origin': '...', 'destination': '...', 'price': '...', ...}]
    
    This is the "Zero-Budget" scraping approach - driver's Chrome extension sends data to your backend.
    """
    if not engine:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # If it's a single dict, wrap in list
        if isinstance(loads_data, dict):
            loads_data = [loads_data]
            
        new_load_count = 0
        updated_load_count = 0
        
        with engine.begin() as conn:
            for raw_load in loads_data:
                ref_id = raw_load.get('ref_id')
                if not ref_id:
                    continue

                # 1. Check if load exists (deduplication)
                existing = conn.execute(
                    text("SELECT id FROM webwise.loads WHERE ref_id = :ref_id"),
                    {"ref_id": str(ref_id)}
                ).fetchone()
                
                if existing:
                    # Update timestamp if load already exists
                    conn.execute(
                        text("UPDATE webwise.loads SET updated_at = now() WHERE ref_id = :ref_id"),
                        {"ref_id": str(ref_id)}
                    )
                    updated_load_count += 1
                    continue
                
                # 2. Create New Load (store raw scrape data)
                conn.execute(
                    text("""
                        INSERT INTO webwise.loads (
                            ref_id, origin, destination, price, equipment_type, 
                            pickup_date, status, raw_data, created_at
                        )
                        VALUES (
                            :ref_id, :origin, :destination, :price, :equipment_type,
                            :pickup_date, :status, :raw_data::jsonb, now()
                        )
                    """),
                    {
                        "ref_id": str(ref_id),
                        "origin": raw_load.get('origin', 'Unknown'),
                        "destination": raw_load.get('destination', 'Unknown'),
                        "price": raw_load.get('price'),
                        "equipment_type": raw_load.get('equipment_type', 'Unknown'),
                        "pickup_date": raw_load.get('pickup_date'),
                        "status": "NEW",
                        "raw_data": json.dumps(raw_load)  # Store full blob as JSONB
                    }
                )
                new_load_count += 1
                
                # 3. TRIGGER AI EVALUATION (Future Step)
                # When AI is ready, this will analyze profitability and auto-draft negotiations
                # background_tasks.add_task(evaluate_load_profitability, ref_id)
        
        return {
            "status": "success", 
            "message": f"Processed {len(loads_data)} items.",
            "new_loads": new_load_count,
            "updated_loads": updated_load_count
        }

    except Exception as e:
        import traceback
        print(f"❌ Ingestion Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")