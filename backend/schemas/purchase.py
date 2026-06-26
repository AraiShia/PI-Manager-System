from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class PurchaseOrderItemCreate(BaseModel):
    product_id: int
    pi_item_id: Optional[int] = None
    supplier_id: Optional[int] = None
    product_name: Optional[str] = None
    customer_model: Optional[str] = None
    factory_code: Optional[str] = None
    product_image: Optional[str] = None
    color: Optional[str] = None
    detail_requirement: Optional[str] = None
    link: Optional[str] = None
    quantity: float
    unit_price: float
    total_price: Optional[float] = None
    price_ex_factory: Optional[float] = None
    price_ex_factory_tax: Optional[float] = None
    price_fob: Optional[float] = None
    price_fob_tax: Optional[float] = None
    # 采购费用字段（2026-06-15 新增）
    labeling_fee: Optional[float] = None
    tax_fee: Optional[float] = None
    shipping_fee: Optional[float] = None
    freight: Optional[float] = None
    remark: Optional[str] = None

class PurchaseOrderCreate(BaseModel):
    dept_id: str
    pi_id: int
    supplier_id: Optional[int] = None
    currency: Optional[str] = "USD"
    items: List[PurchaseOrderItemCreate]

class PurchaseOrderUpdate(BaseModel):
    status: Optional[int] = None
    supplier_id: Optional[int] = None
    currency: Optional[str] = None
    items: Optional[List[PurchaseOrderItemCreate]] = None

class PurchaseOrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name_snapshot: Optional[str] = None
    customer_model_snapshot: Optional[str] = None
    factory_code: Optional[str] = None
    product_image: Optional[str] = None
    color: Optional[str] = None
    detail_requirement: Optional[str] = None
    line_1688_url: Optional[str] = None
    quantity: float
    unit_price: float
    total_price: float
    price_ex_factory: Optional[float] = None
    price_ex_factory_tax: Optional[float] = None
    price_fob: Optional[float] = None
    price_fob_tax: Optional[float] = None
    # 采购费用字段（2026-06-15 新增）
    labeling_fee: Optional[float] = None
    tax_fee: Optional[float] = None
    shipping_fee: Optional[float] = None
    freight: Optional[float] = None
    inbound_status: int = 1

    class Config:
        from_attributes = True

class PurchaseOrderResponse(BaseModel):
    id: int
    po_no: str
    dept_id: str
    pi_id: int
    supplier_id: int
    # 2026-06-23：采购管理 Tab 需要展示的便捷字段（从关联表读取）
    pi_no: Optional[str] = None
    supplier_name: Optional[str] = None
    total_amount: float
    status: int
    created_at: datetime

    class Config:
        from_attributes = True

class PurchaseOrderDetailResponse(PurchaseOrderResponse):
    items: List[PurchaseOrderItemResponse] = []

    class Config:
        from_attributes = True

# 1688采购Schema
class Po1688PurchaseCreate(BaseModel):
    dept_id: str
    po_id: Optional[int] = None
    pi_id: Optional[int] = None
    product_id: Optional[int] = None
    supplier_name: Optional[str] = None
    product_url: Optional[str] = None
    product_remark: Optional[str] = None
    color: Optional[str] = None
    invoice_type: Optional[str] = None
    labeling_fee: Optional[float] = None
    shipping_fee: Optional[float] = None
    shipping_method: Optional[str] = None
    carton_count: Optional[int] = None
    freight: Optional[float] = None
    unit_price: Optional[float] = None       # 商品单价（新增，2026-06-09）
    tax_fee: Optional[float] = None          # 税费（新增，2026-06-09）
    payment_method: Optional[str] = None
    gross_weight: Optional[float] = None
    status: Optional[int] = 1

class Po1688PurchaseResponse(BaseModel):
    id: int
    dept_id: str
    po_id: Optional[int] = None
    pi_id: Optional[int] = None
    product_id: Optional[int] = None
    supplier_name: Optional[str] = None
    product_url: Optional[str] = None
    product_remark: Optional[str] = None
    color: Optional[str] = None
    invoice_type: Optional[str] = None
    labeling_fee: Optional[float] = None
    shipping_fee: Optional[float] = None
    shipping_method: Optional[str] = None
    carton_count: Optional[int] = None
    freight: Optional[float] = None
    unit_price: Optional[float] = None       # 商品单价（新增，2026-06-09）
    tax_fee: Optional[float] = None          # 税费（新增，2026-06-09）
    payment_method: Optional[str] = None
    gross_weight: Optional[float] = None
    status: int = 1
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 2026-06-09 任务 3：商品单价并入产品信息 - 新增 batch 提交 schema
class Po1688PurchaseItem(BaseModel):
    """1688 采购 - 单产品条目（按产品维度）"""
    product_id: int
    supplier_name: Optional[str] = None
    product_url: Optional[str] = None
    product_remark: Optional[str] = None
    color: Optional[str] = None
    invoice_type: Optional[str] = None
    labeling_fee: Optional[float] = None
    shipping_fee: Optional[float] = None
    shipping_method: Optional[str] = None
    carton_count: Optional[int] = None
    freight: Optional[float] = None
    unit_price: Optional[float] = None
    tax_fee: Optional[float] = None
    payment_method: Optional[str] = None
    gross_weight: Optional[float] = None


class Po1688PurchaseBatchCreate(BaseModel):
    """1688 采购 - 批量创建（一 PI 多产品维度）"""
    dept_id: str
    po_id: Optional[int] = None
    pi_id: Optional[int] = None
    screenshot: Optional[str] = None
    remark: Optional[str] = None
    items: List[Po1688PurchaseItem]


# 入库批次Schema
class PoInboundBatchCreate(BaseModel):
    dept_id: str
    po_id: Optional[int] = None
    batch_no: Optional[str] = None
    inbound_date: Optional[datetime] = None
    product_id: int
    quantity: float
    inspector: Optional[str] = None
    remark: Optional[str] = None
    status: Optional[int] = 1

class PoInboundBatchUpdate(BaseModel):
    batch_no: Optional[str] = None
    inbound_date: Optional[datetime] = None
    quantity: Optional[float] = None
    inspector: Optional[str] = None
    remark: Optional[str] = None
    status: Optional[int] = None

class PoInboundBatchResponse(BaseModel):
    id: int
    dept_id: str
    po_id: Optional[int] = None
    batch_no: Optional[str] = None
    inbound_date: Optional[datetime] = None
    product_id: int
    quantity: float
    inspector: Optional[str] = None
    remark: Optional[str] = None
    status: int = 1
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
