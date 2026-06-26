from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class PoPurchaseOrder(Base):
    __tablename__ = "po_purchase_order"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    po_no = Column(String(50), nullable=False, unique=True)
    pi_id = Column(Integer, ForeignKey("pi_proforma_invoice.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("sup_supplier.id"), nullable=False)
    total_amount = Column(DECIMAL(15, 4))
    currency = Column(String(10), default='USD', comment="采购币种: USD/RMB")
    contract_date = Column(DateTime)
    status = Column(Integer, default=1)
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    pi = relationship("PiProformaInvoice")
    supplier = relationship("SupSupplier")
    items = relationship("PoPurchaseOrderItem", back_populates="po", cascade="all, delete-orphan")

class PoPurchaseOrderItem(Base):
    __tablename__ = "po_purchase_order_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    po_id = Column(Integer, ForeignKey("po_purchase_order.id"), nullable=False)
    pi_item_id = Column(Integer)
    product_id = Column(Integer, ForeignKey("prd_customer_product.id"), nullable=False)  # Phase 5
    product_name_snapshot = Column(String(255))
    customer_model_snapshot = Column(String(100))
    factory_code = Column(String(100))              # 工厂编号
    product_image = Column(String(500))            # 产品图片URL
    color = Column(String(100))                    # 颜色
    detail_requirement = Column(String(500))       # 细节要求
    line_1688_url = Column(String(500))
    color_detail = Column(String(500))             # 颜色详情（兼容旧字段）
    quantity = Column(DECIMAL(15, 4), nullable=False)
    unit_price = Column(DECIMAL(15, 4), nullable=False)
    total_price = Column(DECIMAL(15, 4), nullable=False)

    # 4种价格类型
    price_ex_factory = Column(DECIMAL(15, 4))      # 出厂价（不含税）
    price_ex_factory_tax = Column(DECIMAL(15, 4))  # 出厂含税价
    price_fob = Column(DECIMAL(15, 4))             # FOB出厂价
    price_fob_tax = Column(DECIMAL(15, 4))         # FOB含税价

    cartons_estimated = Column(DECIMAL(12, 2))
    volume_estimated_m3 = Column(DECIMAL(12, 6))
    gross_weight_kg = Column(DECIMAL(12, 4))

    # 采购费用字段（2026-06-15 新增）
    labeling_fee = Column(DECIMAL(15, 4))           # 贴标费
    tax_fee = Column(DECIMAL(15, 4))                # 税费
    shipping_fee = Column(DECIMAL(15, 4))           # 发货费
    freight = Column(DECIMAL(15, 4))                # 运费

    inbound_status = Column(Integer, default=1)    # 入库状态：1=已采购(黄), 2=已入库(黑)

    po = relationship("PoPurchaseOrder", back_populates="items")
    # product = relationship("PrdCustomerProduct")  # Phase 5 移除

class Po1688Purchase(Base):
    __tablename__ = "po_1688_purchase"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    po_id = Column(Integer)
    pi_id = Column(Integer)
    product_id = Column(Integer)
    supplier_name = Column(String(200))            # 供应商名称（冗余字段，方便查询）
    product_url = Column(String(500))
    product_remark = Column(Text)                 # 产品备注
    color = Column(String(100))                    # 颜色
    invoice_type = Column(String(20))              # 发票类型：无发票/管票/增票
    labeling_fee = Column(DECIMAL(15, 4))          # 贴标费
    shipping_fee = Column(DECIMAL(15, 4))          # 发货费
    unit_price = Column(DECIMAL(15, 4))            # 商品单价（新增，2026-06-09）
    tax_fee = Column(DECIMAL(15, 4))               # 税费（新增，2026-06-09）
    shipping_method = Column(String(100))          # 发货方式
    carton_count = Column(Integer)                # 箱数
    freight = Column(DECIMAL(15, 4))
    payment_method = Column(String(100))
    gross_weight = Column(DECIMAL(10, 4))
    status = Column(Integer, default=1)             # 1=待采购, 2=采购中, 3=已发货, 4=已入库
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class PoInboundBatch(Base):
    __tablename__ = "po_inbound_batch"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    po_id = Column(Integer, ForeignKey("po_purchase_order.id"), nullable=False)
    batch_no = Column(String(50))                  # 入库批次号
    inbound_date = Column(DateTime)                # 入库日期
    product_id = Column(Integer, ForeignKey("prd_customer_product.id"), nullable=False)  # Phase 5
    quantity = Column(DECIMAL(15, 4))              # 入库数量
    inspector = Column(String(100))                # 验收人
    remark = Column(String(500))
    status = Column(Integer, default=1)            # 1=待验收, 2=已验收
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    po = relationship("PoPurchaseOrder")
    # product = relationship("PrdCustomerProduct")  # Phase 5 移除
