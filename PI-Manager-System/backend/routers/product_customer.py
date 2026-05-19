"""
产品-客户关联API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from app.database import get_db
from schemas.product_customer import (
    ProductCustomerCreate, ProductCustomerUpdate, 
    ProductCustomerResponse, ProductCustomerDetailResponse
)
import crud.product_customer as crud
from models.product_customer import PrdProductCustomer
from models.customer import CrmCustomer

router = APIRouter(prefix="/api/product-customers", tags=["产品客户关联"])


@router.get("", response_model=List[ProductCustomerResponse])
def get_all_product_customers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取所有产品-客户关联"""
    return crud.get_all_product_customers(db, skip=skip, limit=limit)


@router.get("/batch", response_model=List[ProductCustomerDetailResponse])
def get_product_customers_batch(
    product_ids: str = Query(..., description="产品ID列表，逗号分隔，如: 1,2,3"),
    db: Session = Depends(get_db)
):
    """批量获取多个产品的客户关联（优化性能）"""
    try:
        ids = [int(x.strip()) for x in product_ids.split(",") if x.strip()]
        db_pcs = crud.get_product_customers_by_ids(db, ids)
        
        result = []
        for db_pc in db_pcs:
            customer = db.query(CrmCustomer).filter(CrmCustomer.id == db_pc.customer_id).first()
            pc_dict = {
                "id": db_pc.id,
                "product_id": db_pc.product_id,
                "customer_id": db_pc.customer_id,
                "customer_product_code": db_pc.customer_product_code,
                "customer_oe_number": db_pc.customer_oe_number,
                "price_usd": db_pc.price_usd,
                "price_rmb": db_pc.price_rmb,
                "is_active": db_pc.is_active,
                "created_at": db_pc.created_at,
                "updated_at": db_pc.updated_at,
                "customer_code": customer.customer_code if customer else None,
                "customer_name": customer.customer_name if customer else None
            }
            result.append(pc_dict)
        return result
    except Exception as e:
        print(f"批量获取客户产品失败: {e}")
        return []


@router.get("/product/{product_id}", response_model=List[ProductCustomerDetailResponse])
def get_product_customers(product_id: int, db: Session = Depends(get_db)):
    """获取产品的所有客户关联（包含客户信息）"""
    db_pcs = crud.get_product_customers(db, product_id)
    result = []
    for db_pc in db_pcs:
        # 获取客户信息
        customer = db.query(CrmCustomer).filter(CrmCustomer.id == db_pc.customer_id).first()
        pc_dict = {
            "id": db_pc.id,
            "product_id": db_pc.product_id,
            "customer_id": db_pc.customer_id,
            "customer_product_code": db_pc.customer_product_code,
            "customer_oe_number": db_pc.customer_oe_number,
            "price_usd": db_pc.price_usd,
            "price_rmb": db_pc.price_rmb,
            "is_active": db_pc.is_active,
            "created_at": db_pc.created_at,
            "updated_at": db_pc.updated_at,
            "customer_code": customer.customer_code if customer else None,
            "customer_name": customer.customer_name if customer else None
        }
        result.append(pc_dict)
    return result


@router.get("/customer/{customer_id}", response_model=List[ProductCustomerResponse])
def get_customer_products(customer_id: int, db: Session = Depends(get_db)):
    """获取客户的所有产品关联"""
    return crud.get_customer_products(db, customer_id)


@router.get("/product/{product_id}/customer/{customer_id}", response_model=ProductCustomerDetailResponse | None)
def get_product_customer(product_id: int, customer_id: int, db: Session = Depends(get_db)):
    """获取产品-客户的特定关联（包含客户信息）"""
    db_pc = crud.get_product_customer(db, product_id, customer_id)
    if not db_pc:
        return None
    
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == db_pc.customer_id).first()
    return {
        "id": db_pc.id,
        "product_id": db_pc.product_id,
        "customer_id": db_pc.customer_id,
        "customer_product_code": db_pc.customer_product_code,
        "customer_oe_number": db_pc.customer_oe_number,
        "price_usd": db_pc.price_usd,
        "price_rmb": db_pc.price_rmb,
        "is_active": db_pc.is_active,
        "created_at": db_pc.created_at,
        "updated_at": db_pc.updated_at,
        "customer_code": customer.customer_code if customer else None,
        "customer_name": customer.customer_name if customer else None
    }


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