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

def generate_category_code(db: Session) -> str:
    """自动生成类别编号"""
    # 获取最大编号
    categories = db.query(PrdProductCategory).order_by(PrdProductCategory.code.desc()).all()
    
    if not categories:
        return "01"
    
    max_code = categories[0].code if categories else "00"
    
    # 尝试解析数字部分
    try:
        num = int(max_code)
        new_num = num + 1
        return f"{new_num:02d}"  # 两位数字，如 01, 02...
    except:
        # 如果不是纯数字，找到最后一个数字部分
        import re
        matches = re.findall(r'\d+', max_code)
        if matches:
            last_num = int(matches[-1])
            new_num = last_num + 1
            # 替换最后一个数字
            new_code = re.sub(r'\d+$', f"{new_num:02d}", max_code)
            return new_code
        return max_code + "1"

def create_product_category(db: Session, category: ProductCategoryCreate, auto_code: bool = False) -> PrdProductCategory:
    # 如果启用自动编号且没有提供编号
    code = category.code
    if auto_code and (not code or code.strip() == ''):
        code = generate_category_code(db)

    db_category = PrdProductCategory(
        code=code,
        name=category.name,
        description=category.description,
        status=category.status or 1,
        sort_order=category.sort_order or 0,
        parent_id=category.parent_id,
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
    if category.parent_id is not None:
        db_category.parent_id = category.parent_id

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