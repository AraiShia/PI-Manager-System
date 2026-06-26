from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class CustomerAddressBase(BaseModel):
    country: Optional[str] = None
    port: Optional[str] = None
    address_detail: Optional[str] = None
    is_default: int = 0

class CustomerAddressCreate(CustomerAddressBase):
    pass

class CustomerAddressUpdate(CustomerAddressBase):
    pass

class CustomerAddressResponse(CustomerAddressBase):
    id: int
    customer_id: int
    
    class Config:
        from_attributes = True

class CustomerContactBase(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    position: Optional[str] = None
    is_primary: int = 0

class CustomerContactCreate(CustomerContactBase):
    pass

class CustomerContactResponse(CustomerContactBase):
    id: int
    customer_id: int
    
    class Config:
        from_attributes = True

class CustomerBase(BaseModel):
    dept_id: str
    customer_name: str

class CustomerCreate(CustomerBase):
    customer_code: Optional[str] = None
    country: Optional[str] = None
    basic_require: Optional[str] = None
    special_require: Optional[str] = None
    payment_terms: Optional[str] = None
    addresses: Optional[List[CustomerAddressCreate]] = None
    contacts: Optional[List[CustomerContactCreate]] = None

class CustomerUpdate(BaseModel):
    dept_id: Optional[str] = None
    customer_name: Optional[str] = None
    country: Optional[str] = None
    basic_require: Optional[str] = None
    special_require: Optional[str] = None
    payment_terms: Optional[str] = None
    status: Optional[int] = None

class CustomerResponse(CustomerBase):
    id: int
    customer_code: str
    country: Optional[str] = None
    basic_require: Optional[str] = None
    special_require: Optional[str] = None
    payment_terms: Optional[str] = None
    status: int = 1
    created_at: datetime
    
    class Config:
        from_attributes = True
