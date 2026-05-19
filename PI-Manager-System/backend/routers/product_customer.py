"""
产品-客户关联API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from schemas.product_customer import (
    ProductCustomerCreate, ProductCustomerUpdate, 
    ProductCustomerResponse, ProductCustomerDetailResponse
)
import crud.product_customer as crud

router = APIRouter(prefix="/api/product-customers", tags=["产品客户关联"])


@router.get("", response_model=List[ProductCustomerResponse])
def get_all_product_customers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取所有产品-客户关联"""
    return crud.get_all_product_customers(db, skip=skip, limit=limit)


@router.get("/product/{product_id}", response_model=List[ProductCustomerResponse])
def get_product_customers(product_id: int, db: Session = Depends(get_db)):
    """获取产品的所有客户关联"""
    return crud.get_product_customers(db, product_id)


@router.get("/customer/{customer_id}", response_model=List[ProductCustomerResponse])
def get_customer_products(customer_id: int, db: Session = Depends(get_db)):
    """获取客户的所有产品关联"""
    return crud.get_customer_products(db, customer_id)


@router.get("/product/{product_id}/customer/{customer_id}", response_model=ProductCustomerResponse | None)
def get_product_customer(product_id: int, customer_id: int, db: Session = Depends(get_db)):
    """获取产品-客户的特定关联"""
    return crud.get_product_customer(db, product_id, customer_id)


@router.post("", response_model=ProductCustomerResponse)
def create_product_customer(pc: ProductCustomerCreate, db: Session = Depends(get_db)):
    """创建产品-客户关联"""
    return crud.create_product_customer(db, pc)


@router.put("/{pc_id}", response_model=ProductCustomerResponse)
def update_product_customer(pc_id: int, pc: ProductCustomerUpdate, db: Session = Depends(get_db)):
    """更新产品-客户关联"""
    db_pc = crud.update_product_customer(db, pc_id, pc)
    if not db_pc:
        raise HTTPException(status_code=404, detail="关联不存在")
    return db_pc


@router.delete("/{pc_id}")
def delete_product_customer(pc_id: int, db: Session = Depends(get_db)):
    """删除产品-客户关联"""
    success = crud.delete_product_customer(db, pc_id)
    if not success:
        raise HTTPException(status_code=404, detail="关联不存在")
    return {"message": "删除成功"}