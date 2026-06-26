from sqlalchemy import Column, String, Integer, Text, DateTime, Index, ForeignKey
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
    parent_id = Column(String(10), nullable=True, comment="上级类目代码（如 'C'），NULL=大类")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 注意：children/parent 关系已禁用，因为 parent_id 存储的是 code 而非 id
    # 如需启用层级关系，请使用手动查询方式

    __table_args__ = (
        Index('ix_prd_product_category_code', 'code'),
        Index('ix_prd_product_category_status', 'status'),
        Index('ix_prd_product_category_parent_id', 'parent_id'),
    )