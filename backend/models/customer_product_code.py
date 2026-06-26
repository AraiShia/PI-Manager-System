"""
客户产品编号表 - 一个客户产品可对应多个编号
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class PrdCustomerProductCode(Base):
    """客户产品编号表"""
    __tablename__ = "prd_customer_product_code"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_product_id = Column(Integer, ForeignKey("prd_customer_product.id", ondelete="CASCADE"), nullable=False, index=True)
    product_code = Column(String(100), nullable=False, comment="客户产品编号")
    is_primary = Column(Boolean, default=False, comment="是否主编号")
    remark = Column(String(200), comment="备注")
    created_at = Column(DateTime, server_default=func.now())
    
    # 关联关系
    customer_product = relationship("PrdCustomerProduct", back_populates="codes")
    
    __table_args__ = (
        # 同一客户产品下的编号不能重复
        UniqueConstraint('customer_product_id', 'product_code', name='uk_customer_product_code'),
    )
    
    def __repr__(self):
        return f"<PrdCustomerProductCode(id={self.id}, product_id={self.customer_product_id}, code={self.product_code}, primary={self.is_primary})>"