from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from crud.inventory import (
    create_inventory, get_inventory, get_inventories, transfer_inventory,
    get_inventory_logs, get_inventory_aging, get_inventory_summary
)
from schemas.inventory import InventoryCreate, InventoryTransfer, InventoryResponse

router = APIRouter(prefix="/api/inventory", tags=["库存管理"])

@router.post("/", response_model=InventoryResponse)
def create_inventory_api(inventory: InventoryCreate, db: Session = Depends(get_db)):
    return create_inventory(db, inventory)

@router.get("/", response_model=list[InventoryResponse])
def read_inventories(skip: int = 0, limit: int = 100, product_id: int = None, customer_id: int = None, db: Session = Depends(get_db)):
    return get_inventories(db, skip=skip, limit=limit, product_id=product_id, customer_id=customer_id)

@router.get("/{inventory_id}", response_model=InventoryResponse)
def read_inventory(inventory_id: int, db: Session = Depends(get_db)):
    db_inventory = get_inventory(db, inventory_id)
    if db_inventory is None:
        raise HTTPException(status_code=404, detail="库存不存在")
    return db_inventory

@router.post("/transfer")
def transfer_inventory_api(transfer: InventoryTransfer, db: Session = Depends(get_db)):
    success = transfer_inventory(db, transfer)
    if not success:
        raise HTTPException(status_code=400, detail="调拨失败")
    return {"message": "调拨成功"}

@router.get("/logs")
def read_inventory_logs(product_id: int = None, customer_id: int = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_inventory_logs(db, product_id=product_id, customer_id=customer_id, skip=skip, limit=limit)

@router.get("/aging")
def read_inventory_aging(days_threshold: int = 60, db: Session = Depends(get_db)):
    return get_inventory_aging(db, days_threshold)

@router.get("/dashboard")
def get_inventory_dashboard(db: Session = Depends(get_db)):
    return get_inventory_summary(db)
