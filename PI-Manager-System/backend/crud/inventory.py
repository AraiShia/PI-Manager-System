from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from models import (
    InvInventory,
    InvInventoryLog,
    PoPurchaseOrder,
    PoPurchaseOrderItem,
    PrdProduct,
    CrmCustomer
)
from schemas import InventoryCreate, InventoryTransfer

def create_inventory(db: Session, inventory: InventoryCreate) -> InvInventory:
    db_inventory = InvInventory(
        product_id=inventory.product_id,
        customer_id=inventory.customer_id,
        pi_id=inventory.pi_id,
        purchase_order_id=inventory.purchase_order_id,
        supplier_id=inventory.supplier_id,
        quantity=inventory.quantity,
        pending_quantity=inventory.quantity,
        purchase_price=inventory.purchase_price,
        current_location='WAREHOUSE'
    )
    
    db.add(db_inventory)
    db.commit()
    db.refresh(db_inventory)
    
    log = InvInventoryLog(
        product_id=inventory.product_id,
        customer_id=inventory.customer_id,
        pi_id=inventory.pi_id,
        change_type='INV_IN',
        change_quantity=inventory.quantity,
        ref_type='PO',
        ref_id=inventory.purchase_order_id
    )
    db.add(log)
    db.commit()
    
    return db_inventory

def get_inventory(db: Session, inventory_id: int) -> InvInventory:
    return db.query(InvInventory).filter(InvInventory.id == inventory_id).first()

def get_inventories(db: Session, skip: int = 0, limit: int = 100, product_id: int = None, customer_id: int = None):
    query = db.query(InvInventory)
    if product_id is not None:
        query = query.filter(InvInventory.product_id == product_id)
    if customer_id is not None:
        query = query.filter(InvInventory.customer_id == customer_id)
    return query.offset(skip).limit(limit).all()

def get_inventory_by_purchase(db: Session, purchase_order_id: int):
    return db.query(InvInventory).filter(InvInventory.purchase_order_id == purchase_order_id).all()

def transfer_inventory(db: Session, transfer: InventoryTransfer) -> bool:
    source_inv = db.query(InvInventory).filter(InvInventory.id == transfer.source_id).first()
    if not source_inv:
        return False
    
    if source_inv.pending_quantity < transfer.quantity:
        return False
    
    target_inv = db.query(InvInventory).filter(InvInventory.id == transfer.target_id).first()
    if not target_inv:
        return False
    
    source_inv.pending_quantity -= transfer.quantity
    target_inv.pending_quantity += transfer.quantity
    
    db.commit()
    
    return True

def get_inventory_logs(db: Session, product_id: int = None, customer_id: int = None, skip: int = 0, limit: int = 100):
    query = db.query(InvInventoryLog)
    if product_id is not None:
        query = query.filter(InvInventoryLog.product_id == product_id)
    if customer_id is not None:
        query = query.filter(InvInventoryLog.customer_id == customer_id)
    return query.order_by(InvInventoryLog.created_at.desc()).offset(skip).limit(limit).all()

def get_inventory_aging(db: Session, days_threshold: int = 60):
    threshold_date = datetime.now() - timedelta(days=days_threshold)
    return db.query(InvInventory).filter(
        InvInventory.created_at < threshold_date,
        InvInventory.pending_quantity > 0
    ).all()

def get_inventory_summary(db: Session):
    total_quantity = db.query(func.sum(InvInventory.pending_quantity)).scalar() or 0
    total_value = db.query(func.sum(InvInventory.pending_quantity * InvInventory.purchase_price)).scalar() or 0
    
    return {
        'total_quantity': total_quantity,
        'total_value': total_value
    }
