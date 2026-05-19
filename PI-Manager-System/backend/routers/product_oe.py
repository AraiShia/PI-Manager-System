"""
产品OE关联API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from schemas.product_oe import ProductOECreate, ProductOEUpdate, ProductOEResponse
import crud.product_oe as crud

router = APIRouter(prefix="/api/product-oes", tags=["产品OE关联"])


@router.get("", response_model=List[ProductOEResponse])
def get_all_product_oes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取所有产品OE关联"""
    return crud.get_all_product_oes(db, skip=skip, limit=limit)


@router.get("/product/{product_id}", response_model=List[ProductOEResponse])
def get_product_oes(product_id: int, db: Session = Depends(get_db)):
    """获取产品的所有OE号"""
    return crud.get_product_oes(db, product_id)


@router.get("/product/{product_id}/primary", response_model=ProductOEResponse | None)
def get_primary_oe(product_id: int, db: Session = Depends(get_db)):
    """获取产品的主OE号"""
    return crud.get_primary_oe(db, product_id)


@router.post("", response_model=ProductOEResponse)
def create_product_oe(oe: ProductOECreate, db: Session = Depends(get_db)):
    """创建产品OE关联"""
    return crud.create_product_oe(db, oe)


@router.put("/{oe_id}", response_model=ProductOEResponse)
def update_product_oe(oe_id: int, oe: ProductOEUpdate, db: Session = Depends(get_db)):
    """更新产品OE"""
    db_oe = crud.update_product_oe(db, oe_id, oe)
    if not db_oe:
        raise HTTPException(status_code=404, detail="OE关联不存在")
    return db_oe


@router.delete("/{oe_id}")
def delete_product_oe(oe_id: int, db: Session = Depends(get_db)):
    """删除产品OE"""
    success = crud.delete_product_oe(db, oe_id)
    if not success:
        raise HTTPException(status_code=404, detail="OE关联不存在")
    return {"message": "删除成功"}


@router.post("/product/{product_id}/set-primary/{oe_id}")
def set_primary_oe(product_id: int, oe_id: int, db: Session = Depends(get_db)):
    """设置主OE号"""
    success = crud.set_primary_oe(db, product_id, oe_id)
    if not success:
        raise HTTPException(status_code=404, detail="设置失败")
    return {"message": "设置成功"}