from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class QuoteItemCreate(BaseModel):
    product_id: int
    quantity: float
    unit_price: float
    remark: Optional[str] = None

class QuoteCreate(BaseModel):
    dept_id: str
    customer_id: int
    currency: Optional[str] = "USD"
    valid_until: Optional[datetime] = None
    items: List[QuoteItemCreate]

class QuoteUpdate(BaseModel):
    status: Optional[int] = None
    valid_until: Optional[datetime] = None

class QuoteResponse(BaseModel):
    id: int
    quote_no: str
    dept_id: str
    customer_id: int
    total_amount: float
    currency: str
    valid_until: Optional[datetime]
    status: int
    created_at: datetime
    
    class Config:
        from_attributes = True
