from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, DECIMAL, Boolean, Text, Index
from sqlalchemy.sql import func
from app.database import Base

class PrdProductSupplier(Base):
    __tablename__ = "prd_product_supplier"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("prd_product.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("sup_supplier.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("crm_customer.id"), nullable=True)  # 关联客户（可选）
    factory_code = Column(String(50), nullable=True)
    
    # 价格信息
    purchase_price = Column(DECIMAL(15, 4))  # 采购价格
    currency = Column(String(10), default='CNY')  # 币种
    
    # 包装信息
    units_per_carton = Column(Integer)  # 每箱数量
    carton_length_cm = Column(DECIMAL(10, 2))  # 外箱长
    carton_width_cm = Column(DECIMAL(10, 2))  # 外箱宽
    carton_height_cm = Column(DECIMAL(10, 2))  # 外箱高
    gross_weight_kg = Column(DECIMAL(10, 4))  # 毛重
    
    # 其他信息
    moq = Column(Integer)  # 最小起订量
    lead_time_days = Column(Integer)  # 交货周期(天)
    purchase_channel = Column(String(100))  # 采购渠道
    remark = Column(String(500))  # 备注
    special_requirements = Column(Text)  # 特殊需求（如特殊包装、标签等）
    is_default = Column(Boolean, default=False)  # 是否默认方案
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_prd_product_supplier_factory_code', 'factory_code'),
        Index('ix_prd_product_supplier_product_id', 'product_id'),
        {'sqlite_autoincrement': True},
    )