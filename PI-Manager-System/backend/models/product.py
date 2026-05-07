from sqlalchemy import Column, String, Integer, DECIMAL, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class PrdProduct(Base):
    __tablename__ = "prd_product"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    product_code = Column(String(50), nullable=False, unique=True)
    oe_number = Column(String(100), nullable=False)
    factory_code = Column(String(100))
    brand = Column(String(100))
    detail_desc = Column(Text, nullable=False)
    supplier_id = Column(Integer)
    exw_price_incl = Column(DECIMAL(15, 4))
    exw_price_excl = Column(DECIMAL(15, 4))
    fob_price_incl = Column(DECIMAL(15, 4))
    fob_price_excl = Column(DECIMAL(15, 4))
    freight = Column(DECIMAL(15, 4))
    packing_fee = Column(DECIMAL(15, 4))
    purchase_channel = Column(String(100))
    default_image_url = Column(String(500))
    
    carton_length_cm = Column(DECIMAL(10, 2))
    carton_width_cm = Column(DECIMAL(10, 2))
    carton_height_cm = Column(DECIMAL(10, 2))
    units_per_carton = Column(Integer)
    carton_volume_m3 = Column(DECIMAL(12, 6))
    gross_weight_kg = Column(DECIMAL(10, 4))
    
    length_cm = Column(DECIMAL(10, 2))
    width_cm = Column(DECIMAL(10, 2))
    height_cm = Column(DECIMAL(10, 2))
    weight_kg = Column(DECIMAL(10, 4))
    
    category_id = Column(Integer, ForeignKey("prd_product_category.id"))
    status = Column(Integer, default=1)
    is_imported = Column(Integer, default=0, comment="是否已确认导入：0-未导入，1-已导入")
    imported_at = Column(DateTime, comment="导入确认时间")
    imported_by = Column(Integer, comment="导入确认人ID")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    category = relationship("PrdProductCategory")
    
    __table_args__ = (
        Index('ix_prd_product_oe_number', 'oe_number'),
        Index('ix_prd_product_product_code', 'product_code'),
        Index('ix_prd_product_status', 'status'),
        Index('ix_prd_product_supplier_id', 'supplier_id'),
        Index('ix_prd_product_category_id', 'category_id'),
    )

class PrdProductImage(Base):
    __tablename__ = "prd_product_image"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("prd_product.id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    image_type = Column(Integer, default=1)
    sort_order = Column(Integer, default=0)
    
    product = relationship("PrdProduct")

class PrdProductCustomerCode(Base):
    __tablename__ = "prd_product_customer_code"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("prd_product.id"), nullable=False)
    supplier_id = Column(Integer)
    customer_code = Column(String(100), nullable=False)
    remark = Column(String(200))
    
    product = relationship("PrdProduct")
