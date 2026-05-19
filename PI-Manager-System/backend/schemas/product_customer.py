"""
产品-客户关联Schema
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from decimal import Decimal


class ProductCustomerBase(BaseModel):
    product_id: int
    customer_id: int
    customer_product_code: Optional[str] = None
    customer_oe_number: Optional[str] = None
    price_usd: Optional[Decimal] = None
    price_rmb: Optional[Decimal] = None
    is_active: bool = True


class ProductCustomerCreate(ProductCustomerBase):
    pass


class ProductCustomerUpdate(BaseModel):
    customer_product_code: Optional[str] = None
    customer_oe_number: Optional[str] = None
    price_usd: Optional[Decimal] = None
    price_rmb: Optional[Decimal] = None
    is_active: Optional[bool] = None


class ProductCustomerResponse(ProductCustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProductCustomerDetailResponse(ProductCustomerResponse):
    """包含产品信息的响应"""
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    customer_name: Optional[str] = None