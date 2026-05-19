"""
产品-客户关联CRUD操作
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from models.product_customer import PrdProductCustomer
from schemas.product_customer import ProductCustomerCreate, ProductCustomerUpdate


def get_product_customers(db: Session, product_id: int) -> List[PrdProductCustomer]:
    """获取产品的所有客户关联"""
    return db.query(PrdProductCustomer).filter(
        PrdProductCustomer.product_id == product_id
    ).all()


def get_customer_products(db: Session, customer_id: int) -> List[PrdProductCustomer]:
    """获取客户的所有产品关联"""
    return db.query(PrdProductCustomer).filter(
        PrdProductCustomer.customer_id == customer_id,
        PrdProductCustomer.is_active == True
    ).all()


def get_product_customer(db: Session, product_id: int, customer_id: int) -> Optional[PrdProductCustomer]:
    """获取产品-客户的特定关联"""
    return db.query(PrdProductCustomer).filter(
        and_(
            PrdProductCustomer.product_id == product_id,
            PrdProductCustomer.customer_id == customer_id
        )
    ).first()


def get_all_product_customers(db: Session, skip: int = 0, limit: int = 100) -> List[PrdProductCustomer]:
    """获取所有产品-客户关联"""
    return db.query(PrdProductCustomer).offset(skip).limit(limit).all()


def get_product_customer_by_id(db: Session, pc_id: int) -> Optional[PrdProductCustomer]:
    """根据ID获取产品-客户关联"""
    return db.query(PrdProductCustomer).filter(PrdProductCustomer.id == pc_id).first()


def create_product_customer(db: Session, pc: ProductCustomerCreate) -> PrdProductCustomer:
    """创建产品-客户关联"""
    # 检查是否已存在
    existing = get_product_customer(db, pc.product_id, pc.customer_id)
    if existing:
        return existing
    
    db_pc = PrdProductCustomer(
        product_id=pc.product_id,
        customer_id=pc.customer_id,
        customer_product_code=pc.customer_product_code,
        customer_oe_number=pc.customer_oe_number,
        price_usd=pc.price_usd,
        price_rmb=pc.price_rmb,
        is_active=pc.is_active
    )
    db.add(db_pc)
    db.commit()
    db.refresh(db_pc)
    return db_pc


def update_product_customer(db: Session, pc_id: int, pc: ProductCustomerUpdate) -> Optional[PrdProductCustomer]:
    """更新产品-客户关联"""
    db_pc = get_product_customer_by_id(db, pc_id)
    if not db_pc:
        return None
    
    update_data = pc.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_pc, key, value)
    
    db.commit()
    db.refresh(db_pc)
    return db_pc


def delete_product_customer(db: Session, pc_id: int) -> bool:
    """删除产品-客户关联"""
    db_pc = get_product_customer_by_id(db, pc_id)
    if not db_pc:
        return False
    
    db.delete(db_pc)
    db.commit()
    return True