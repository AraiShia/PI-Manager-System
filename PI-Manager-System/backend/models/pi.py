from sqlalchemy import Column, String, Integer, DECIMAL, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class PiProformaInvoice(Base):
    __tablename__ = "pi_proforma_invoice"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    pi_no = Column(String(50), nullable=False, unique=True)
    customer_id = Column(Integer, ForeignKey("crm_customer.id"), nullable=False)
    total_amount = Column(DECIMAL(15, 4))
    currency = Column(String(10), default="USD")
    status = Column(Integer, default=1)
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    customer = relationship("CrmCustomer")

class PiProformaInvoiceItem(Base):
    __tablename__ = "pi_proforma_invoice_item"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pi_id = Column(Integer, ForeignKey("pi_proforma_invoice.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("prd_product.id"), nullable=False)
    oe_number = Column(String(100))
    customer_code = Column(String(100))
    detail_desc = Column(String(500))
    quantity = Column(DECIMAL(15, 4), nullable=False)
    unit_price = Column(DECIMAL(15, 4), nullable=False)
    total_price = Column(DECIMAL(15, 4), nullable=False)
    remark = Column(Text)
    
    pi = relationship("PiProformaInvoice")
    product = relationship("PrdProduct")

class PiPaymentStage(Base):
    __tablename__ = "pi_payment_stage"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pi_id = Column(Integer, ForeignKey("pi_proforma_invoice.id"), nullable=False)
    stage_type = Column(String(20), nullable=False)
    stage_no = Column(Integer)
    amount = Column(DECIMAL(15, 4), nullable=False)
    due_date = Column(DateTime)
    paid_date = Column(DateTime)
    status = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)
    
    pi = relationship("PiProformaInvoice")

class PiProformaInvoiceVersion(Base):
    __tablename__ = "pi_proforma_invoice_version"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pi_id = Column(Integer, ForeignKey("pi_proforma_invoice.id"), nullable=False)
    version_no = Column(Integer, nullable=False)
    snapshot_data = Column(JSON, nullable=False)
    change_desc = Column(String(500))
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    
    pi = relationship("PiProformaInvoice")

class PiPriceHistory(Base):
    __tablename__ = "pi_price_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    customer_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    pi_id = Column(Integer, nullable=False)
    pi_item_id = Column(Integer)
    unit_price = Column(DECIMAL(15, 4), nullable=False)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
