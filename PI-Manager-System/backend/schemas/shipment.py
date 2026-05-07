from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class ShipmentItemCreate(BaseModel):
    product_id: int
    quantity: float
    unit_price: Optional[float] = None
    remark: Optional[str] = None

class ShipmentCreate(BaseModel):
    dept_id: str
    pi_id: int
    currency: Optional[str] = "USD"
    shipment_date: Optional[datetime] = None
    items: List[ShipmentItemCreate]

class ShipmentResponse(BaseModel):
    id: int
    dept_id: str
    pi_id: int
    status: int
    created_at: datetime
    
    class Config:
        from_attributes = True
