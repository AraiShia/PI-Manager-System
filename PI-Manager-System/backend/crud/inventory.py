# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime, timedelta
from models import (
    InvInventory,
    InvInventoryLog,
    PoPurchaseOrder,
    PoPurchaseOrderItem,
    PoInboundBatch,
    PrdProduct,
    CrmCustomer
)
from schemas import InventoryCreate, InventoryTransfer

def create_inventory(db: Session, inventory: InventoryCreate, stock_type: int = 1, dept_id: str = 'S') -> InvInventory:
    # 颜色映射：1=采购在途(黄), 2=待入库(蓝), 3=已入库(绿), 4=历史库存(黑)
    color = getattr(inventory, 'stock_status_color', None)
    if not color:
        color = 'yellow' if stock_type == 1 else ('blue' if stock_type == 2 else ('green' if stock_type == 3 else 'black'))

    db_inventory = InvInventory(
        dept_id=dept_id,
        product_id=inventory.product_id,
        customer_id=inventory.customer_id,
        pi_id=inventory.pi_id,
        po_id=inventory.po_id,
        supplier_id=inventory.supplier_id,
        total_quantity=inventory.quantity,
        pending_quantity=inventory.quantity,
        purchase_price=inventory.purchase_price,
        current_location=inventory.current_location or 'WAREHOUSE',
        customer_product_code=getattr(inventory, 'customer_product_code', None),
        inventory_customer_price=getattr(inventory, 'inventory_customer_price', None),
        color=getattr(inventory, 'color', None),
        stock_type=stock_type,
        stock_status_color=color,
        remark=getattr(inventory, 'remark', None)
    )

    db.add(db_inventory)
    db.commit()
    db.refresh(db_inventory)

    log = InvInventoryLog(
        dept_id=dept_id,
        product_id=inventory.product_id,
        customer_id=inventory.customer_id,
        pi_id=inventory.pi_id,
        change_type=1,
        change_quantity=inventory.quantity,
        before_quantity=0,
        after_quantity=inventory.quantity,
        ref_type='PO',
        ref_id=inventory.po_id,
        remark=getattr(inventory, 'remark', None)
    )
    db.add(log)
    db.commit()

    return db_inventory

def get_inventory(db: Session, inventory_id: int) -> InvInventory:
    return db.query(InvInventory).filter(InvInventory.id == inventory_id).first()

def get_inventories(db: Session, skip: int = 0, limit: int = 100, product_id: int = None, customer_id: int = None, stock_type: int = None):
    query = db.query(InvInventory).options(
        joinedload(InvInventory.product),
        joinedload(InvInventory.customer)
    )
    if product_id is not None:
        query = query.filter(InvInventory.product_id == product_id)
    if customer_id is not None:
        query = query.filter(InvInventory.customer_id == customer_id)
    if stock_type is not None:
        query = query.filter(InvInventory.stock_type == stock_type)
    return query.offset(skip).limit(limit).all()

def get_inventory_by_purchase(db: Session, po_id: int):
    return db.query(InvInventory).filter(InvInventory.po_id == po_id).all()

def update_inventory(db: Session, inventory_id: int, inventory_data: dict) -> InvInventory:
    """更新库存记录"""
    db_inventory = db.query(InvInventory).filter(InvInventory.id == inventory_id).first()
    if not db_inventory:
        return None
    
    if 'product_id' in inventory_data:
        db_inventory.product_id = inventory_data['product_id']
    if 'customer_id' in inventory_data:
        db_inventory.customer_id = inventory_data['customer_id']
    if 'supplier_id' in inventory_data:
        db_inventory.supplier_id = inventory_data['supplier_id']
    if 'pi_id' in inventory_data:
        db_inventory.pi_id = inventory_data['pi_id']
    if 'po_id' in inventory_data:
        db_inventory.po_id = inventory_data['po_id']
    if 'quantity' in inventory_data:
        new_qty = inventory_data['quantity']
        db_inventory.total_quantity = new_qty
        # pending_quantity = 总量 - 已发货量
        shipped = db_inventory.shipped_quantity or 0
        db_inventory.pending_quantity = new_qty - shipped
    if 'current_location' in inventory_data:
        db_inventory.current_location = inventory_data['current_location']
    if 'purchase_price' in inventory_data:
        db_inventory.purchase_price = inventory_data['purchase_price']
    if 'customer_product_code' in inventory_data:
        db_inventory.customer_product_code = inventory_data['customer_product_code']
    if 'inventory_customer_price' in inventory_data:
        db_inventory.inventory_customer_price = inventory_data['inventory_customer_price']
    if 'color' in inventory_data:
        db_inventory.color = inventory_data['color']
    if 'stock_type' in inventory_data:
        db_inventory.stock_type = inventory_data['stock_type']
        stock_type = inventory_data['stock_type']
        db_inventory.stock_status_color = 'yellow' if stock_type == 1 else ('blue' if stock_type == 2 else ('green' if stock_type == 3 else 'black'))
    if 'stock_status_color' in inventory_data:
        db_inventory.stock_status_color = inventory_data['stock_status_color']
    if 'remark' in inventory_data:
        db_inventory.remark = inventory_data['remark']
    
    db.commit()
    db.refresh(db_inventory)
    return db_inventory

def delete_inventory(db: Session, inventory_id: int) -> bool:
    """删除库存记录"""
    db_inventory = db.query(InvInventory).filter(InvInventory.id == inventory_id).first()
    if not db_inventory:
        return False
    # 同时删除关联日志
    db.query(InvInventoryLog).filter(InvInventoryLog.ref_id == inventory_id).delete()
    db.delete(db_inventory)
    db.commit()
    return True

def transfer_inventory(db: Session, transfer: InventoryTransfer) -> bool:
    source_inv = db.query(InvInventory).filter(InvInventory.id == transfer.source_id).first()
    if not source_inv:
        return False

    if source_inv.pending_quantity < transfer.quantity:
        return False

    target_inv = db.query(InvInventory).filter(InvInventory.id == transfer.target_id).first()
    if not target_inv:
        return False

    before_quantity = target_inv.pending_quantity
    target_inv.pending_quantity += transfer.quantity
    target_inv.total_quantity += transfer.quantity
    source_inv.pending_quantity -= transfer.quantity

    log = InvInventoryLog(
        dept_id=source_inv.dept_id,
        product_id=source_inv.product_id,
        customer_id=source_inv.customer_id,
        pi_id=source_inv.pi_id,
        change_type=3,
        change_quantity=transfer.quantity,
        before_quantity=before_quantity,
        after_quantity=target_inv.pending_quantity,
        ref_type='TRANSFER',
        ref_id=transfer.source_id,
        remark=f'从库存{source_inv.id}调拨至{target_inv.id}'
    )
    db.add(log)
    db.commit()
    return True

def inbound_inventory(db: Session, po_id: int, product_id: int, quantity: float, inspector: str = None, remark: str = None) -> InvInventory:
    """入库操作"""
    inv = db.query(InvInventory).filter(
        InvInventory.po_id == po_id,
        InvInventory.product_id == product_id,
        InvInventory.stock_type == 1
    ).first()

    if not inv:
        return None

    before_qty = inv.pending_quantity
    inv.stock_type = 3  # 3=已入库(绿)
    inv.stock_status_color = 'green'
    inv.pending_quantity = 0

    log = InvInventoryLog(
        dept_id=inv.dept_id,
        product_id=product_id,
        customer_id=inv.customer_id,
        pi_id=inv.pi_id,
        change_type=2,
        change_quantity=quantity,
        before_quantity=before_qty,
        after_quantity=inv.total_quantity,
        ref_type='PO',
        ref_id=po_id,
        remark=remark or f'入库验收，由{inspector}确认'
    )
    db.add(log)

    po_item = db.query(PoPurchaseOrderItem).filter(
        PoPurchaseOrderItem.po_id == po_id,
        PoPurchaseOrderItem.product_id == product_id
    ).first()
    if po_item:
        po_item.inbound_status = 2

    db.commit()
    db.refresh(inv)
    return inv

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
        'total_quantity': float(total_quantity),
        'total_value': float(total_value)
    }

def get_product_recent_logs(db: Session, limit: int = 100):
    """获取所有产品的最近变更记录，按产品分组"""
    from crud.supplier import get_supplier
    from crud.customer import get_customer
    
    logs = db.query(InvInventoryLog).order_by(InvInventoryLog.created_at.desc()).limit(limit * 5).all()
    print(f"DEBUG - 后端获取到 {len(logs)} 条日志记录")
    
    # 按 product_id 分组，只取每个产品最新的记录
    product_latest = {}
    for log in logs:
        if log.product_id not in product_latest:
            product_latest[log.product_id] = log
    
    print(f"DEBUG - 按产品分组后 {len(product_latest)} 个产品")
    
    # 构建返回数据
    result = {}
    for product_id, log in product_latest.items():
        print(f"DEBUG - 处理产品{product_id}, ref_type={log.ref_type}, ref_id={log.ref_id}, customer_id={log.customer_id}")
        
        # 获取供应商名称 - 优先从关联的库存记录获取
        supplier_name = None
        
        # 方案1：从日志的ref_id获取
        if log.ref_type == 'PO' and log.ref_id:
            inv = db.query(InvInventory).filter(
                InvInventory.product_id == product_id,
                InvInventory.po_id == log.ref_id
            ).first()
            if inv and inv.supplier_id:
                supplier = get_supplier(db, inv.supplier_id)
                if supplier:
                    supplier_name = supplier.supplier_name
        
        # 方案2：如果方案1没找到，从该产品最新的库存记录获取
        if not supplier_name:
            inv = db.query(InvInventory).filter(
                InvInventory.product_id == product_id
            ).order_by(InvInventory.created_at.desc()).first()
            if inv and inv.supplier_id:
                supplier = get_supplier(db, inv.supplier_id)
                if supplier:
                    supplier_name = supplier.supplier_name
        
        if supplier_name:
            print(f"DEBUG - 找到供应商: {supplier_name}")
        
        # 获取客户名称
        customer_name = None
        if log.customer_id:
            customer = get_customer(db, log.customer_id)
            if customer:
                customer_name = customer.customer_name
        
        result[product_id] = {
            'last_change_time': log.created_at.isoformat() if log.created_at else None,
            'change_type': log.change_type,
            'change_quantity': float(log.change_quantity) if log.change_quantity else 0,
            'before_quantity': float(log.before_quantity) if log.before_quantity else 0,
            'after_quantity': float(log.after_quantity) if log.after_quantity else 0,
            'supplier_name': supplier_name,
            'customer_name': customer_name,
            'remark': log.remark,
        }
    
    return result

# 入库批次CRUD
def create_inbound_batch(db: Session, batch_data) -> PoInboundBatch:
    db_batch = PoInboundBatch(
        dept_id=batch_data.dept_id,
        po_id=batch_data.po_id,
        product_id=batch_data.product_id,
        batch_no=batch_data.batch_no,
        inbound_date=batch_data.inbound_date,
        quantity=batch_data.quantity,
        inspector=batch_data.inspector,
        remark=batch_data.remark,
        status=1
    )
    db.add(db_batch)
    db.commit()
    db.refresh(db_batch)
    return db_batch

def get_inbound_batches(db: Session, po_id: int = None, skip: int = 0, limit: int = 100):
    query = db.query(PoInboundBatch)
    if po_id is not None:
        query = query.filter(PoInboundBatch.po_id == po_id)
    return query.order_by(PoInboundBatch.created_at.desc()).offset(skip).limit(limit).all()

def confirm_inbound(db: Session, batch_id: int, inspector: str = None) -> PoInboundBatch:
    """确认入库批次"""
    batch = db.query(PoInboundBatch).filter(PoInboundBatch.id == batch_id).first()
    if not batch:
        return None

    batch.status = 2
    if inspector:
        batch.inspector = inspector

    inbound_inventory(db, batch.po_id, batch.product_id, batch.quantity, inspector, batch.remark)
    db.commit()
    db.refresh(batch)
    return batch
