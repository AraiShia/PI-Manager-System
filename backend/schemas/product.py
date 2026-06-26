from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class ProductImageCreate(BaseModel):
    image_url: str
    image_type: int = 1
    sort_order: int = 0

class ProductBase(BaseModel):
    dept_id: str
    oe_number: str
    detail_desc: str
    units_per_carton: Optional[int] = None

class SupplierSchemeCreate(BaseModel):
    supplier_id: int
    supplier_name: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    factory_code: Optional[str] = None
    customer_product_code: Optional[str] = None
    exw_price_incl: Optional[float] = None
    exw_price_excl: Optional[float] = None
    fob_price_incl: Optional[float] = None
    fob_price_excl: Optional[float] = None
    freight: Optional[float] = None
    packing_fee: Optional[float] = None
    units_per_carton: Optional[int] = None
    carton_length_cm: Optional[float] = None
    carton_width_cm: Optional[float] = None
    carton_height_cm: Optional[float] = None
    gross_weight_kg: Optional[float] = None
    weight_kg: Optional[float] = None
    is_default: Optional[bool] = False
    remark: Optional[str] = None

class ProductCreate(ProductBase):
    factory_code: Optional[str] = None
    brand: Optional[str] = None
    supplier_id: Optional[int] = None
    exw_price_incl: Optional[float] = None
    exw_price_excl: Optional[float] = None
    fob_price_incl: Optional[float] = None
    fob_price_excl: Optional[float] = None
    freight: Optional[float] = None
    packing_fee: Optional[float] = None
    purchase_channel: Optional[str] = None
    carton_length_cm: Optional[float] = None
    carton_width_cm: Optional[float] = None
    carton_height_cm: Optional[float] = None
    carton_volume_m3: Optional[float] = None
    gross_weight_kg: Optional[float] = None
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    category_id: Optional[int] = None
    default_image_url: Optional[str] = None
    supplier_schemes: Optional[List[SupplierSchemeCreate]] = None

class ProductUpdate(BaseModel):
    oe_number: Optional[str] = None
    factory_code: Optional[str] = None
    brand: Optional[str] = None
    detail_desc: Optional[str] = None
    supplier_id: Optional[int] = None
    exw_price_incl: Optional[float] = None
    exw_price_excl: Optional[float] = None
    fob_price_incl: Optional[float] = None
    fob_price_excl: Optional[float] = None
    freight: Optional[float] = None
    packing_fee: Optional[float] = None
    purchase_channel: Optional[str] = None
    carton_length_cm: Optional[float] = None
    carton_width_cm: Optional[float] = None
    carton_height_cm: Optional[float] = None
    units_per_carton: Optional[int] = None
    carton_volume_m3: Optional[float] = None
    gross_weight_kg: Optional[float] = None
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    category_id: Optional[int] = None
    status: Optional[int] = None
    default_image_url: Optional[str] = None
    supplier_schemes: Optional[List[SupplierSchemeCreate]] = None

class ProductResponse(ProductBase):
    id: int
    product_code: str
    factory_code: Optional[str] = None
    brand: Optional[str] = None
    supplier_id: Optional[int] = None
    exw_price_incl: Optional[float] = None
    exw_price_excl: Optional[float] = None
    fob_price_incl: Optional[float] = None
    fob_price_excl: Optional[float] = None
    freight: Optional[float] = None
    packing_fee: Optional[float] = None
    purchase_channel: Optional[str] = None
    carton_length_cm: Optional[float] = None
    carton_width_cm: Optional[float] = None
    carton_height_cm: Optional[float] = None
    carton_volume_m3: Optional[float] = None
    gross_weight_kg: Optional[float] = None
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    category_id: Optional[int] = None
    status: int = 1
    created_at: datetime
    default_image_url: Optional[str] = None
    is_imported: int = 0
    imported_at: Optional[datetime] = None
    imported_by: Optional[int] = None
    
    class Config:
        from_attributes = True

class ProductImageResponse(BaseModel):
    id: int
    product_id: int
    image_url: str
    image_type: int
    sort_order: int
    
    class Config:
        from_attributes = True
