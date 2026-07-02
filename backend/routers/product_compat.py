# -*- coding: utf-8 -*-
"""
产品接口兼容垫片（Phase 5）

Phase 5 删除 prd_product 表后，前端仍调用 /api/products。
为避免破坏现有前端，本文件提供 /api/products 兼容端点，
底层数据全部来自 prd_customer_product。

新代码请使用 /api/customer-products。
"""
import logging
import json
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from crud.customer_product import (
    get_customer_product,
    get_customer_products,
    get_customer_products_by_customer,
    search_by_oe_number,
    search_by_code,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/products", tags=["products-compat"])


class CompatProductItem(BaseModel):
    """前端兼容用的产品对象

    字段必须与 /api/customer-products/{id} 的 CustomerProductResponse 对齐，
    否则前端的 product_confirmed 信号会丢失 customer_remark / price_rmb 等。
    """
    id: int
    customer_id: Optional[int] = None
    product_code: Optional[str] = None
    system_code: Optional[str] = None
    oe_number: Optional[str] = None
    product_name: Optional[str] = None
    customer_model: Optional[str] = None
    color: Optional[str] = None
    customer_remark: Optional[str] = None
    detail_desc: Optional[str] = None
    brand: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    price_usd: Optional[float] = None
    price_rmb: Optional[float] = None
    image_url: Optional[str] = None
    sub_images: Optional[List[str]] = None
    is_active: bool = True


class CompatProductListResponse(BaseModel):
    items: List[CompatProductItem]
    total: int


def _to_compat_item(cp) -> CompatProductItem:
    """转换：基于 PrdCustomerProduct 字段填充 CompatProductItem

    2026-06-23 扩展：补齐 customer_remark / customer_model / color / price_*
    等字段，使前端的 product_confirmed 信号能拿到完整数据。
    """
    sub_images: List[str] = []
    if getattr(cp, "sub_images", None):
        try:
            sub_images = json.loads(cp.sub_images) if isinstance(cp.sub_images, str) else list(cp.sub_images or [])
        except Exception:
            sub_images = []

    return CompatProductItem(
        id=cp.id,
        customer_id=cp.customer_id,
        product_code=cp.system_code,
        system_code=cp.system_code,
        oe_number=cp.customer_model,
        product_name=cp.product_name or cp.detail_desc,
        customer_model=cp.customer_model,
        color=cp.color,
        customer_remark=cp.customer_remark,
        detail_desc=cp.detail_desc or cp.product_name,
        brand=cp.brand,
        category_id=str(cp.category_id) if cp.category_id is not None else None,
        price_usd=float(cp.price_usd) if cp.price_usd is not None else None,
        price_rmb=float(cp.price_rmb) if cp.price_rmb is not None else None,
        image_url=cp.image_url,
        sub_images=sub_images,
        is_active=bool(cp.is_active) if cp.is_active is not None else True,
    )


@router.get("", response_model=CompatProductListResponse)
def list_products_compat(
    customer_id: Optional[int] = Query(None, description="客户ID"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    兼容旧端点：GET /api/products

    Phase 5 之后该接口代理到 prd_customer_product。
    """
    logger.info(
        "[compat /api/products] 入参 customer_id=%s, search=%s, page=%s, page_size=%s",
        customer_id, search, page, page_size,
    )
    skip = (page - 1) * page_size
    items, total = get_customer_products(
        db,
        customer_id=customer_id,
        search=search,
        skip=skip,
        limit=page_size,
    )
    return CompatProductListResponse(
        items=[_to_compat_item(it) for it in items],
        total=total,
    )


@router.get("/by-customer/{customer_id}", response_model=List[CompatProductItem])
def list_products_by_customer_compat(customer_id: int, db: Session = Depends(get_db)):
    """兼容旧端点：GET /api/products/by-customer/{customer_id}"""
    logger.info("[compat /api/products] by-customer customer_id=%s", customer_id)
    items = get_customer_products_by_customer(db, customer_id)
    return [_to_compat_item(it) for it in items]


@router.get("/by-oe/{oe_number}", response_model=List[CompatProductItem])
def search_by_oe_compat(oe_number: str, db: Session = Depends(get_db)):
    """兼容旧端点：GET /api/products/by-oe/{oe_number}"""
    logger.info("[compat /api/products] by-oe oe=%s", oe_number)
    items = search_by_oe_number(db, oe_number)
    return [_to_compat_item(it) for it in items]


@router.get("/by-code/{code}", response_model=List[CompatProductItem])
def search_by_code_compat(code: str, db: Session = Depends(get_db)):
    """兼容旧端点：GET /api/products/by-code/{code}"""
    logger.info("[compat /api/products] by-code code=%s", code)
    items = search_by_code(db, code)
    return [_to_compat_item(it) for it in items]


@router.get("/{product_id}", response_model=CompatProductItem)
def get_product_compat(product_id: int, db: Session = Depends(get_db)):
    """兼容旧端点：GET /api/products/{product_id}"""
    logger.info("[compat /api/products] get product_id=%s", product_id)
    cp = get_customer_product(db, product_id)
    if not cp:
        raise HTTPException(status_code=404, detail=f"产品 {product_id} 不存在")
    return _to_compat_item(cp)



