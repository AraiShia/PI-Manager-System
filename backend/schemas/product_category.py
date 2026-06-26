from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ProductCategoryBase(BaseModel):
    code: Optional[str] = None  # 可选，支持自动生成
    name: str
    description: Optional[str] = None
    status: Optional[int] = 1
    sort_order: Optional[int] = 0
    parent_id: Optional[str] = None  # 上级类目代码（如 'C'），NULL=大类

class ProductCategoryCreate(ProductCategoryBase):
    pass

class ProductCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None
    sort_order: Optional[int] = None
    parent_id: Optional[str] = None

class ProductCategoryResponse(ProductCategoryBase):
    id: int
    created_at: Optional[datetime] = None  # 2026-06-14 加固：历史 raw-SQL 插入可能为 NULL
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True