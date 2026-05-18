# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from crud.inventory import (
    create_inventory, get_inventory, get_inventories, update_inventory, delete_inventory,
    transfer_inventory, get_inventory_logs, get_inventory_aging, get_inventory_summary,
    inbound_inventory, create_inbound_batch, get_inbound_batches, confirm_inbound,
    get_product_recent_logs
)
from crud.supplier import get_supplier
from schemas.inventory import InventoryCreate, InventoryTransfer, InventoryResponse
from schemas.purchase import PoInboundBatchCreate, PoInboundBatchResponse

router = APIRouter(prefix="/api/inventory", tags=["库存管理"])

# ==================== 创建和列表 ====================

@router.post("/", response_model=InventoryResponse)
def create_inventory_api(inventory: InventoryCreate, db: Session = Depends(get_db)):
    dept_id = getattr(inventory, 'dept_id', 'S')
    stock_type = getattr(inventory, 'stock_type', 1)
    return create_inventory(db, inventory, stock_type=stock_type, dept_id=dept_id)

@router.get("/")
def read_inventories(skip: int = 0, limit: int = 100, product_id: int = None, customer_id: int = None, stock_type: int = None, db: Session = Depends(get_db)):
    inventories = get_inventories(db, skip=skip, limit=limit, product_id=product_id, customer_id=customer_id, stock_type=stock_type)
    result = []
    for inv in inventories:
        supplier_name = None
        if inv.supplier_id:
            supplier = get_supplier(db, inv.supplier_id)
            if supplier:
                supplier_name = supplier.supplier_name
        
        inv_dict = {
            "id": inv.id,
            "product_id": inv.product_id,
            "product_code": inv.product.product_code if inv.product else None,
            "oe_number": inv.product.oe_number if inv.product else None,
            "customer_id": inv.customer_id,
            "customer_name": inv.customer.customer_name if inv.customer else None,
            "supplier_id": inv.supplier_id,
            "supplier_name": supplier_name,
            "pi_id": inv.pi_id,
            "po_id": inv.po_id,
            "total_quantity": float(inv.total_quantity) if inv.total_quantity else 0,
            "shipped_quantity": float(inv.shipped_quantity) if inv.shipped_quantity else 0,
            "pending_quantity": float(inv.pending_quantity) if inv.pending_quantity else 0,
            "purchase_price": float(inv.purchase_price) if inv.purchase_price else None,
            "current_location": inv.current_location,
            "customer_product_code": inv.customer_product_code,
            "inventory_customer_price": float(inv.inventory_customer_price) if inv.inventory_customer_price else None,
            "color": inv.color,
            "stock_status_color": inv.stock_status_color,
            "stock_type": inv.stock_type,
            "remark": inv.remark,
            "created_at": inv.created_at.isoformat() if inv.created_at else None
        }
        result.append(inv_dict)
    return result

# ==================== 固定路径路由（必须在 /{inventory_id} 之前） ====================

@router.post("/transfer")
def transfer_inventory_api(transfer: InventoryTransfer, db: Session = Depends(get_db)):
    success = transfer_inventory(db, transfer)
    if not success:
        raise HTTPException(status_code=400, detail="调拨失败")
    return {"message": "调拨成功"}

@router.post("/inbound")
def inbound_inventory_api(po_id: int, product_id: int, quantity: float, inspector: str = None, remark: str = None, db: Session = Depends(get_db)):
    inv = inbound_inventory(db, po_id, product_id, quantity, inspector, remark)
    if not inv:
        raise HTTPException(status_code=404, detail="未找到待入库库存记录")
    return {"message": "入库成功", "inventory": inv}

@router.post("/inbound-batch", response_model=PoInboundBatchResponse)
def create_inbound_batch_api(batch: PoInboundBatchCreate, db: Session = Depends(get_db)):
    return create_inbound_batch(db, batch)

@router.get("/inbound-batch")
def read_inbound_batches(po_id: int = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_inbound_batches(db, po_id=po_id, skip=skip, limit=limit)

@router.post("/inbound-batch/{batch_id}/confirm")
def confirm_inbound_batch_api(batch_id: int, inspector: str = None, db: Session = Depends(get_db)):
    batch = confirm_inbound(db, batch_id, inspector)
    if not batch:
        raise HTTPException(status_code=404, detail="入库批次不存在")
    return {"message": "入库确认成功", "batch": batch}

@router.get("/logs")
def read_inventory_logs(product_id: int = None, customer_id: int = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_inventory_logs(db, product_id=product_id, customer_id=customer_id, skip=skip, limit=limit)

@router.get("/aging")
def read_inventory_aging(days_threshold: int = 60, db: Session = Depends(get_db)):
    return get_inventory_aging(db, days_threshold)

@router.get("/dashboard")
def get_inventory_dashboard(db: Session = Depends(get_db)):
    return get_inventory_summary(db)

@router.get("/product-logs")
def get_logs_by_product(db: Session = Depends(get_db)):
    """获取按产品分组的最近变更记录"""
    return get_product_recent_logs(db)

# ==================== 动态路径路由（必须放在最后） ====================

@router.get("/{inventory_id}", response_model=InventoryResponse)
def read_inventory(inventory_id: int, db: Session = Depends(get_db)):
    db_inventory = get_inventory(db, inventory_id)
    if db_inventory is None:
        raise HTTPException(status_code=404, detail="库存不存在")
    return db_inventory

@router.put("/{inventory_id}")
def update_inventory_api(inventory_id: int, inventory: InventoryCreate, db: Session = Depends(get_db)):
    """更新库存记录"""
    db_inventory = get_inventory(db, inventory_id)
    if db_inventory is None:
        raise HTTPException(status_code=404, detail="库存不存在")
    inventory_dict = inventory.model_dump()
    result = update_inventory(db, inventory_id, inventory_dict)
    if result is None:
        raise HTTPException(status_code=500, detail="更新失败")
    return {"message": "更新成功", "inventory": result}

@router.delete("/{inventory_id}")
def delete_inventory_api(inventory_id: int, db: Session = Depends(get_db)):
    """删除库存记录"""
    success = delete_inventory(db, inventory_id)
    if not success:
        raise HTTPException(status_code=404, detail="库存不存在")
    return {"message": "删除成功"}
