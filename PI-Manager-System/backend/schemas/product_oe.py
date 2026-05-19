"""
产品OE关联Schema
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ProductOEBase(BaseModel):
    product_id: int
    oe_number: str
    is_primary: bool = False


class ProductOECreate(ProductOEBase):
    pass


class ProductOEUpdate(BaseModel):
    oe_number: Optional[str] = None
    is_primary: Optional[bool] = None


class ProductOEResponse(ProductOEBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True