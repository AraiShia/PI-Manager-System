"""
客户产品管理 Schema
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CustomerProductCodeCreate(BaseModel):
    """客户产品编号创建"""
    product_code: str
    is_primary: bool = False
    remark: Optional[str] = None


class CustomerProductCodeResponse(BaseModel):
    """客户产品编号响应"""
    id: int
    customer_product_id: int
    product_code: str
    is_primary: bool
    remark: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CustomerProductOECreate(BaseModel):
    """客户产品OE号创建"""
    oe_number: str
    is_primary: bool = False
    remark: Optional[str] = None


class CustomerProductOEResponse(BaseModel):
    """客户产品OE号响应"""
    id: int
    customer_product_id: int
    oe_number: str
    is_primary: bool
    remark: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CustomerProductCreate(BaseModel):
    """客户产品创建"""
    customer_id: int
    product_name: Optional[str] = None
    customer_model: Optional[str] = None
    color: Optional[str] = None
    customer_remark: Optional[str] = None
    category_id: Optional[str] = None
    price_usd: Optional[float] = None
    price_rmb: Optional[float] = None
    detail_desc: Optional[str] = None
    brand: Optional[str] = None
    specifications: Optional[str] = None
    image_url: Optional[str] = None
    sub_images: Optional[List[str]] = None
    carton_length_cm: Optional[float] = None
    carton_width_cm: Optional[float] = None
    carton_height_cm: Optional[float] = None
    units_per_carton: Optional[int] = None
    gross_weight_kg: Optional[float] = None
    # 编号列表（创建时一并添加）
    codes: Optional[List[str]] = None
    # OE号列表（创建时一并添加）
    oes: Optional[List[str]] = None


class CustomerProductUpdate(BaseModel):
    """客户产品更新"""
    product_name: Optional[str] = None
    customer_model: Optional[str] = None
    color: Optional[str] = None
    customer_remark: Optional[str] = None
    category_id: Optional[str] = None
    price_usd: Optional[float] = None
    price_rmb: Optional[float] = None
    detail_desc: Optional[str] = None
    brand: Optional[str] = None
    specifications: Optional[str] = None
    image_url: Optional[str] = None
    sub_images: Optional[List[str]] = None
    carton_length_cm: Optional[float] = None
    carton_width_cm: Optional[float] = None
    carton_height_cm: Optional[float] = None
    units_per_carton: Optional[int] = None
    gross_weight_kg: Optional[float] = None
    is_active: Optional[bool] = None


class CustomerProductResponse(BaseModel):
    """客户产品响应"""
    id: int
    customer_id: int
    system_code: Optional[str] = None  # 系统产品编号
    product_name: Optional[str] = None
    customer_model: Optional[str] = None
    color: Optional[str] = None
    customer_remark: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    price_usd: Optional[float] = None
    price_rmb: Optional[float] = None
    detail_desc: Optional[str] = None
    brand: Optional[str] = None
    specifications: Optional[str] = None
    image_url: Optional[str] = None
    sub_images: Optional[List[str]] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 关联数据
    customer_name: Optional[str] = None  # 客户名称
    code_count: Optional[int] = 0  # 编号数量
    primary_code: Optional[str] = None  # 主编号（显示用）
    oe_count: Optional[int] = 0  # OE号数量
    primary_oe: Optional[str] = None  # 主OE号
    
    # 完整列表
    codes: Optional[List[CustomerProductCodeResponse]] = []
    oes: Optional[List[CustomerProductOEResponse]] = []
    
    class Config:
        from_attributes = True


class CustomerProductListResponse(BaseModel):
    """客户产品列表响应（含分页）"""
    items: List[CustomerProductResponse]
    total: int
    page: int
    page_size: int


class BatchImportRequest(BaseModel):
    """批量导入请求"""
    items: List[str]  # 要导入的字符串列表
    set_first_as_primary: bool = True  # 是否将第一个设为主