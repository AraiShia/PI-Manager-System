from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class PoPurchaseOrder(Base):
    __tablename__ = "po_purchase_order"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    po_no = Column(String(50), nullable=False, unique=True)
    pi_id = Column(Integer, ForeignKey("pi_proforma_invoice.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("sup_supplier.id"), nullable=False)
    total_amount = Column(DECIMAL(15, 4))
    contract_date = Column(DateTime)
    status = Column(Integer, default=1)
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    pi = relationship("PiProformaInvoice")
    supplier = relationship("SupSupplier")

class PoPurchaseOrderItem(Base):
    __tablename__ = "po_purchase_order_item"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    po_id = Column(Integer, ForeignKey("po_purchase_order.id"), nullable=False)
    pi_item_id = Column(Integer)
    product_id = Column(Integer, ForeignKey("prd_product.id"), nullable=False)
    color_detail = Column(String(500))
    quantity = Column(DECIMAL(15, 4), nullable=False)
    unit_price = Column(DECIMAL(15, 4), nullable=False)
    total_price = Column(DECIMAL(15, 4), nullable=False)
    
    cartons_estimated = Column(DECIMAL(12, 2))
    volume_estimated_m3 = Column(DECIMAL(12, 6))
    gross_weight_kg = Column(DECIMAL(12, 4))
    
    po = relationship("PoPurchaseOrder")
    product = relationship("PrdProduct")

class Po1688Purchase(Base):
    __tablename__ = "po_1688_purchase"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    po_id = Column(Integer)
    pi_id = Column(Integer)
    product_id = Column(Integer)
    product_url = Column(String(500))
    freight = Column(DECIMAL(15, 4))
    payment_method = Column(String(100))
    gross_weight = Column(DECIMAL(10, 4))
