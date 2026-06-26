from sqlalchemy import Column, String, Integer, DECIMAL, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class QoQuote(Base):
    __tablename__ = "qo_quote"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    quote_no = Column(String(50), nullable=False, unique=True)
    customer_id = Column(Integer, ForeignKey("crm_customer.id"), nullable=False)
    total_amount = Column(DECIMAL(15, 4))
    currency = Column(String(10), default="USD")
    valid_until = Column(DateTime)
    status = Column(Integer, default=1)
    remark = Column(Text)
    converted_pi_id = Column(Integer)
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    customer = relationship("CrmCustomer")
    items = relationship("QoQuoteItem", back_populates="quote")

class QoQuoteItem(Base):
    __tablename__ = "qo_quote_item"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    quote_id = Column(Integer, ForeignKey("qo_quote.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("prd_customer_product.id"))  # Phase 5
    oe_number = Column(String(100))  # OE号
    customer_code = Column(String(100))  # 客户编号
    detail_desc = Column(String(500))  # 产品描述
    quantity = Column(DECIMAL(15, 4), nullable=False)
    unit_price = Column(DECIMAL(15, 4), nullable=False)
    total_price = Column(DECIMAL(15, 4), nullable=False)
    remark = Column(Text)
    
    quote = relationship("QoQuote", back_populates="items")
    # product = relationship("PrdCustomerProduct")  # Phase 5 移除
