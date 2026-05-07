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
    status: int
    created_at: datetime
    
    class Config:
        from_attributes = True
