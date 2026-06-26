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
    CrmCustomer
)
from models.inventory import (
    STOCK_STATUS_IN_TRANSIT, STOCK_STATUS_PENDING_INBOUND,
    STOCK_STATUS_STOCKED, STOCK_STATUS_ARCHIVED,
    STOCK_STATUS_COLOR_MAP, STOCK_STATUS_LABEL_MAP
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
    # Phase 5: InvInventory.product 关系已移除，只保留 customer 关系
    query = db.query(InvInventory).options(
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


def create_inventory_for_pi_item(
    db: Session,
    product_id: int,
    customer_id: int,
    pi_id: int,
    quantity: float,
    supplier_id: int = None
) -> InvInventory:
    """为 PI item 创建采购在途库存记录（黄）
    
    防重复：同一 pi_id + product_id 组合不重复创建（排除历史库存）
    """
    existing = db.query(InvInventory).filter(
        InvInventory.pi_id == pi_id,
        InvInventory.product_id == product_id,
        InvInventory.stock_type.in_([STOCK_STATUS_IN_TRANSIT, STOCK_STATUS_PENDING_INBOUND, STOCK_STATUS_STOCKED])
    ).first()

    if existing:
        return existing  # 已存在则返回

    inv = InvInventory(
        dept_id='S',
        product_id=product_id,
        customer_id=customer_id,
        pi_id=pi_id,
        supplier_id=supplier_id,
        quantity=quantity,
        total_quantity=0,
        shipped_quantity=0,
        pending_quantity=quantity,
        current_location='IN_TRANSIT',
        stock_type=STOCK_STATUS_IN_TRANSIT,      # 1: 黄
        stock_status_color=STOCK_STATUS_COLOR_MAP[STOCK_STATUS_IN_TRANSIT],
        purchase_date=datetime.now(),
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def transition_inventory_status(
    db: Session,
    inventory_id: int,
    target_status: int
) -> InvInventory:
    """库存状态流转
    
    允许的流转:
      1(黄) ↔ 2(蓝): 双向（采购在途 ↔ 待入库）
      2(蓝) → 3(绿): 入库操作
      3(绿) → 4(黑): 归档（不可逆）
    
    Raises:
        ValueError: 库存记录不存在或不允许的流转
    """
    VALID_TRANSITIONS = {
        STOCK_STATUS_IN_TRANSIT: [STOCK_STATUS_PENDING_INBOUND],     # 黄→蓝
        STOCK_STATUS_PENDING_INBOUND: [STOCK_STATUS_IN_TRANSIT, STOCK_STATUS_STOCKED],  # 蓝→黄 或 蓝→绿
        STOCK_STATUS_STOCKED: [STOCK_STATUS_ARCHIVED],              # 绿→黑
        STOCK_STATUS_ARCHIVED: [],                                   # 黑不可变
    }

    inv = db.query(InvInventory).filter(InvInventory.id == inventory_id).first()
    if not inv:
        raise ValueError(f"库存记录 {inventory_id} 不存在")

    if target_status not in VALID_TRANSITIONS.get(inv.stock_type, []):
        current_label = STOCK_STATUS_LABEL_MAP.get(inv.stock_type, str(inv.stock_type))
        target_label = STOCK_STATUS_LABEL_MAP.get(target_status, str(target_status))
        raise ValueError(f"不允许从 [{current_label}] 流转到 [{target_label}]")

    old_status = inv.stock_type
    inv.stock_type = target_status
    inv.stock_status_color = STOCK_STATUS_COLOR_MAP.get(target_status, 'yellow')

    # 已入库时更新位置
    if target_status == STOCK_STATUS_STOCKED:
        inv.current_location = 'WAREHOUSE'

    db.commit()
    db.refresh(inv)

    # 写流转日志
    log = InvInventoryLog(
        dept_id=inv.dept_id,
        product_id=inv.product_id,
        customer_id=inv.customer_id,
        pi_id=inv.pi_id,
        change_type=5,  # 状态流转
        change_quantity=0,
        before_quantity=float(old_status),
        after_quantity=float(target_status),
        ref_type='STATUS_TRANSITION',
        ref_id=inventory_id,
        remark=f"状态流转: {STOCK_STATUS_LABEL_MAP.get(old_status)} → {STOCK_STATUS_LABEL_MAP.get(target_status)}",
    )
    db.add(log)
    db.commit()

    return inv


def upsert_inventory_on_inbound(
    db: Session,
    *,
    dept_id: str,
    po_id: int,
    pi_id: int,
    product_id: int,
    customer_id: int,
    supplier_id: int = None,
    quantity: float,
    inspector: str = None,
    remark: str = None,
    purchase_price: float = None,
    customer_product_code: str = None,
) -> InvInventory:
    """
    入库时更新已有库存记录（2026-06-23 v2: 使用 4 状态生命周期）

    流程：
    1. 查找该 PI+产品 对应的在途/待入库记录（stock_type=1 或 2）
    2. 更新数量：total_quantity += qty, pending_quantity -= qty
    3. 状态流转：
       - 全部入库 (pending <= 0) → 绿(已入库, stock_type=3)
       - 部分入库 (pending > 0)  → 蓝(待入库, stock_type=2)
    4. 兼容旧数据：若无预创建记录，新建一条绿状态记录
    """
    import logging
    logger = logging.getLogger(__name__)

    qty = float(quantity or 0)
    if qty <= 0:
        logger.warning(f"[upsert_inv] skip: qty={qty} <= 0")
        return None

    # 优先查找 PI 创建的在途/待入库记录
    inv = db.query(InvInventory).filter(
        InvInventory.pi_id == pi_id,
        InvInventory.product_id == product_id,
        InvInventory.stock_type.in_([STOCK_STATUS_IN_TRANSIT, STOCK_STATUS_PENDING_INBOUND])
    ).first()

    # 回退：按 po_id+product_id 查找（兼容旧数据）
    if not inv:
        inv = db.query(InvInventory).filter(
            InvInventory.po_id == po_id,
            InvInventory.product_id == product_id,
        ).first()

    logger.info(
        f"[upsert_inv] query result: existing_inv="
        f"{'yes id=' + str(inv.id) + ' type=' + str(inv.stock_type) + ' qty=' + str(inv.total_quantity) if inv else 'no (will create)'}"
    )

    before_qty = float(inv.total_quantity or 0) if inv else 0.0

    if inv:
        # 更新数量
        inv.total_quantity = before_qty + qty
        old_pending = float(inv.pending_quantity or 0)
        inv.pending_quantity = max(0, old_pending - qty)

        # 补充后续才知道的字段
        if supplier_id and not inv.supplier_id:
            inv.supplier_id = supplier_id
        if customer_product_code and not inv.customer_product_code:
            inv.customer_product_code = customer_product_code
        if purchase_price is not None and not inv.purchase_price:
            inv.purchase_price = purchase_price
        if not inv.pi_id:
            inv.pi_id = pi_id

        # 状态流转
        after_qty = float(inv.total_quantity)
        if inv.pending_quantity <= 0:
            # 全部入库 → 绿(已入库)
            if inv.stock_type != STOCK_STATUS_STOCKED:
                try:
                    transition_inventory_status(db, inv.id, STOCK_STATUS_STOCKED)
                except ValueError as e:
                    logger.warning(f"[upsert_inv] 状态流转失败，手动设置: {e}")
                    inv.stock_type = STOCK_STATUS_STOCKED
                    inv.stock_status_color = STOCK_STATUS_COLOR_MAP[STOCK_STATUS_STOCKED]
                    inv.current_location = 'WAREHOUSE'
                    db.commit()
        else:
            # 部分入库 → 蓝(待入库)
            if inv.stock_type == STOCK_STATUS_IN_TRANSIT:
                try:
                    transition_inventory_status(db, inv.id, STOCK_STATUS_PENDING_INBOUND)
                except ValueError as e:
                    logger.warning(f"[upsert_inv] 状态流转失败，手动设置: {e}")
                    inv.stock_type = STOCK_STATUS_PENDING_INBOUND
                    inv.stock_status_color = STOCK_STATUS_COLOR_MAP[STOCK_STATUS_PENDING_INBOUND]
                    db.commit()
    else:
        # 兼容旧数据：无预创建记录则新建（直接为已入库状态）
        inv = InvInventory(
            dept_id=dept_id or "S",
            product_id=product_id,
            customer_id=customer_id or 0,
            pi_id=pi_id,
            po_id=po_id,
            supplier_id=supplier_id,
            total_quantity=qty,
            shipped_quantity=0,
            pending_quantity=0,
            purchase_price=purchase_price,
            customer_product_code=customer_product_code,
            stock_type=STOCK_STATUS_STOCKED,      # 3: 已入库(绿)
            stock_status_color=STOCK_STATUS_COLOR_MAP[STOCK_STATUS_STOCKED],
            current_location='WAREHOUSE',
            purchase_date=datetime.now(),
            remark=remark,
        )
        db.add(inv)
        after_qty = qty

    # 写库存流水日志
    log = InvInventoryLog(
        dept_id=dept_id or "S",
        product_id=product_id,
        customer_id=customer_id or 0,
        pi_id=pi_id,
        change_type=2,  # 2=入库
        change_quantity=qty,
        before_quantity=before_qty,
        after_quantity=after_qty,
        ref_type='PO_INBOUND',
        ref_id=po_id,
        remark=remark or f"入库验收 by {inspector or 'N/A'}",
    )
    db.add(log)

    db.commit()
    db.refresh(inv)
    logger.info(f"[upsert_inv] ✅ committed: inv_id={inv.id}, total_qty={inv.total_quantity}, stock_type={inv.stock_type}, color={inv.stock_status_color}, log_added")
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
    import logging
    logger = logging.getLogger(__name__)

    inbound_start = datetime.now()
    logger.info(f"\n{'═' * 80}")
    logger.info(f"[📦 入库批次创建流程开始] create_inbound_batch()")
    logger.info(f"{'═' * 80}")
    logger.info(f"  参数:")
    logger.info(f"    PO_ID: {batch_data.po_id}")
    logger.info(f"    Product_ID: {batch_data.product_id}")
    logger.info(f"    Batch_NO: {batch_data.batch_no}")
    logger.info(f"    Quantity: {batch_data.quantity}")
    logger.info(f"    Inspector: {batch_data.inspector}")
    logger.info(f"    Inbound_Date: {batch_data.inbound_date}")

    # 步骤1: 创建入库批次记录
    logger.info(f"\n[步骤1/3] 创建入库批次记录...")
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

    logger.info(f"[✅ 入库批次创建成功]")
    logger.info(f"  Batch ID: {db_batch.id}")
    logger.info(f"  Batch NO: {db_batch.batch_no}")
    logger.info(f"  Status: {db_batch.status} (1=待确认)")

    # 输出最终结果
    inbound_duration = (datetime.now() - inbound_start).total_seconds()
    logger.info(f"\n{'═' * 80}")
    logger.info(f"[✅ 入库批次创建完成]")
    logger.info(f"{'═' * 80}")
    logger.info(f"  Batch ID: {db_batch.id}")
    logger.info(f"  Batch NO: {db_batch.batch_no}")
    logger.info(f"  Product ID: {db_batch.product_id}")
    logger.info(f"  Quantity: {db_batch.quantity}")
    logger.info(f"  耗时: {inbound_duration:.3f}s")
    logger.info(f"  状态: 待确认 (需要调用 confirm_inbound 完成实际入库)")
    logger.info(f"{'═' * 80}\n")

    return db_batch

def get_inbound_batches(db: Session, po_id: int = None, skip: int = 0, limit: int = 100):
    query = db.query(PoInboundBatch)
    if po_id is not None:
        query = query.filter(PoInboundBatch.po_id == po_id)
    return query.order_by(PoInboundBatch.created_at.desc()).offset(skip).limit(limit).all()

def confirm_inbound(db: Session, batch_id: int, inspector: str = None) -> PoInboundBatch:
    """确认入库批次"""
    import logging
    logger = logging.getLogger(__name__)

    confirm_start = datetime.now()
    logger.info(f"\n{'═' * 80}")
    logger.info(f"[✅ 入库确认流程开始] confirm_inbound()")
    logger.info(f"{'═' * 80}")
    logger.info(f"  参数:")
    logger.info(f"    Batch ID: {batch_id}")
    logger.info(f"    Inspector: {inspector}")

    # 步骤1: 查询入库批次
    logger.info(f"\n[步骤1/3] 查询入库批次...")
    batch = db.query(PoInboundBatch).filter(PoInboundBatch.id == batch_id).first()
    if not batch:
        logger.error(f"[❌ 错误] 入库批次不存在: {batch_id}")
        return None

    logger.info(f"[✅ 批次查询成功]")
    logger.info(f"  Batch ID: {batch.id}")
    logger.info(f"  Batch NO: {batch.batch_no}")
    logger.info(f"  PO_ID: {batch.po_id}")
    logger.info(f"  Product_ID: {batch.product_id}")
    logger.info(f"  Quantity: {batch.quantity}")
    logger.info(f"  当前状态: {batch.status} (1=待确认)")

    # 步骤2: 更新状态并执行实际入库
    logger.info(f"\n[步骤2/3] 更新状态并执行实际入库操作...")
    batch.status = 2  # 已确认
    if inspector:
        batch.inspector = inspector

    logger.info(f"  状态更新: 1(待确认) → 2(已确认)")
    logger.info(f"  Inspector: {inspector or batch.inspector}")

    # 调用实际入库函数
    logger.info(f"  调用 inbound_inventory() 增加库存...")
    inbound_result = inbound_inventory(db, batch.po_id, batch.product_id, batch.quantity, inspector, batch.remark)
    if inbound_result:
        logger.info(f"  [✅ 库存更新成功]")
        logger.info(f"    库存ID: {inbound_result.id}")
        logger.info(f"    当前库存量: {inbound_result.quantity}")
    else:
        logger.warning(f"  [⚠️ 库存更新返回空结果]")

    db.commit()
    db.refresh(batch)

    # 输出最终结果
    confirm_duration = (datetime.now() - confirm_start).total_seconds()
    logger.info(f"\n[步骤3/3] 入库确认完成")
    logger.info(f"\n{'═' * 80}")
    logger.info(f"[✅ 入库确认流程完成]")
    logger.info(f"{'═' * 80}")
    logger.info(f"  Batch ID: {batch.id}")
    logger.info(f"  Batch NO: {batch.batch_no}")
    logger.info(f"  Product ID: {batch.product_id}")
    logger.info(f"  入库数量: {batch.quantity}")
    logger.info(f"  最终状态: {batch.status} (2=已确认)")
    logger.info(f"  Inspector: {batch.inspector}")
    logger.info(f"  耗时: {confirm_duration:.3f}s")
    logger.info(f"{'═' * 80}\n")

    return batch
