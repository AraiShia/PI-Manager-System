from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class OrderFileCreate(BaseModel):
    pi_id: int
    product_id: Optional[int] = None
    file_type: str
    original_name: str
    stored_name: str
    file_path: str
    file_size: Optional[int] = None
    file_ext: Optional[str] = None


class OrderFileResponse(BaseModel):
    id: int
    pi_id: int
    product_id: Optional[int] = None
    file_type: str
    original_name: str
    stored_name: str
    file_path: str
    file_size: Optional[int] = None
    file_ext: Optional[str] = None
    uploaded_by: Optional[int] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True
