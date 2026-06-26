from sqlalchemy.orm import Session
from models import PrdProductSupplier, PrdProduct, SupSupplier, CrmCustomer
from schemas import ProductSupplierCreate, ProductSupplierUpdate
from app.cache import cache, CACHE_KEYS

def create_product_supplier(db: Session, product_supplier: ProductSupplierCreate) -> PrdProductSupplier:
    """创建产品供应商方案（支持同一产品对应同一供应商的多个方案）"""
    db_product_supplier = PrdProductSupplier(
        product_id=product_supplier.product_id,
        supplier_id=product_supplier.supplier_id,
        customer_id=product_supplier.customer_id,
        factory_code=product_supplier.factory_code,
        # 价格信息
        purchase_price=product_supplier.purchase_price,
        currency=product_supplier.currency,
        # 包装信息
        units_per_carton=product_supplier.units_per_carton,
        carton_length_cm=product_supplier.carton_length_cm,
        carton_width_cm=product_supplier.carton_width_cm,
        carton_height_cm=product_supplier.carton_height_cm,
        gross_weight_kg=product_supplier.gross_weight_kg,
        # 其他信息
        moq=product_supplier.moq,
        lead_time_days=product_supplier.lead_time_days,
        purchase_channel=product_supplier.purchase_channel,
        remark=product_supplier.remark,
        special_requirements=product_supplier.special_requirements,
        is_default=product_supplier.is_default
    )
    db.add(db_product_supplier)
    db.commit()
    db.refresh(db_product_supplier)
    
    # 清除相关缓存
    cache.clear_prefix(f"{CACHE_KEYS['PRODUCT_SUPPLIER']}:{product_supplier.product_id}")
    
    return db_product_supplier

def get_product_supplier(db: Session, product_supplier_id: int) -> PrdProductSupplier:
    return db.query(PrdProductSupplier).filter(PrdProductSupplier.id == product_supplier_id).first()

def get_product_suppliers_by_product(db: Session, product_id: int):
    return db.query(PrdProductSupplier).filter(PrdProductSupplier.product_id == product_id).all()

def get_product_suppliers_with_details(db: Session, product_id: int):
    """获取产品的供应商关联，包含供应商和客户详细信息"""
    # 尝试从缓存获取
    cache_key = f"{CACHE_KEYS['PRODUCT_SUPPLIER']}:{product_id}:details"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    result = db.query(
        PrdProductSupplier,
        SupSupplier.supplier_code,
        SupSupplier.supplier_name,
        CrmCustomer.customer_code,
        CrmCustomer.customer_name,
        CrmCustomer.special_require  # 添加客户特殊要求
    ).join(
        SupSupplier, PrdProductSupplier.supplier_id == SupSupplier.id
    ).outerjoin(
        CrmCustomer, PrdProductSupplier.customer_id == CrmCustomer.id
    ).filter(
        PrdProductSupplier.product_id == product_id
    ).all()
    
    result_list = [
        {
            "id": ps.id,
            "product_id": ps.product_id,
            "supplier_id": ps.supplier_id,
            "customer_id": ps.customer_id,
            "factory_code": ps.factory_code,
            "supplier_code": sc,
            "supplier_name": sn,
            "customer_code": cc,
            "customer_name": cn,
            "customer_special_require": csr,  # 客户特殊要求
            # 价格信息
            "purchase_price": float(ps.purchase_price) if ps.purchase_price else None,
            "currency": ps.currency,
            # 包装信息
            "units_per_carton": ps.units_per_carton,
            "carton_length_cm": float(ps.carton_length_cm) if ps.carton_length_cm else None,
            "carton_width_cm": float(ps.carton_width_cm) if ps.carton_width_cm else None,
            "carton_height_cm": float(ps.carton_height_cm) if ps.carton_height_cm else None,
            "gross_weight_kg": float(ps.gross_weight_kg) if ps.gross_weight_kg else None,
            # 其他信息
            "moq": ps.moq,
            "lead_time_days": ps.lead_time_days,
            "purchase_channel": ps.purchase_channel,
            "remark": ps.remark,
            "special_requirements": ps.special_requirements,
            "is_default": ps.is_default,
            "created_at": ps.created_at,
            "updated_at": ps.updated_at
        }
        for ps, sc, sn, cc, cn, csr in result
    ]
    
    # 缓存结果（30秒）
    cache.set(cache_key, result_list, ttl=30)
    
    return result_list

def update_product_supplier(db: Session, product_supplier_id: int, update_data: ProductSupplierUpdate) -> PrdProductSupplier:
    db_ps = get_product_supplier(db, product_supplier_id)
    if not db_ps:
        return None
    
    update_dict = update_data.dict(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_ps, key, value)
    
    db.commit()
    db.refresh(db_ps)
    
    # 清除相关缓存
    cache.clear_prefix(f"{CACHE_KEYS['PRODUCT_SUPPLIER']}:{db_ps.product_id}")
    
    return db_ps

def delete_product_supplier(db: Session, product_supplier_id: int) -> bool:
    db_ps = get_product_supplier(db, product_supplier_id)
    if not db_ps:
        return False
    
    db.delete(db_ps)
    db.commit()
    return True

def delete_product_suppliers_by_product(db: Session, product_id: int):
    """删除产品的所有供应商关联"""
    db.query(PrdProductSupplier).filter(PrdProductSupplier.product_id == product_id).delete()
    db.commit()
