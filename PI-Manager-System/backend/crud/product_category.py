from sqlalchemy.orm import Session
from models.product_category import PrdProductCategory
from schemas.product_category import ProductCategoryCreate, ProductCategoryUpdate

def get_product_category(db: Session, category_id: int) -> PrdProductCategory:
    return db.query(PrdProductCategory).filter(PrdProductCategory.id == category_id).first()

def get_product_category_by_code(db: Session, code: str) -> PrdProductCategory:
    return db.query(PrdProductCategory).filter(PrdProductCategory.code == code).first()

def get_product_categories(db: Session, status: int = None) -> list[PrdProductCategory]:
    query = db.query(PrdProductCategory)
    if status is not None:
        query = query.filter(PrdProductCategory.status == status)
    return query.order_by(PrdProductCategory.sort_order).all()

def create_product_category(db: Session, category: ProductCategoryCreate) -> PrdProductCategory:
    db_category = PrdProductCategory(
        code=category.code,
        name=category.name,
        description=category.description,
        status=category.status or 1,
        sort_order=category.sort_order or 0
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

def update_product_category(db: Session, category_id: int, category: ProductCategoryUpdate) -> PrdProductCategory:
    db_category = get_product_category(db, category_id)
    if not db_category:
        return None
    
    if category.name is not None:
        db_category.name = category.name
    if category.description is not None:
        db_category.description = category.description
    if category.status is not None:
        db_category.status = category.status
    if category.sort_order is not None:
        db_category.sort_order = category.sort_order
    
    db.commit()
    db.refresh(db_category)
    return db_category

def delete_product_category(db: Session, category_id: int) -> bool:
    db_category = get_product_category(db, category_id)
    if not db_category:
        return False
    
    db.delete(db_category)
    db.commit()
    return True