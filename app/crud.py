from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.load import Load
from app.schemas.load import LoadCreate

def get_load_by_ref(db: Session, ref_id: str):
    return db.query(Load).filter(Load.ref_id == ref_id).first()

def create_load(db: Session, load: LoadCreate, discovered_by_id: Optional[int] = None):
    db_load = Load(
        ref_id=load.ref_id,
        origin=load.origin,
        destination=load.destination,
        price=load.price,
        equipment_type=load.equipment_type,
        pickup_date=load.pickup_date,
        discovered_by_id=discovered_by_id
    )
    db.add(db_load)
    db.commit()
    db.refresh(db_load)
    return db_load
