from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class InventoryCreate(BaseModel):
    dept_id: Optional[str] = 'S'
    product_id: int
    customer_id: int
    pi_id: Optional[int] = None
    po_id: Optional[int] = None
    supplier_id: Optional[int] = None
    quantity: float
    purchase_price: Optional[float] = None
    current_location: Optional[str] = 'WAREHOUSE'
    customer_product_code: Optional[str] = None
    inventory_customer_price: Optional[float] = None
    color: Optional[str] = None
    stock_type: Optional[int] = 1
    stock_status_color: Optional[str] = None
    remark: Optional[str] = None

class InventoryTransfer(BaseModel):
    source_id: int
    target_id: int
    quantity: float

class InventoryResponse(BaseModel):
    id: int
    product_id: int
    customer_id: int
    pi_id: Optional[int] = None
    po_id: Optional[int] = None
    supplier_id: Optional[int] = None
    total_quantity: float
    shipped_quantity: float
    pending_quantity: float
    purchase_price: Optional[float] = None
    current_location: Optional[str] = None
    customer_product_code: Optional[str] = None
    inventory_customer_price: Optional[float] = None
    color: Optional[str] = None
    stock_status_color: Optional[str] = None
    stock_type: int = 1
    created_at: datetime

    class Config:
        from_attributes = True