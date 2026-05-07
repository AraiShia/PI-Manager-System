from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from crud.purchase import (
    create_purchase_order, get_purchase_order, get_purchase_orders, 
    update_purchase_status, create_1688_purchase, get_1688_purchases,
    update_purchase_order
)
from schemas.purchase import PurchaseOrderCreate, PurchaseOrderResponse, PurchaseOrderUpdate

router = APIRouter(prefix="/api/purchase-orders", tags=["采购管理"])

@router.post("/", response_model=PurchaseOrderResponse)
def create_purchase_order_api(purchase: PurchaseOrderCreate, db: Session = Depends(get_db)):
    try:
        return create_purchase_order(db, purchase)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[PurchaseOrderResponse])
def read_purchase_orders(skip: int = 0, limit: int = 100, status: int = None, pi_id: int = None, db: Session = Depends(get_db)):
    return get_purchase_orders(db, skip=skip, limit=limit, status=status, pi_id=pi_id)

@router.get("/{po_id}", response_model=PurchaseOrderResponse)
def read_purchase_order(po_id: int, db: Session = Depends(get_db)):
    db_po = get_purchase_order(db, po_id)
    if db_po is None:
        raise HTTPException(status_code=404, detail="采购单不存在")
    return db_po

@router.put("/{po_id}", response_model=PurchaseOrderResponse)
def update_purchase_order_api(po_id: int, purchase_update: PurchaseOrderUpdate, db: Session = Depends(get_db)):
    try:
        db_po = update_purchase_order(db, po_id, purchase_update)
        if db_po is None:
            raise HTTPException(status_code=404, detail="采购单不存在")
        return db_po
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{po_id}/confirm")
def confirm_purchase(po_id: int, db: Session = Depends(get_db)):
    db_po = update_purchase_status(db, po_id, 2)
    if db_po is None:
        raise HTTPException(status_code=404, detail="采购单不存在")
    return {"message": "采购已确认", "purchase_order": db_po}

@router.post("/{po_id}/inbound")
def inbound_purchase(po_id: int, db: Session = Depends(get_db)):
    db_po = update_purchase_status(db, po_id, 3)
    if db_po is None:
        raise HTTPException(status_code=404, detail="采购单不存在")
    return {"message": "已入库", "purchase_order": db_po}

@router.post("/1688")
def create_1688_purchase_api(purchase_data, db: Session = Depends(get_db)):
    return create_1688_purchase(db, purchase_data)

@router.get("/1688")
def read_1688_purchases(pi_id: int = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_1688_purchases(db, pi_id=pi_id, skip=skip, limit=limit)
