from sqlalchemy import Column, String, Integer, DECIMAL, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class SupSupplier(Base):
    __tablename__ = "sup_supplier"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    supplier_code = Column(String(50), nullable=False, unique=True)
    supplier_name = Column(String(200), nullable=False)
    region = Column(String(100))
    source_location = Column(String(200))
    invoice_type = Column(Integer)
    tax_rate = Column(DECIMAL(5, 2))
    supply_cycle_days = Column(Integer)
    return_policy = Column(Text)
    payment_terms = Column(String(100))
    status = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    contacts = relationship("SupSupplierContact", back_populates="supplier", lazy="select")

class SupSupplierContact(Base):
    __tablename__ = "sup_supplier_contact"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey("sup_supplier.id"), nullable=False)
    name = Column(String(100))
    phone = Column(String(50))
    email = Column(String(100))
    address = Column(Text)
    is_primary = Column(Integer, default=0)
    
    supplier = relationship("SupSupplier", back_populates="contacts")
