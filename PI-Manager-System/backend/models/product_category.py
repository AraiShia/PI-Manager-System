from sqlalchemy import Column, String, Integer, Text, DateTime, Index
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class PrdProductCategory(Base):
    __tablename__ = "prd_product_category"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    description = Column(Text)
    status = Column(Integer, default=1)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        Index('ix_prd_product_category_code', 'code'),
        Index('ix_prd_product_category_status', 'status'),
    )