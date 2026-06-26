# -*- coding: utf-8 -*-
"""
采购订单明细项包装规格关联表 Schema
日期：2026-05-28
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PurchasePackageBase(BaseModel):
    """包装规格基础 Schema"""
    packing_type: Optional[str] = Field(None, description="包装方式: 纸箱/托盘/木箱/无")
    units_per_carton: Optional[int] = Field(None, description="每箱数量/打包规格")
    carton_length_cm: Optional[float] = Field(None, description="纸箱长度(cm)")
    carton_width_cm: Optional[float] = Field(None, description="纸箱宽度(cm)")
    carton_height_cm: Optional[float] = Field(None, description="纸箱高度(cm)")
    gross_weight_kg: Optional[float] = Field(None, description="毛重(kg)")
    boxes_count: Optional[int] = Field(None, description="箱数")
    purchase_channel: Optional[str] = Field(None, description="采购渠道")


class PurchasePackageCreate(PurchasePackageBase):
    """创建包装规格请求"""
    po_item_id: int = Field(..., description="采购明细项ID")


class PurchasePackageUpdate(PurchasePackageBase):
    """更新包装规格请求"""
    pass


class PurchasePackageResponse(PurchasePackageBase):
    """包装规格响应"""
    id: int
    po_item_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HistoryPackageResponse(BaseModel):
    """历史包装规格查询响应"""
    found: bool = Field(..., description="是否找到历史记录")
    package: Optional[PurchasePackageBase] = Field(None, description="包装规格数据")
    source: Optional[str] = Field(None, description="来源说明")
    created_at: Optional[datetime] = Field(None, description="历史记录创建时间")