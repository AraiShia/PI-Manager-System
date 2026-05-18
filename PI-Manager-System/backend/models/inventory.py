from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class InvInventory(Base):
    __tablename__ = "inv_inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    product_id = Column(Integer, ForeignKey("prd_product.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("crm_customer.id"), nullable=False)
    pi_id = Column(Integer)
    po_id = Column(Integer)
    supplier_id = Column(Integer)

    total_quantity = Column(DECIMAL(15, 4), nullable=False)
    shipped_quantity = Column(DECIMAL(15, 4), default=0)
    pending_quantity = Column(DECIMAL(15, 4), default=0)

    purchase_price = Column(DECIMAL(15, 4))

    # 新增字段
    customer_product_code = Column(String(100))           # 客户号/客户产品编码
    inventory_customer_price = Column(DECIMAL(15, 4))     # 库存客户价格
    color = Column(String(50))                             # 颜色（用于区分库存状态）
    stock_status_color = Column(String(20))               # 颜色标识：yellow=已采购未入库, black=已入库, blue=历史留存
    stock_type = Column(Integer, default=1)               # 库存类型：1=新采购(黄), 2=已入库(黑), 3=历史留存(蓝)

    current_location = Column(String(200))
    location_desc = Column(String(500))
    remark = Column(String(500))  # 备注

    purchase_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    product = relationship("PrdProduct")
    customer = relationship("CrmCustomer")

class InvInventoryLog(Base):
    __tablename__ = "inv_inventory_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    product_id = Column(Integer, nullable=False)
    customer_id = Column(Integer, nullable=False)
    pi_id = Column(Integer)

    change_type = Column(Integer, nullable=False)
    change_quantity = Column(DECIMAL(15, 4), nullable=False)
    before_quantity = Column(DECIMAL(15, 4), nullable=False)
    after_quantity = Column(DECIMAL(15, 4), nullable=False)

    ref_type = Column(String(50))
    ref_id = Column(Integer)
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)