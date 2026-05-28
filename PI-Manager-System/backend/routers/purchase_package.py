# -*- coding: utf-8 -*-
"""
采购订单明细项包装规格关联表 API 路由
日期：2026-05-28
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from schemas.purchase_package import (
    PurchasePackageCreate,
    PurchasePackageUpdate,
    PurchasePackageResponse,
    HistoryPackageResponse,
)
from crud import purchase_package as crud_package

router = APIRouter(prefix="/purchase-items", tags=["采购包装规格"])


@router.get("/{po_item_id}/package", response_model=PurchasePackageResponse)
def get_package(po_item_id: int, db: Session = Depends(get_db)):
    """获取采购明细项的包装规格
    
    Returns:
        200: 包装规格数据
        404: 包装规格不存在
    """
    package = crud_package.get_package_by_po_item(db, po_item_id)
    if not package:
        raise HTTPException(status_code=404, detail="包装规格不存在")
    return package


@router.post("/{po_item_id}/package", response_model=PurchasePackageResponse)
def create_or_update_package(
    po_item_id: int,
    package_data: PurchasePackageCreate,
    db: Session = Depends(get_db)
):
    """创建或更新采购明细项的包装规格（upsert）"""
    if package_data.po_item_id != po_item_id:
        raise HTTPException(status_code=400, detail="po_item_id 不匹配")
    return crud_package.create_or_update_package(db, po_item_id, package_data)


@router.put("/{po_item_id}/package", response_model=PurchasePackageResponse)
def update_package(
    po_item_id: int,
    package_data: PurchasePackageUpdate,
    db: Session = Depends(get_db)
):
    """更新包装规格"""
    existing = crud_package.get_package_by_po_item(db, po_item_id)
    if not existing:
        raise HTTPException(status_code=404, detail="包装规格不存在")
    create_data = PurchasePackageCreate(po_item_id=po_item_id, **package_data.model_dump(exclude_unset=True))
    return crud_package.create_or_update_package(db, po_item_id, create_data)


@router.delete("/{po_item_id}/package")
def delete_package(po_item_id: int, db: Session = Depends(get_db)):
    """删除包装规格"""
    success = crud_package.delete_package(db, po_item_id)
    if not success:
        raise HTTPException(status_code=404, detail="包装规格不存在")
    return {"message": "删除成功"}


@router.get("/history-package", response_model=HistoryPackageResponse)
def get_history_package(
    customer_id: int = Query(..., description="客户ID", ge=1),
    product_id: int = Query(..., description="产品ID", ge=1),
    db: Session = Depends(get_db)
):
    """根据客户+产品获取历史包装规格（智能回填接口）
    
    参数校验：
    - ge=1 约束确保参数为正整数
    
    返回：
    - found=True + package: 找到历史记录
    - found=False + package=None: 无历史记录（正常返回）
    """
    return crud_package.get_history_package(db, customer_id, product_id)