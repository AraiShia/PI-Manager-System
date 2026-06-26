"""
客户产品OE号表 - 一个客户产品可对应多个OE号
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class PrdCustomerProductOE(Base):
    """客户产品OE号表"""
    __tablename__ = "prd_customer_product_oe"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # ForeignKey已经自动创建索引，无需重复
    customer_product_id = Column(Integer, ForeignKey("prd_customer_product.id", ondelete="CASCADE"), nullable=False)
    oe_number = Column(String(100), nullable=False, comment="OE号")
    is_primary = Column(Boolean, default=False, comment="是否主OE号")
    remark = Column(String(200), comment="备注")
    created_at = Column(DateTime, server_default=func.now())
    
    # 关联关系
    customer_product = relationship("PrdCustomerProduct", back_populates="oes")
    
    __table_args__ = (
        # 同一客户产品下的OE号不能重复
        UniqueConstraint('customer_product_id', 'oe_number', name='uk_customer_product_oe'),
    )
    
    def __repr__(self):
        return f"<PrdCustomerProductOE(id={self.id}, product_id={self.customer_product_id}, oe={self.oe_number}, primary={self.is_primary})>"