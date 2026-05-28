from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ProductCategoryBase(BaseModel):
    code: Optional[str] = None  # 可选，支持自动生成
    name: str
    description: Optional[str] = None
    status: Optional[int] = 1
    sort_order: Optional[int] = 0

class ProductCategoryCreate(ProductCategoryBase):
    pass

class ProductCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None
    sort_order: Optional[int] = None

class ProductCategoryResponse(ProductCategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True