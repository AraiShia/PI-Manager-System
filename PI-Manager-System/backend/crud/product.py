from sqlalchemy.orm import Session
from models import PrdProduct, PrdProductImage, PiProformaInvoiceItem
from schemas import ProductCreate, ProductUpdate
from utils.number_generator import NumberGenerator
from utils.volume_calculator import VolumeCalculator

def create_product(db: Session, product: ProductCreate) -> PrdProduct:
    product_code = NumberGenerator.generate_product_code(db, product.dept_id, product.category_id or 1)
    
    carton_volume_m3 = None
    if product.carton_length_cm and product.carton_width_cm and product.carton_height_cm:
        carton_volume_m3 = VolumeCalculator.calculate_carton_volume(
            product.carton_length_cm,
            product.carton_width_cm,
            product.carton_height_cm
        )
    
    db_product = PrdProduct(
        product_code=product_code,
        **product.dict()
    )
    db_product.carton_volume_m3 = carton_volume_m3
    
    db.add(db_product)
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

def search_products(db: Session, keyword: str = "", category_id: int = None, status: int = None):
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
    
    if category_id is not None:
        query = query.filter(PrdProduct.category_id == category_id)
    
    if status is not None:
        query = query.filter(PrdProduct.status == status)
    
    return query.all()

def update_product(db: Session, product_id: int, product_update: ProductUpdate) -> PrdProduct:
    db_product = get_product(db, product_id)
    if not db_product:
        return None
    
    update_data = product_update.dict(exclude_unset=True)
    
    if 'carton_length_cm' in update_data or 'carton_width_cm' in update_data or 'carton_height_cm' in update_data:
        length = update_data.get('carton_length_cm', db_product.carton_length_cm)
        width = update_data.get('carton_width_cm', db_product.carton_width_cm)
        height = update_data.get('carton_height_cm', db_product.carton_height_cm)
        if length and width and height:
            update_data['carton_volume_m3'] = VolumeCalculator.calculate_carton_volume(length, width, height)
    
    for key, value in update_data.items():
        setattr(db_product, key, value)
    
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
