from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from crud.shipment import (
    create_shipment, confirm_shipment, get_shipment, get_shipments, get_available_inventory
)
from schemas.shipment import ShipmentCreate, ShipmentResponse

router = APIRouter(prefix="/api/shipments", tags=["出货管理"])

@router.post("/", response_model=ShipmentResponse)
def create_shipment_api(shipment: ShipmentCreate, db: Session = Depends(get_db)):
    try:
        return create_shipment(db, shipment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[ShipmentResponse])
def read_shipments(skip: int = 0, limit: int = 100, pi_id: int = None, status: int = None, db: Session = Depends(get_db)):
    return get_shipments(db, skip=skip, limit=limit, pi_id=pi_id, status=status)

@router.get("/{shipment_id}", response_model=ShipmentResponse)
def read_shipment(shipment_id: int, db: Session = Depends(get_db)):
    db_shipment = get_shipment(db, shipment_id)
    if db_shipment is None:
        raise HTTPException(status_code=404, detail="出货单不存在")
    return db_shipment

@router.post("/{shipment_id}/confirm")
def confirm_shipment_api(shipment_id: int, db: Session = Depends(get_db)):
    try:
        return confirm_shipment(db, shipment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/inventory")
def read_available_inventory(pi_id: int, db: Session = Depends(get_db)):
    return get_available_inventory(db, pi_id)
