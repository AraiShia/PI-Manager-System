from sqlalchemy import Column, String, Integer, Boolean, DECIMAL, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class PiProformaInvoice(Base):
    __tablename__ = "pi_proforma_invoice"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    pi_no = Column(String(50), nullable=False, unique=True)
    customer_id = Column(Integer, ForeignKey("crm_customer.id"), nullable=False)
    total_amount = Column(DECIMAL(15, 4))
    currency = Column(String(10), default="USD")
    status = Column(Integer, default=1)
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # === 2026-06-17 方案B: 同步审计字段 ===
    pi_data_sync_event = Column(JSON, nullable=True)  # 记录每次同步事件详情

    customer = relationship("CrmCustomer")
    items = relationship("PiProformaInvoiceItem", back_populates="pi", cascade="all, delete-orphan")
    payment_stages = relationship("PiPaymentStage", back_populates="pi", cascade="all, delete-orphan")

class PiProformaInvoiceItem(Base):
    __tablename__ = "pi_proforma_invoice_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pi_id = Column(Integer, ForeignKey("pi_proforma_invoice.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("prd_customer_product.id"), nullable=True)  # 2026-06-16 Phase 5: FK 改为 prd_customer_product
    oe_number = Column(String(100))
    customer_code = Column(String(100))
    detail_desc = Column(String(500))
    quantity = Column(DECIMAL(15, 4), nullable=False)
    unit_price = Column(DECIMAL(15, 4), nullable=False)
    total_price = Column(DECIMAL(15, 4), nullable=False)
    remark = Column(Text)
    # 2026-06-12 需求#40：软删除标记
    is_deleted = Column(Boolean, default=False, nullable=False, server_default='0')
    # 2026-06-12 需求#42：临时产品标记（冗余字段，避免频繁关联 PrdProduct 查询）
    is_temporary = Column(Boolean, default=False, nullable=False, server_default='0')
    temp_model = Column(String(100))
    temp_image = Column(String(500))
    temp_category_id = Column(String(10))

    # === 2026-06-17 方案B: 业务回写字段(21个) ===
    # 采购(P0 同步,来自 po_purchase_order_item)
    purchase_price = Column(DECIMAL(15, 4), nullable=True)           # 采购单价
    shipping_fee = Column(DECIMAL(15, 4), nullable=True)              # 运费
    misc_fee = Column(DECIMAL(15, 4), nullable=True)                  # 杂费 = labeling_fee + tax_fee + freight
    total_order_amount = Column(DECIMAL(15, 4), nullable=True)        # 采购总金额
    supplier_name = Column(String(200), nullable=True)                # 供应商名称
    shop_url = Column(String(500), nullable=True)                     # 1688链接 (线下line_1688_url / 线上product_url仅1688)
    delivery_date = Column(DateTime, nullable=True)                   # 交期
    factory_code = Column(String(100), nullable=True)                 # 工厂编号(快照回写)

    # 入库(P0 同步,删除is_received Boolean,统一用storage_status String)
    storage_status = Column(String(20), nullable=True)                # "已入库" / "已采购" / "× 未入库"
    stocked_qty = Column(DECIMAL(15, 4), nullable=True)               # SUM(inbound.quantity)

    # 线上采购选项(P1 同步,重命名 purchase_option → purchase_option_name 对齐UI)
    purchase_option_name = Column(String(200), nullable=True)        # 采购选项/名称

    # 包装规格(P1 同步)
    packaging = Column(String(100), nullable=True)                   # 包装方式
    carton_size = Column(String(100), nullable=True)                 # 外箱尺寸 LxWxH cm
    pack_spec = Column(String(100), nullable=True)                   # 装箱规格 units_per_carton
    carton_gross_weight = Column(DECIMAL(15, 4), nullable=True)      # 毛重 kg

    # 客户付款(P0/P2 同步)
    customer_prepayment = Column(DECIMAL(15, 4), nullable=True)      # 客户预付款
    remaining_payment = Column(DECIMAL(15, 4), nullable=True)        # 剩余应收款 = total - prepayment
    factory_deposit = Column(DECIMAL(15, 4), nullable=True)          # 工厂定金(P2优先级)
    factory_balance = Column(DECIMAL(15, 4), nullable=True)          # 工厂尾款(P2优先级)

    # 产品细节(P1 同步)
    brand = Column(String(100), nullable=True)                       # 品牌

    # 同步审计(P0)
    last_synced_at = Column(DateTime, nullable=True)                 # 最后同步时间戳

    # 🔧 2026-06-22 新增：41列设计缺失字段(导入时直接存入主表)
    customer_model = Column(String(100), nullable=True)              # Col 7 客户型号
    product_feature = Column(Text, nullable=True)                    # Col 8 产品特性
    product_detail = Column(Text, nullable=True)                     # Col 31 产品细节
    invoice_status = Column(String(50), nullable=True)               # Col 40 开票情况

    # 🔧 2026-06-22 新增：包装规格细化字段(41列 Col 33, 35)
    carton_count = Column(Integer, nullable=True)                    # Col 35 箱数
    carton_length_cm = Column(DECIMAL(10, 2), nullable=True)         # Col 33 纸箱长度
    carton_width_cm = Column(DECIMAL(10, 2), nullable=True)          # Col 33 纸箱宽度
    carton_height_cm = Column(DECIMAL(10, 2), nullable=True)         # Col 33 纸箱高度

    pi = relationship("PiProformaInvoice", back_populates="items")
    # product = relationship("PrdCustomerProduct")  # Phase 5 移除：使用 unified_product_lookup

class PiPaymentStage(Base):
    __tablename__ = "pi_payment_stage"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pi_id = Column(Integer, ForeignKey("pi_proforma_invoice.id"), nullable=False)
    stage_type = Column(String(20), nullable=False)
    stage_no = Column(Integer)
    amount = Column(DECIMAL(15, 4), nullable=False)
    due_date = Column(DateTime)
    paid_date = Column(DateTime)
    status = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)
    
    pi = relationship("PiProformaInvoice", back_populates="payment_stages")

class PiProformaInvoiceVersion(Base):
    __tablename__ = "pi_proforma_invoice_version"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pi_id = Column(Integer, ForeignKey("pi_proforma_invoice.id"), nullable=False)
    version_no = Column(Integer, nullable=False)
    snapshot_data = Column(JSON, nullable=False)
    change_desc = Column(String(500))
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    
    pi = relationship("PiProformaInvoice")

class PiPriceHistory(Base):
    __tablename__ = "pi_price_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    customer_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    pi_id = Column(Integer, nullable=False)
    pi_item_id = Column(Integer)
    unit_price = Column(DECIMAL(15, 4), nullable=False)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
