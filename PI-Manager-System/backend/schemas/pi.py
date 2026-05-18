from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class PIPaymentStageCreate(BaseModel):
    stage_type: str
    stage_no: Optional[int] = None
    amount: float
    due_date: Optional[datetime] = None

class PIInvoiceItemCreate(BaseModel):
    product_id: int
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

    class Config:
        from_attributes = True

class PIInvoiceItemResponse(BaseModel):
    id: int
    product_id: int
    oe_number: Optional[str] = None
    customer_code: Optional[str] = None
    detail_desc: Optional[str] = None
    quantity: float
    unit_price: float
    total_price: float
    remark: Optional[str] = None
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