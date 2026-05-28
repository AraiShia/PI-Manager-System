from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MemoRecordCreate(BaseModel):
    entity_type: str
    entity_id: int
    field_name: str
    content: str


class MemoRecordUpdate(BaseModel):
    content: Optional[str] = None


class MemoRecordResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    field_name: str
    content: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
