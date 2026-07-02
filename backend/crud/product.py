from sqlalchemy.orm import Session
from sqlalchemy import select
from models import PrdProduct, PrdProductImage, PiProformaInvoiceItem, PrdProductSupplier, PrdProductAuditLog
from schemas import ProductCreate, ProductUpdate, SupplierSchemeCreate
from utils.number_generator import NumberGenerator
from utils.volume_calculator import VolumeCalculator
import json
import time
import logging

logger = logging.getLogger(__name__)

def create_product(db: Session, product: ProductCreate) -> PrdProduct:
    product_code = NumberGenerator.generate_product_code(db, product.dept_id, product.category_id or 1)

    carton_volume_m3 = None
    if product.carton_length_cm and product.carton_width_cm and product.carton_height_cm:
        carton_volume_m3 = VolumeCalculator.calculate_carton_volume(
            product.carton_length_cm,
            product.carton_width_cm,
            product.carton_height_cm
        )

    product_data = product.dict(exclude={"supplier_schemes"})
    db_product = PrdProduct(
        product_code=product_code,
        **product_data
    )
    db_product.carton_volume_m3 = carton_volume_m3

    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    if product.supplier_schemes:
        for scheme in product.supplier_schemes:
            db_scheme = PrdProductSupplier(
                product_id=db_product.id,
                supplier_id=scheme.supplier_id,
                customer_id=scheme.customer_id if scheme.customer_id else None,
                factory_code=scheme.factory_code or str(db_product.oe_number),
                units_per_carton=scheme.units_per_carton,
                carton_length_cm=scheme.carton_length_cm,
                carton_width_cm=scheme.carton_width_cm,
                carton_height_cm=scheme.carton_height_cm,
                gross_weight_kg=scheme.gross_weight_kg,
                is_default=scheme.is_default,
                remark=scheme.remark
            )
            db.add(db_scheme)
        db.commit()
        db.refresh(db_product)

    return db_product

def get_product(db: Session, product_id: int) -> PrdProduct:
    return db.query(PrdProduct).filter(PrdProduct.id == product_id).first()

def get_product_by_code(db: Session, product_code: str) -> PrdProduct:
    return db.query(PrdProduct).filter(PrdProduct.product_code == product_code).first()

def get_products(db: Session, skip: int = 0, limit: int = 100, status: int = None):
    query = db.query(PrdProduct)
    if status is not None:
        query = query.filter(PrdProduct.status == status)
    return query.offset(skip).limit(limit).all()

def search_products(db: Session, keyword: str = "", category_id: int = None, category_code: str = None, status: int = None, customer_id: int = None):
    query = db.query(PrdProduct)

    if keyword:
        keyword = f"%{keyword}%"
        query = query.filter(
            PrdProduct.oe_number.ilike(keyword) |
            PrdProduct.product_code.ilike(keyword) |
            PrdProduct.factory_code.ilike(keyword) |
            PrdProduct.brand.ilike(keyword) |
            PrdProduct.detail_desc.ilike(keyword)
        )

    # 2026-06-14 支持 category_code 字符串（前端下拉框存的是 code 'C01' 等）
    if category_id is None and category_code:
        from models.product_category import PrdProductCategory
        cat = db.query(PrdProductCategory).filter(PrdProductCategory.code == category_code).first()
        if cat is not None:
            category_id = cat.id
        else:
            # 找不到对应类目 → 0 匹配
            return []

    if category_id is not None:
        query = query.filter(PrdProduct.category_id == category_id)
    
    if status is not None:
        query = query.filter(PrdProduct.status == status)
    
    if customer_id is not None:
        from models import PrdCustomerProduct
        product_ids = db.query(PrdCustomerProduct.product_id).filter(
            PrdCustomerProduct.customer_id == customer_id
        ).distinct().all()
        product_ids = [p[0] for p in product_ids]
        if product_ids:
            query = query.filter(PrdProduct.id.in_(product_ids))
        else:
            return []
    
    return query.all()

def update_product(db: Session, product_id: int, product_update: ProductUpdate) -> PrdProduct:
    db_product = get_product(db, product_id)
    if not db_product:
        return None

    update_data = product_update.dict(exclude_unset=True, exclude={"supplier_schemes"})

    if 'carton_length_cm' in update_data or 'carton_width_cm' in update_data or 'carton_height_cm' in update_data:
        length = update_data.get('carton_length_cm', db_product.carton_length_cm)
        width = update_data.get('carton_width_cm', db_product.carton_width_cm)
        height = update_data.get('carton_height_cm', db_product.carton_height_cm)
        if length and width and height:
            update_data['carton_volume_m3'] = VolumeCalculator.calculate_carton_volume(length, width, height)

    for key, value in update_data.items():
        setattr(db_product, key, value)

    if product_update.supplier_schemes is not None:
        db.query(PrdProductSupplier).filter(PrdProductSupplier.product_id == product_id).delete()
        for scheme in product_update.supplier_schemes:
            db_scheme = PrdProductSupplier(
                product_id=product_id,
                supplier_id=scheme.supplier_id,
                customer_id=scheme.customer_id if scheme.customer_id else None,
                factory_code=scheme.factory_code or str(db_product.oe_number),
                units_per_carton=scheme.units_per_carton,
                carton_length_cm=scheme.carton_length_cm,
                carton_width_cm=scheme.carton_width_cm,
                carton_height_cm=scheme.carton_height_cm,
                gross_weight_kg=scheme.gross_weight_kg,
                is_default=scheme.is_default if hasattr(scheme, 'is_default') else False,
                remark=scheme.remark
            )
            db.add(db_scheme)

    db.commit()
    db.refresh(db_product)

    return db_product

def toggle_product_status(db: Session, product_id: int) -> PrdProduct:
    db_product = get_product(db, product_id)
    if not db_product:
        return None
    
    db_product.status = 1 if db_product.status == 0 else 0
    db.commit()
    db.refresh(db_product)
    
    return db_product

def delete_product(db: Session, product_id: int) -> dict:
    db_product = get_product(db, product_id)
    if not db_product:
        return {"success": False, "message": "产品不存在"}
    
    has_pi = db.query(PiProformaInvoiceItem).filter(
        PiProformaInvoiceItem.product_id == product_id
    ).first()
    
    if has_pi:
        return {"success": False, "message": "该产品已关联PI单，无法删除"}
    
    db.query(PrdProductImage).filter(PrdProductImage.product_id == product_id).delete()
    db.delete(db_product)
    db.commit()
    
    return {"success": True, "message": "产品已删除"}

def get_product_images(db: Session, product_id: int):
    return db.query(PrdProductImage).filter(PrdProductImage.product_id == product_id).order_by(PrdProductImage.sort_order).all()

def add_product_image(db: Session, product_id: int, image_url: str, image_type: int = 1, sort_order: int = 0) -> PrdProductImage:
    db_image = PrdProductImage(
        product_id=product_id,
        image_url=image_url,
        image_type=image_type,
        sort_order=sort_order
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return db_image

def delete_product_image(db: Session, image_id: int) -> bool:
    db_image = db.query(PrdProductImage).filter(PrdProductImage.id == image_id).first()
    if not db_image:
        return False
    
    db.delete(db_image)
    db.commit()
    return True
