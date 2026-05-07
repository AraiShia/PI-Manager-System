from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CustomerPaymentCreate(BaseModel):
    pi_id: int
    amount: float
    payment_date: datetime
    currency: Optional[str] = "USD"
    fee: Optional[float] = None
    receipt_url: Optional[str] = None
    remark: Optional[str] = None

class CustomerPaymentResponse(BaseModel):
    id: int
    pi_id: int
    amount: float
    payment_date: datetime
    currency: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class SupplierPaymentCreate(BaseModel):
    purchase_order_id: int
    amount: float
    payment_date: datetime
    currency: Optional[str] = "USD"
    fee: Optional[float] = None
    receipt_url: Optional[str] = None
    remark: Optional[str] = None

class SupplierPaymentResponse(BaseModel):
    id: int
    purchase_order_id: int
    amount: float
    payment_date: datetime
    currency: str
    created_at: datetime
    
    class Config:
        from_attributes = True
