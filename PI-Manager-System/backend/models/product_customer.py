"""
产品-客户关联表 - 产品与客户的绑定关系，包含客户产品编号
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, DECIMAL, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class PrdProductCustomer(Base):
    """产品-客户关联表"""
    __tablename__ = "prd_product_customer"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("prd_product.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("crm_customer.id", ondelete="CASCADE"), nullable=False)
    customer_product_code = Column(String(100), comment="客户给的产品编号")
    customer_oe_number = Column(String(100), comment="客户认定的OE号")
    price_usd = Column(DECIMAL(15, 4), comment="USD价格")
    price_rmb = Column(DECIMAL(15, 4), comment="RMB价格")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关联关系
    product = relationship("PrdProduct", backref="customer_relations")
    customer = relationship("CrmCustomer", backref="product_relations")
    
    __table_args__ = (
        UniqueConstraint('product_id', 'customer_id', name='uk_product_customer'),
        Index('ix_prd_product_customer_customer_id', 'customer_id'),
        Index('ix_prd_product_customer_product_id', 'product_id'),
    )
    
    def __repr__(self):
        return f"<PrdProductCustomer(id={self.id}, product_id={self.product_id}, customer_id={self.customer_id})>"