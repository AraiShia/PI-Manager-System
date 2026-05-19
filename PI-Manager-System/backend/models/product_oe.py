"""
产品OE关联表 - 一个产品可以有多个OE号
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class PrdProductOE(Base):
    """产品OE关联表"""
    __tablename__ = "prd_product_oe"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("prd_product.id", ondelete="CASCADE"), nullable=False)
    oe_number = Column(String(100), nullable=False)
    is_primary = Column(Boolean, default=False, comment="是否主OE号")
    created_at = Column(DateTime, server_default=func.now())
    
    # 关联关系
    product = relationship("PrdProduct", backref="oe_relations")
    
    __table_args__ = (
        Index('ix_prd_product_oe_product_id', 'product_id'),
        Index('ix_prd_product_oe_oe_number', 'oe_number'),
    )
    
    def __repr__(self):
        return f"<PrdProductOE(id={self.id}, product_id={self.product_id}, oe={self.oe_number}, primary={self.is_primary})>"