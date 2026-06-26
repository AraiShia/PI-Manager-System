from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class QuoteItemCreate(BaseModel):
    product_id: int
    oe_number: Optional[str] = None
    customer_code: Optional[str] = None
    detail_desc: Optional[str] = None
    quantity: float
    unit_price: float
    remark: Optional[str] = None


class QuoteItemResponse(BaseModel):
    id: int
    quote_id: int
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


class QuoteCreate(BaseModel):
    dept_id: str
    customer_id: int
    currency: Optional[str] = "USD"
    valid_until: Optional[str] = None
    remark: Optional[str] = None
    items: List[QuoteItemCreate]


class QuoteUpdate(BaseModel):
    status: Optional[int] = None
    valid_until: Optional[str] = None
    remark: Optional[str] = None


class QuoteResponse(BaseModel):
    id: int
    quote_no: str
    dept_id: str
    customer_id: int
    customer_name: Optional[str] = None
    currency: str
    total_amount: float
    valid_until: Optional[str] = None
    status: int
    remark: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class QuoteDetailResponse(BaseModel):
    id: int
    quote_no: str
    dept_id: str
    customer_id: int
    customer_name: Optional[str] = None
    currency: str
    total_amount: float
    valid_until: Optional[str] = None
    status: int
    remark: Optional[str] = None
    created_at: Optional[str] = None
    items: List[QuoteItemResponse] = []

    class Config:
        from_attributes = True
