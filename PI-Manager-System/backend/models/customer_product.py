"""
客户产品表 - 产品跟随客户，每个客户有独立的产品编号体系
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, DECIMAL, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class PrdCustomerProduct(Base):
    """客户产品表 - 产品跟随客户"""
    __tablename__ = "prd_customer_product"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # ForeignKey已经自动创建索引，无需重复
    customer_id = Column(Integer, ForeignKey("crm_customer.id", ondelete="CASCADE"), nullable=False)
    
    # 系统产品编号：客户编号+部门编号+类别+年份+序号
    # 格式: A01S01240001 (客户编号A01 + 部门S + 类别01 + 年份24 + 序号0001)
    system_code = Column(String(50), nullable=True, unique=True, comment="系统产品编号")
    
    # 兼容旧表结构的字段（暂时保留，迁移后可能删除）
    customer_product_code = Column(String(100), nullable=True, default='')
    
    # 产品基础信息
    product_name = Column(String(200), comment="产品名称")
    customer_model = Column(String(100), comment="客户型号（默认=OE号）")
    color = Column(String(50), comment="颜色")
    customer_remark = Column(Text, comment="客户备注")
    
    # 产品类目
    category_id = Column(String(10), ForeignKey("prd_product_category.code"), nullable=True, comment="产品类目")
    
    # 价格
    price_usd = Column(DECIMAL(15, 4), comment="USD价格")
    price_rmb = Column(DECIMAL(15, 4), comment="RMB价格")
    
    # 产品规格（来自原产品表）
    detail_desc = Column(Text, comment="产品详细描述")
    brand = Column(String(100), comment="品牌")
    specifications = Column(Text, comment="规格参数")
    
    # 图片 - 主图
    image_url = Column(String(500), comment="主图URL")
    # 图片 - 副图（JSON格式存储多个URL）
    sub_images = Column(Text, comment="副图URLs，JSON数组格式")
    
    # 包装信息
    carton_length_cm = Column(DECIMAL(10, 2), comment="纸箱长度(cm)")
    carton_width_cm = Column(DECIMAL(10, 2), comment="纸箱宽度(cm)")
    carton_height_cm = Column(DECIMAL(10, 2), comment="纸箱高度(cm)")
    units_per_carton = Column(Integer, comment="每箱数量")
    gross_weight_kg = Column(DECIMAL(10, 4), comment="毛重(kg)")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否激活")
    deleted_at = Column(DateTime, nullable=True, comment="软删除时间（用于异步物理删除）")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关联关系
    customer = relationship("CrmCustomer", backref="customer_products")
    category = relationship("PrdProductCategory")
    codes = relationship("PrdCustomerProductCode", back_populates="customer_product", cascade="all, delete-orphan")
    oes = relationship("PrdCustomerProductOE", back_populates="customer_product", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<PrdCustomerProduct(id={self.id}, customer_id={self.customer_id}, name={self.product_name})>"