from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class ArCustomerPayment(Base):
    __tablename__ = "ar_customer_payment"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    receipt_no = Column(String(50), nullable=False, unique=True)
    pi_id = Column(Integer, ForeignKey("pi_proforma_invoice.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("crm_customer.id"), nullable=False)
    amount = Column(DECIMAL(15, 4), nullable=False)
    handling_fee = Column(DECIMAL(15, 4))
    payment_date = Column(DateTime, nullable=False)
    remittance_bank = Column(String(200))
    currency = Column(String(10))
    water_image = Column(String(500))
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    
    pi = relationship("PiProformaInvoice")
    customer = relationship("CrmCustomer")

class ApSupplierPayment(Base):
    __tablename__ = "ap_supplier_payment"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    payment_no = Column(String(50), nullable=False, unique=True)
    po_id = Column(Integer, ForeignKey("po_purchase_order.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("sup_supplier.id"), nullable=False)
    deposit_amount = Column(DECIMAL(15, 4))
    deposit_date = Column(DateTime)
    balance_amount = Column(DECIMAL(15, 4))
    balance_date = Column(DateTime)
    total_amount = Column(DECIMAL(15, 4))
    paid_amount = Column(DECIMAL(15, 4))
    unpaid_amount = Column(DECIMAL(15, 4))
    status = Column(Integer, default=1)
    payment_proof = Column(String(500))
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    po = relationship("PoPurchaseOrder")
    supplier = relationship("SupSupplier")
