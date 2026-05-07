from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class CrmCustomer(Base):
    __tablename__ = "crm_customer"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    customer_code = Column(String(20), nullable=False, unique=True)
    customer_name = Column(String(200), nullable=False)
    country = Column(String(100))
    basic_require = Column(Text)
    special_require = Column(Text)
    payment_terms = Column(String(100))
    status = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class CrmCustomerAddress(Base):
    __tablename__ = "crm_customer_address"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("crm_customer.id"), nullable=False)
    country = Column(String(100))
    port = Column(String(200))
    address_detail = Column(String(500))
    is_default = Column(Integer, default=0)
    
    customer = relationship("CrmCustomer")

class CrmCustomerContact(Base):
    __tablename__ = "crm_customer_contact"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("crm_customer.id"), nullable=False)
    name = Column(String(100))
    phone = Column(String(50))
    email = Column(String(100))
    position = Column(String(100))
    is_primary = Column(Integer, default=0)
    
    customer = relationship("CrmCustomer")
