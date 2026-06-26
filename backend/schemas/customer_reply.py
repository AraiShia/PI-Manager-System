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
    reply_type: Optional[str] = "reply"
    submitter_name: Optional[str] = None
    sequence_num: Optional[int] = None


class CustomerReplyCreate(CustomerReplyBase):
    pass


class CustomerReplyUpdate(BaseModel):
    reply_date: Optional[date] = None
    reply_content: Optional[str] = None
    reply_type: Optional[str] = None
    submitter_name: Optional[str] = None


class CustomerReplyResponse(CustomerReplyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    sequence_label: Optional[str] = None

    class Config:
        from_attributes = True


class BatchRepliesRequest(BaseModel):
    """批量查询回复记录请求"""
    items: list[dict]


class BatchReplyItemResponse(BaseModel):
    """单条回复记录（含商品信息）"""
    id: int
    pi_id: int
    pi_item_id: Optional[int] = None
    product_name: Optional[str] = None
    pi_no: Optional[str] = None
    reply_type: str
    sequence_label: Optional[str] = None
    submitter_name: Optional[str] = None
    reply_date: Optional[str] = None
    reply_content: str
    customer_name: Optional[str] = None


class BatchRepliesResponse(BaseModel):
    """批量查询响应"""
    replies: list[BatchReplyItemResponse]
    total: int