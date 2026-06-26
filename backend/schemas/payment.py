from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class CustomerPaymentCreate(BaseModel):
    dept_id: str
    pi_id: int
    customer_id: int
    amount: float
    handling_fee: Optional[float] = None
    actual_amount: Optional[float] = None
    payment_date: datetime
    remittance_bank: Optional[str] = None
    currency: Optional[str] = "USD"
    water_image: Optional[str] = None
    payment_method: Optional[str] = None
    order_ids: Optional[str] = None
    remark: Optional[str] = None

class CustomerPaymentUpdate(BaseModel):
    amount: Optional[float] = None
    handling_fee: Optional[float] = None
    actual_amount: Optional[float] = None
    is_fully_paid: Optional[bool] = None
    payment_date: Optional[datetime] = None
    remittance_bank: Optional[str] = None
    currency: Optional[str] = None
    water_image: Optional[str] = None
    remark: Optional[str] = None

class CustomerPaymentResponse(BaseModel):
    id: int
    dept_id: str
    receipt_no: str
    pi_id: int
    customer_id: int
    amount: float
    handling_fee: Optional[float] = None
    actual_amount: Optional[float] = None
    is_fully_paid: bool = False
    order_ids: Optional[str] = None
    payment_date: datetime
    remittance_bank: Optional[str] = None
    currency: Optional[str] = None
    water_image: Optional[str] = None
    remark: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SupplierPaymentStageCreate(BaseModel):
    id: Optional[int] = None  # 有id表示编辑，无id表示新增
    stage_type: str  # deposit=定金, balance=尾款
    stage_name: Optional[str] = None  # 定金、尾款1、尾款2...
    amount: float  # 应付金额
    paid_amount: Optional[float] = 0  # 已付金额
    status: Optional[int] = 1  # 1=待付, 2=部分付, 3=已付
    payment_date: Optional[datetime] = None
    payment_proof: Optional[str] = None
    remark: Optional[str] = None

class SupplierPaymentStageUpdate(BaseModel):
    stage_type: Optional[str] = None
    stage_name: Optional[str] = None
    amount: Optional[float] = None
    paid_amount: Optional[float] = None
    status: Optional[int] = None
    payment_date: Optional[datetime] = None
    payment_proof: Optional[str] = None
    remark: Optional[str] = None

class SupplierPaymentStageResponse(BaseModel):
    id: int
    payment_id: int
    stage_type: str
    stage_name: Optional[str] = None
    amount: float
    paid_amount: float
    status: int
    payment_date: Optional[datetime] = None
    payment_proof: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SupplierPaymentCreate(BaseModel):
    dept_id: str
    po_id: Optional[int] = None
    supplier_id: int
    total_amount: Optional[float] = None  # 自动计算：sum(stages.amount)
    paid_amount: Optional[float] = 0
    unpaid_amount: Optional[float] = None  # 自动计算
    payment_method: Optional[str] = None
    stages: List[SupplierPaymentStageCreate] = []  # 付款阶段列表
    remark: Optional[str] = None

class SupplierPaymentUpdate(BaseModel):
    po_id: Optional[int] = None
    supplier_id: Optional[int] = None
    total_amount: Optional[float] = None
    paid_amount: Optional[float] = None
    unpaid_amount: Optional[float] = None
    status: Optional[int] = None
    payment_method: Optional[str] = None
    stages: Optional[List[SupplierPaymentStageCreate]] = None  # 传None表示不修改stages
    remark: Optional[str] = None

class SupplierPaymentResponse(BaseModel):
    id: int
    dept_id: str
    payment_no: str
    po_id: Optional[int] = None
    supplier_id: int
    total_amount: float
    paid_amount: float
    unpaid_amount: float
    status: int
    payment_method: Optional[str] = None
    remark: Optional[str] = None
    created_at: datetime
    # stages 通过单独接口获取，不在此返回

    class Config:
        from_attributes = True