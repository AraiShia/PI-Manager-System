"""
客户回复Schema
"""
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class CustomerReplyBase(BaseModel):
    pi_id: int
    customer_id: int
    reply_date: date
    reply_content: str


class CustomerReplyCreate(CustomerReplyBase):
    pass


class CustomerReplyUpdate(BaseModel):
    reply_date: Optional[date] = None
    reply_content: Optional[str] = None


class CustomerReplyResponse(CustomerReplyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True