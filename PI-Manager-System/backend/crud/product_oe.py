"""
产品OE关联CRUD操作
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from models.product_oe import PrdProductOE
from schemas.product_oe import ProductOECreate, ProductOEUpdate


def get_product_oes(db: Session, product_id: int) -> List[PrdProductOE]:
    """获取产品的所有OE号"""
    return db.query(PrdProductOE).filter(
        PrdProductOE.product_id == product_id
    ).order_by(PrdProductOE.is_primary.desc(), PrdProductOE.id).all()


def get_primary_oe(db: Session, product_id: int) -> Optional[PrdProductOE]:
    """获取产品的主OE号"""
    return db.query(PrdProductOE).filter(
        PrdProductOE.product_id == product_id,
        PrdProductOE.is_primary == True
    ).first()


def get_all_product_oes(db: Session, skip: int = 0, limit: int = 100) -> List[PrdProductOE]:
    """获取所有产品OE关联"""
    return db.query(PrdProductOE).offset(skip).limit(limit).all()


def get_product_oe(db: Session, oe_id: int) -> Optional[PrdProductOE]:
    """获取单个产品OE"""
    return db.query(PrdProductOE).filter(PrdProductOE.id == oe_id).first()


def create_product_oe(db: Session, oe: ProductOECreate) -> PrdProductOE:
    """创建产品OE关联"""
    db_oe = PrdProductOE(
        product_id=oe.product_id,
        oe_number=oe.oe_number,
        is_primary=oe.is_primary
    )
    db.add(db_oe)
    db.commit()
    db.refresh(db_oe)
    return db_oe


def update_product_oe(db: Session, oe_id: int, oe: ProductOEUpdate) -> Optional[PrdProductOE]:
    """更新产品OE"""
    db_oe = get_product_oe(db, oe_id)
    if not db_oe:
        return None
    
    update_data = oe.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_oe, key, value)
    
    db.commit()
    db.refresh(db_oe)
    return db_oe


def delete_product_oe(db: Session, oe_id: int) -> bool:
    """删除产品OE"""
    db_oe = get_product_oe(db, oe_id)
    if not db_oe:
        return False
    
    db.delete(db_oe)
    db.commit()
    return True


def set_primary_oe(db: Session, product_id: int, oe_id: int) -> bool:
    """设置主OE号"""
    # 先取消所有主OE
    db.query(PrdProductOE).filter(
        PrdProductOE.product_id == product_id,
        PrdProductOE.is_primary == True
    ).update({'is_primary': False})
    
    # 设置新的主OE
    db_oe = get_product_oe(db, oe_id)
    if db_oe and db_oe.product_id == product_id:
        db_oe.is_primary = True
        db.commit()
        return True
    return False