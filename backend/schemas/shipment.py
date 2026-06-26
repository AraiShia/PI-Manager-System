from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class ShipmentStageCreate(BaseModel):
    """出货阶段创建"""
    id: Optional[int] = None  # 有id表示编辑
    stage_name: Optional[str] = None  # 阶段名称
    stage_no: Optional[int] = 1
    shipment_date: Optional[str] = None  # 接受字符串日期
    container_no: Optional[str] = None
    bl_no: Optional[str] = None
    quantity: Optional[float] = 0
    ci_document: Optional[str] = None
    pl_document: Optional[str] = None
    inventory_quantity: Optional[float] = 0
    inventory_amount: Optional[float] = 0
    storage_location: Optional[str] = None
    payment_status: Optional[int] = 1  # 1=未收款, 2=部分收款, 3=已收齐
    remark: Optional[str] = None

class ShipmentStageResponse(BaseModel):
    """出货阶段响应"""
    id: int
    shipment_id: int
    stage_name: Optional[str] = None
    stage_no: int
    shipment_date: Optional[datetime] = None
    container_no: Optional[str] = None
    bl_no: Optional[str] = None
    quantity: float
    ci_document: Optional[str] = None
    pl_document: Optional[str] = None
    inventory_quantity: float
    inventory_amount: float
    storage_location: Optional[str] = None
    payment_status: int
    remark: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ShipmentItemCreate(BaseModel):
    product_id: int
    pi_item_id: Optional[int] = None
    stage_id: Optional[int] = None  # 关联到具体出货阶段
    quantity: float
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    carton_no: Optional[str] = None
    net_weight: Optional[float] = None
    gross_weight: Optional[float] = None
    dimension: Optional[str] = None
    remark: Optional[str] = None

class ShipmentItemResponse(BaseModel):
    id: int
    shipment_id: int
    stage_id: Optional[int] = None
    product_id: int
    pi_item_id: Optional[int] = None
    quantity: float
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    carton_no: Optional[str] = None
    net_weight: Optional[float] = None
    gross_weight: Optional[float] = None
    dimension: Optional[str] = None
    remark: Optional[str] = None

    class Config:
        from_attributes = True

class ShipmentCreate(BaseModel):
    """出货单创建 - 支持多阶段"""
    dept_id: str
    pi_id: int
    stages: List[ShipmentStageCreate] = []  # 出货阶段列表
    items: List[ShipmentItemCreate] = []
    remark: Optional[str] = None

class ShipmentUpdate(BaseModel):
    """出货单更新"""
    dept_id: Optional[str] = None
    pi_id: Optional[int] = None
    stages: Optional[List[ShipmentStageCreate]] = None
    items: Optional[List[ShipmentItemCreate]] = None
    remark: Optional[str] = None

class ShipmentResponse(BaseModel):
    """出货单响应"""
    id: int
    dept_id: str
    pi_id: int
    pi_no: Optional[str] = None  # PI号
    shipment_no: Optional[str] = None
    ci_no: Optional[str] = None
    ci_locked: bool = False
    customs_no: Optional[str] = None
    pi_nos: Optional[str] = None
    total_amount: Optional[float] = None
    total_cartons: Optional[int] = None
    total_gross_weight: Optional[float] = None
    total_volume: Optional[float] = None
    total_quantity: Optional[float] = None
    payment_status: int = 1
    status: int = 1
    stages_count: int = 0  # 阶段数量
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ShipmentDetailResponse(ShipmentResponse):
    """出货单详情"""
    pass

class CiDocumentCreate(BaseModel):
    stage_id: Optional[int] = None  # 关联到具体阶段
    invoice_no: Optional[str] = None
    invoice_date: Optional[datetime] = None
    exporter: Optional[str] = None
    exporter_address: Optional[str] = None
    exporter_phone: Optional[str] = None
    exporter_fax: Optional[str] = None
    importer: Optional[str] = None
    importer_address: Optional[str] = None
    importer_phone: Optional[str] = None
    importer_fax: Optional[str] = None
    loading_port: Optional[str] = None
    destination_port: Optional[str] = None
    transport_way: Optional[str] = None
    payment_terms: Optional[str] = None
    total_amount: Optional[float] = None
    marks: Optional[str] = None

class PlDocumentCreate(BaseModel):
    stage_id: Optional[int] = None  # 关联到具体阶段
    pl_no: Optional[str] = None
    pl_date: Optional[datetime] = None
    total_cartons: Optional[int] = None
    total_gross_weight: Optional[float] = None
    total_net_weight: Optional[float] = None
    total_volume: Optional[float] = None
    remark: Optional[str] = None

class CiDocumentResponse(BaseModel):
    id: int
    shipment_id: int
    stage_id: Optional[int] = None
    invoice_no: Optional[str] = None
    invoice_date: Optional[datetime] = None
    exporter: Optional[str] = None
    importer: Optional[str] = None
    total_amount: Optional[float] = None
    marks: Optional[str] = None

    class Config:
        from_attributes = True

class PlDocumentResponse(BaseModel):
    id: int
    shipment_id: int
    stage_id: Optional[int] = None
    pl_no: Optional[str] = None
    pl_date: Optional[datetime] = None
    total_cartons: Optional[int] = None
    total_gross_weight: Optional[float] = None
    total_net_weight: Optional[float] = None
    total_volume: Optional[float] = None
    remark: Optional[str] = None

    class Config:
        from_attributes = True
