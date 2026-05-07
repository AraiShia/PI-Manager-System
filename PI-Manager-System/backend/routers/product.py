from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from crud.product import (
    create_product, get_product, get_products, update_product, delete_product, 
    search_products, get_product_images, toggle_product_status, add_product_image, delete_product_image
)
from schemas.product import ProductCreate, ProductUpdate, ProductResponse, ProductImageResponse
from routers.auth import get_current_user, get_current_admin, get_current_user_optional
from models.user import SysUser
from functools import lru_cache
from datetime import datetime

router = APIRouter(prefix="/api/products", tags=["产品管理"])

@router.post("/", response_model=ProductResponse)
def create_product_api(product: ProductCreate, db: Session = Depends(get_db)):
    return create_product(db, product)

@router.get("/", response_model=list[ProductResponse])
def read_products(skip: int = 0, limit: int = 100, status: int = None, db: Session = Depends(get_db)):
    return get_products(db, skip=skip, limit=limit, status=status)

@router.get("/search", response_model=list[ProductResponse])
def search_products_api(keyword: str = "", category_id: int = None, status: int = None, db: Session = Depends(get_db)):
    return search_products(db, keyword=keyword, category_id=category_id, status=status)

@router.get("/{product_id}", response_model=ProductResponse)
def read_product(product_id: int, db: Session = Depends(get_db)):
    db_product = get_product(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="产品不存在")
    return db_product

@router.put("/{product_id}", response_model=ProductResponse)
def update_product_api(
    product_id: int, 
    product: ProductUpdate, 
    current_user: Optional[SysUser] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    db_product = get_product(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="产品不存在")
    
    # 检查权限：如果产品已导入且当前用户不是管理员，则拒绝修改
    if db_product.is_imported == 1:
        # 如果没有登录或者用户不是管理员，则拒绝修改
        if not current_user or not current_user.is_admin:
            raise HTTPException(
                status_code=403, 
                detail="产品已确认导入，只有管理员可以修改"
            )
    
    db_product = update_product(db, product_id, product)
    return db_product

@router.patch("/{product_id}/status", response_model=ProductResponse)
def toggle_product_status_api(product_id: int, db: Session = Depends(get_db)):
    db_product = toggle_product_status(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="产品不存在")
    return db_product

@router.delete("/{product_id}")
def delete_product_api(product_id: int, db: Session = Depends(get_db)):
    result = delete_product(db, product_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return {"message": result["message"]}

@router.get("/{product_id}/images", response_model=list[ProductImageResponse])
def read_product_images(product_id: int, db: Session = Depends(get_db)):
    db_product = get_product(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="产品不存在")
    return get_product_images(db, product_id)

@router.post("/{product_id}/images", response_model=ProductImageResponse)
def add_product_image_api(
    product_id: int, 
    image_type: int = 1, 
    sort_order: int = 0,
    db: Session = Depends(get_db)
):
    db_product = get_product(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="产品不存在")
    
    return add_product_image(db, product_id, f"/api/products/{product_id}/images/placeholder", image_type, sort_order)

@router.delete("/images/{image_id}")
def delete_product_image_api(image_id: int, db: Session = Depends(get_db)):
    success = delete_product_image(db, image_id)
    if not success:
        raise HTTPException(status_code=404, detail="图片不存在")
    return {"message": "图片已删除"}

@router.patch("/{product_id}/confirm-import")
def confirm_import_product(
    product_id: int,
    current_user: Optional[SysUser] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """确认产品导入"""
    print(f"DEBUG - confirm_import_product called for product_id: {product_id}")
    print(f"DEBUG - current_user: {current_user}")
    
    db_product = get_product(db, product_id)
    if db_product is None:
        print(f"DEBUG - Product {product_id} not found")
        raise HTTPException(status_code=404, detail="产品不存在")
    
    if db_product.is_imported == 1:
        print(f"DEBUG - Product {product_id} already imported")
        raise HTTPException(status_code=400, detail="产品已确认导入")
    
    db_product.is_imported = 1
    db_product.imported_at = datetime.now()
    db_product.imported_by = current_user.id if current_user else 1
    db.commit()
    db.refresh(db_product)
    
    print(f"DEBUG - Product {product_id} imported successfully")
    return {"message": "产品导入已确认", "product": db_product}

@router.patch("/{product_id}/cancel-import")
def cancel_import_product(
    product_id: int,
    current_user: Optional[SysUser] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """取消产品导入确认（仅管理员）"""
    print(f"DEBUG - cancel_import_product called for product_id: {product_id}")
    print(f"DEBUG - current_user: {current_user}")
    
    db_product = get_product(db, product_id)
    if db_product is None:
        print(f"DEBUG - Product {product_id} not found")
        raise HTTPException(status_code=404, detail="产品不存在")
    
    if db_product.is_imported == 0:
        print(f"DEBUG - Product {product_id} not imported")
        raise HTTPException(status_code=400, detail="产品未确认导入")
    
    # 检查权限：只有管理员可以取消导入
    if not current_user or not current_user.is_admin:
        print(f"DEBUG - User {current_user} is not admin, access denied")
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    db_product.is_imported = 0
    db_product.imported_at = None
    db_product.imported_by = None
    db.commit()
    db.refresh(db_product)
    
    print(f"DEBUG - Product {product_id} import canceled successfully")
    return {"message": "产品导入确认已取消", "product": db_product}
