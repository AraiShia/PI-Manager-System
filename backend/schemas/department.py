from pydantic import BaseModel
from datetime import datetime

class SysDepartmentBase(BaseModel):
    dept_id: str
    dept_name: str
    db_name: str

class SysDepartmentCreate(SysDepartmentBase):
    pass

class SysDepartmentUpdate(BaseModel):
    dept_name: str | None = None
    db_name: str | None = None
    status: int | None = None

class SysDepartmentResponse(SysDepartmentBase):
    status: int = 1
    created_at: datetime | None = None
    
    class Config:
        from_attributes = True
