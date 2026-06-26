from sqlalchemy.orm import Session
from backend.models.pending_shipment import ShPendingShipmentItem
from backend.models.pi import PiProformaInvoiceItem


def add_to_pending_queue(db: Session, pi_item_ids: list[int], user_id: str) -> list[ShPendingShipmentItem]:
    """将PI产品明细添加到待出货队列"""
    items = []
    for pi_item_id in pi_item_ids:
        # 检查是否已在队列中
        existing = db.query(ShPendingShipmentItem).filter(
            ShPendingShipmentItem.pi_item_id == pi_item_id,
            ShPendingShipmentItem.status == 1
        ).first()
        if existing:
            continue
        
        pi_item = db.query(PiProformaInvoiceItem).filter_by(id=pi_item_id).first()
        if not pi_item:
            continue
            
        item = ShPendingShipmentItem(
            pi_id=pi_item.pi_id,
            pi_item_id=pi_item_id,
            product_id=pi_item.product_id,
            customer_id=pi_item.customer_id,
            created_by=user_id,
            status=1
        )
        db.add(item)
        items.append(item)
    
    db.commit()
    for item in items:
        db.refresh(item)
    return items


def get_pending_items(db: Session, status: int = None) -> list[dict]:
    """获取待出货队列产品列表"""
    query = db.query(ShPendingShipmentItem)
    if status:
        query = query.filter(ShPendingShipmentItem.status == status)
    items = query.all()
    return [_item_to_dict(item) for item in items]


def remove_from_pending(db: Session, item_id: int) -> bool:
    """从待出货队列移除"""
    item = db.query(ShPendingShipmentItem).filter_by(id=item_id).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


def confirm_pending_items(db: Session, item_ids: list[int]) -> int:
    """确认待出货项（标记为已确认）"""
    count = 0
    for item_id in item_ids:
        item = db.query(ShPendingShipmentItem).filter_by(id=item_id).first()
        if item and item.status == 1:
            item.status = 2
            count += 1
    db.commit()
    return count


def _item_to_dict(item: ShPendingShipmentItem) -> dict:
    """转换队列项为字典"""
    return {
        'id': item.id,
        'pi_id': item.pi_id,
        'pi_item_id': item.pi_item_id,
        'product_id': item.product_id,
        'customer_id': item.customer_id,
        'status': item.status,
        'created_at': item.created_at.isoformat() if item.created_at else None,
    }
