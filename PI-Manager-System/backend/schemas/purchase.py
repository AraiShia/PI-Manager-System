from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class PurchaseOrderItemCreate(BaseModel):
    product_id: int
    quantity: float
    unit_price: float
    remark: Optional[str] = None

class PurchaseOrderCreate(BaseModel):
    dept_id: str
    pi_id: int
    supplier_id: int
    currency: Optional[str] = "USD"
    items: List[PurchaseOrderItemCreate]

class PurchaseOrderUpdate(BaseModel):
    status: Optional[int] = None
    supplier_id: Optional[int] = None
    currency: Optional[str] = None
    items: Optional[List[PurchaseOrderItemCreate]] = None

class PurchaseOrderResponse(BaseModel):
    id: int
    po_no: str
    dept_id: str
    pi_id: int
    supplier_id: int
    total_amount: float
    status: int
    created_at: datetime
    
    class Config:
        from_attributes = True
