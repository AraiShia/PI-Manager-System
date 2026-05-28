# -*- coding: utf-8 -*-
"""
采购订单明细项包装规格关联表 CRUD 操作
日期：2026-05-28
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from models.purchase_package import PoPurchaseOrderItemPackage
from models.purchase import PoPurchaseOrderItem
from models.pi import PiProformaInvoiceItem
from schemas.purchase_package import (
    PurchasePackageCreate,
    PurchasePackageUpdate,
    PurchasePackageResponse,
    HistoryPackageResponse,
)


def get_package_by_po_item(db: Session, po_item_id: int) -> Optional[PoPurchaseOrderItemPackage]:
    """根据采购明细项ID获取包装规格"""
    return db.query(PoPurchaseOrderItemPackage).filter(
        PoPurchaseOrderItemPackage.po_item_id == po_item_id
    ).first()


def create_or_update_package(db: Session, po_item_id: int, 
                             package_data: PurchasePackageCreate) -> PoPurchaseOrderItemPackage:
    """创建或更新包装规格（upsert）
    
    事务保护：任何异常都会自动回滚
    """
    try:
        existing = get_package_by_po_item(db, po_item_id)
        
        if existing:
            update_data = package_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if key != "po_item_id" and hasattr(existing, key):
                    setattr(existing, key, value)
            db.flush()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            db_package = PoPurchaseOrderItemPackage(
                po_item_id=po_item_id,
                **{k: v for k, v in package_data.model_dump().items() if k != "po_item_id"}
            )
            db.add(db_package)
            db.flush()
            db.commit()
            db.refresh(db_package)
            return db_package
    except Exception:
        db.rollback()
        raise


def delete_package(db: Session, po_item_id: int) -> bool:
    """删除包装规格
    
    事务保护：任何异常都会自动回滚
    """
    try:
        package = get_package_by_po_item(db, po_item_id)
        if package:
            db.delete(package)
            db.commit()
            return True
        return False
    except Exception:
        db.rollback()
        raise


def get_history_package(db: Session, customer_id: int, product_id: int) -> HistoryPackageResponse:
    """根据客户+产品获取历史包装规格（最近一次）"""
    result = (
        db.query(PoPurchaseOrderItemPackage, PoPurchaseOrderItem)
        .join(PoPurchaseOrderItem, PoPurchaseOrderItemPackage.po_item_id == PoPurchaseOrderItem.id)
        .join(PiProformaInvoiceItem, PoPurchaseOrderItem.pi_item_id == PiProformaInvoiceItem.id)
        .filter(PiProformaInvoiceItem.customer_id == customer_id)
        .filter(PoPurchaseOrderItem.product_id == product_id)
        .order_by(desc(PoPurchaseOrderItemPackage.created_at))
        .first()
    )
    
    if result:
        package, po_item = result
        return HistoryPackageResponse(
            found=True,
            package={
                "packing_type": package.packing_type,
                "units_per_carton": package.units_per_carton,
                "carton_length_cm": float(package.carton_length_cm) if package.carton_length_cm else None,
                "carton_width_cm": float(package.carton_width_cm) if package.carton_width_cm else None,
                "carton_height_cm": float(package.carton_height_cm) if package.carton_height_cm else None,
            },
            source=f"po_item_id: {package.po_item_id}",
            created_at=package.created_at
        )
    
    return HistoryPackageResponse(found=False, package=None)