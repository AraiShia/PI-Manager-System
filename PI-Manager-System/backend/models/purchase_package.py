# -*- coding: utf-8 -*-
"""
采购订单明细项包装规格关联表数据模型
日期：2026-05-28
"""

from sqlalchemy import Column, BigInteger, Integer, DECIMAL, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class PoPurchaseOrderItemPackage(Base):
    """采购订单明细项包装规格关联表
    
    用于存储每个采购订单明细项的包装规格数据。
    数据跟随订单生命周期，与订单绑定而非产品。
    """
    __tablename__ = "po_purchase_order_item_package"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    po_item_id = Column(
        BigInteger, 
        ForeignKey("po_purchase_order_item.id", ondelete="CASCADE"), 
        nullable=False, 
        unique=True, 
        comment="采购明细项ID"
    )
    packing_type = Column(String(50), comment="包装方式: 纸箱/托盘/木箱/无")
    units_per_carton = Column(Integer, comment="每箱数量/打包规格")
    carton_length_cm = Column(DECIMAL(10,2), comment="纸箱长度(cm)")
    carton_width_cm = Column(DECIMAL(10,2), comment="纸箱宽度(cm)")
    carton_height_cm = Column(DECIMAL(10,2), comment="纸箱高度(cm)")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    po_item = relationship("PoPurchaseOrderItem", backref="package")