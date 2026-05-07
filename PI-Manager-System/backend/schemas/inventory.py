from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class InventoryCreate(BaseModel):
    product_id: int
    customer_id: int
    pi_id: int
    purchase_order_id: int
    supplier_id: int
    quantity: float
    purchase_price: float

class InventoryTransfer(BaseModel):
    source_id: int
    target_id: int
    quantity: float

class InventoryResponse(BaseModel):
    id: int
    product_id: int
    customer_id: int
    pi_id: int
    quantity: float
    pending_quantity: float
    purchase_price: float
    current_location: str
    created_at: datetime
    
    class Config:
        from_attributes = True
