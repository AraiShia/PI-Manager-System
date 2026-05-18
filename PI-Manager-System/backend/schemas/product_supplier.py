from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ProductSupplierBase(BaseModel):
    product_id: int
    supplier_id: int
    factory_code: str

class ProductSupplierCreate(BaseModel):
    product_id: int
    supplier_id: int
    customer_id: Optional[int] = None  # 关联客户（可选）
    factory_code: str
    # 价格信息
    purchase_price: Optional[float] = None
    currency: Optional[str] = 'CNY'
    # 包装信息
    units_per_carton: Optional[int] = None
    carton_length_cm: Optional[float] = None
    carton_width_cm: Optional[float] = None
    carton_height_cm: Optional[float] = None
    gross_weight_kg: Optional[float] = None
    # 其他信息
    moq: Optional[int] = None
    lead_time_days: Optional[int] = None
    purchase_channel: Optional[str] = None
    remark: Optional[str] = None
    special_requirements: Optional[str] = None  # 特殊需求
    is_default: Optional[bool] = False  # 是否默认方案

class ProductSupplierUpdate(BaseModel):
    factory_code: Optional[str] = None
    customer_id: Optional[int] = None
    # 价格信息
    purchase_price: Optional[float] = None
    currency: Optional[str] = None
    # 包装信息
    units_per_carton: Optional[int] = None
    carton_length_cm: Optional[float] = None
    carton_width_cm: Optional[float] = None
    carton_height_cm: Optional[float] = None
    gross_weight_kg: Optional[float] = None
    # 其他信息
    moq: Optional[int] = None
    lead_time_days: Optional[int] = None
    purchase_channel: Optional[str] = None
    remark: Optional[str] = None
    special_requirements: Optional[str] = None
    is_default: Optional[bool] = None

class ProductSupplierResponse(BaseModel):
    id: int
    product_id: int
    supplier_id: int
    customer_id: Optional[int] = None
    factory_code: str
    # 价格信息
    purchase_price: Optional[float] = None
    currency: Optional[str] = None
    # 包装信息
    units_per_carton: Optional[int] = None
    carton_length_cm: Optional[float] = None
    carton_width_cm: Optional[float] = None
    carton_height_cm: Optional[float] = None
    gross_weight_kg: Optional[float] = None
    # 其他信息
    moq: Optional[int] = None
    lead_time_days: Optional[int] = None
    purchase_channel: Optional[str] = None
    remark: Optional[str] = None
    special_requirements: Optional[str] = None
    is_default: Optional[bool] = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ProductSupplierDetailResponse(ProductSupplierResponse):
    supplier_code: Optional[str] = None
    supplier_name: Optional[str] = None
    customer_code: Optional[str] = None
    customer_name: Optional[str] = None
