from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class ShShipment(Base):
    __tablename__ = "sh_shipment"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    shipment_no = Column(String(50), nullable=False, unique=True)
    pi_id = Column(Integer, ForeignKey("pi_proforma_invoice.id"), nullable=False)
    shipment_date = Column(DateTime)
    ci_document = Column(String(500))
    pl_document = Column(String(500))
    payment_status = Column(Integer, default=1)
    status = Column(Integer, default=1)
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    pi = relationship("PiProformaInvoice")

class ShShipmentItem(Base):
    __tablename__ = "sh_shipment_item"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(Integer, ForeignKey("sh_shipment.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("prd_product.id"), nullable=False)
    quantity = Column(DECIMAL(15, 4), nullable=False)
    
    cartons_shipped = Column(DECIMAL(12, 2))
    volume_shipped_m3 = Column(DECIMAL(12, 6))
    
    remark = Column(String(500))
    
    shipment = relationship("ShShipment")
    product = relationship("PrdProduct")
