from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

from schemas.pi_detail import PIInvoiceItemDetailResponse, PIInvoiceDetailFullResponse

class PIPaymentStageCreate(BaseModel):
    stage_type: str
    stage_no: Optional[int] = None
    amount: float
    due_date: Optional[datetime] = None

class PIInvoiceItemCreate(BaseModel):
    product_id: Optional[int] = None
    quantity: float
    unit_price: float
    oe_number: Optional[str] = None
    customer_code: Optional[str] = None
    detail_desc: Optional[str] = None
    remark: Optional[str] = None

class PIInvoiceBase(BaseModel):
    dept_id: str
    customer_id: int

class PIInvoiceCreate(PIInvoiceBase):
    items: List[PIInvoiceItemCreate]
    payment_stages: List[PIPaymentStageCreate]
    currency: str = "USD"
    quote_id: Optional[int] = None

class PIInvoiceUpdate(BaseModel):
    status: Optional[int] = None
    customer_id: Optional[int] = None
    currency: Optional[str] = None
    items: Optional[List[PIInvoiceItemCreate]] = None
    payment_stages: Optional[List[PIPaymentStageCreate]] = None

class PIInvoiceResponse(PIInvoiceBase):
    id: int
    pi_no: str
    total_amount: float
    currency: str = "USD"
    status: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    quote_id: Optional[int] = None
    customer_code: Optional[str] = None
    customer_name: Optional[str] = None
    # 2026-06-10 新增 — 总表回填字段
    order_date: Optional[str] = None
    product_count: Optional[int] = 0
    paid_amount: Optional[float] = 0
    storage_status: Optional[str] = ""
    # 库存与状态扩展字段
    has_inventory: Optional[bool] = False
    inventory_quantity: Optional[float] = 0
    inventory_pending: Optional[float] = 0
    inventory_count: Optional[int] = 0
    # 2026-06-11 Phase 7.6: 出货回填字段
    shipment_count: Optional[int] = 0
    shipped_quantity: Optional[float] = 0
    latest_shipment_date: Optional[str] = None
    # 2026-06-11 第 38 条: 已付款/未付款派生字段
    unpaid_amount: Optional[float] = 0
    payment_progress: Optional[float] = 0
    payment_status: Optional[str] = "未付款"

    class Config:
        from_attributes = True

class PIInvoiceItemResponse(BaseModel):
    id: int
    product_id: Optional[int] = None
    oe_number: Optional[str] = None
    customer_code: Optional[str] = None
    detail_desc: Optional[str] = None
    quantity: float
    unit_price: float
    total_price: float
    remark: Optional[str] = None
    # 🔧 2026-06-22 修复：添加缺失字段，response_model 才会返回这些字段
    packaging: Optional[str] = None              # 包装方式
    purchase_option_name: Optional[str] = None   # 采购选项/名称
    packaging_method: Optional[str] = None        # 兼容旧字段
    purchase_option: Optional[str] = None         # 兼容旧字段
    pack_spec: Optional[str] = None               # 装箱规格
    packing_spec: Optional[str] = None
    carton_size: Optional[str] = None
    carton_count: Optional[int] = None            # 多件/箱模式=总箱数；1件多箱模式=数量×每件箱数
    units_per_carton: Optional[int] = None        # 每箱件数（多件/箱模式下使用）
    cartons_per_unit: Optional[int] = None       # 每件箱数（1件多箱模式下使用）
    carton_gross_weight: Optional[float] = None
    total_weight: Optional[float] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    customer_model: Optional[str] = None
    color: Optional[str] = None                     # 产品颜色（与 product_feature 拼接显示）
    product_feature: Optional[str] = None
    factory_no: Optional[str] = None
    class Config:
        from_attributes = True

class PIPaymentStageResponse(BaseModel):
    id: int
    stage_type: str
    stage_no: Optional[int] = None
    amount: float
    due_date: Optional[datetime] = None
    paid_date: Optional[datetime] = None
    status: int = 1
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class PIInvoiceDetailResponse(PIInvoiceResponse):
    customer_name: Optional[str] = None
    customer_code: Optional[str] = None
    items: List[PIInvoiceItemResponse] = []
    payment_stages: List[PIPaymentStageResponse] = []

    class Config:
        from_attributes = True

class PIVersionResponse(BaseModel):
    id: int
    version_no: int
    change_desc: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class PIRelatedDataResponse(BaseModel):
    purchase_orders: List[dict] = []
    shipments: List[dict] = []
    payments: List[dict] = []