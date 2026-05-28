from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from crud.product_category import (
    get_product_category, get_product_categories, create_product_category,
    update_product_category, delete_product_category, generate_category_code
)
from schemas.product_category import (
    ProductCategoryCreate, ProductCategoryUpdate, ProductCategoryResponse
)

router = APIRouter()

@router.get("/", response_model=list[ProductCategoryResponse])
def read_categories(status: int = None, db: Session = Depends(get_db)):
    return get_product_categories(db, status=status)

@router.get("/next-code")
def get_next_category_code(db: Session = Depends(get_db)):
    """获取下一个自动编号"""
    return {"code": generate_category_code(db)}

@router.get("/{category_id}", response_model=ProductCategoryResponse)
def read_category(category_id: int, db: Session = Depends(get_db)):
    db_category = get_product_category(db, category_id)
    if db_category is None:
        raise HTTPException(status_code=404, detail="类别不存在")
    return db_category

@router.post("/", response_model=ProductCategoryResponse)
def create_category(category: ProductCategoryCreate, auto_code: bool = True, db: Session = Depends(get_db)):
    """创建类别，auto_code=True时如果没提供编号则自动生成"""
    return create_product_category(db, category, auto_code=auto_code)

@router.put("/{category_id}", response_model=ProductCategoryResponse)
def update_category(category_id: int, category: ProductCategoryUpdate, db: Session = Depends(get_db)):
    db_category = update_product_category(db, category_id, category)
    if db_category is None:
        raise HTTPException(status_code=404, detail="类别不存在")
    return db_category

@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    if not delete_product_category(db, category_id):
        raise HTTPException(status_code=404, detail="类别不存在")
    return {"message": "类别删除成功"}