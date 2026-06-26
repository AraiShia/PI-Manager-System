from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class ShShipment(Base):
    __tablename__ = "sh_shipment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    shipment_no = Column(String(50), unique=True)
    pi_id = Column(Integer, ForeignKey("pi_proforma_invoice.id"), nullable=False)
    # 移除单个 shipment_date, container_no, bl_no，移到 stage 中
    total_amount = Column(DECIMAL(15, 4))          # 出货总金额
    total_cartons = Column(Integer)               # 总箱数
    total_gross_weight = Column(DECIMAL(12, 4))   # 总毛重
    total_volume = Column(DECIMAL(12, 6))          # 总体积
    payment_status = Column(Integer, default=1)    # 1=未收款, 2=部分收款, 3=已收齐
    status = Column(Integer, default=1)            # 1=待出货, 2=出货中, 3=已出货, 4=已到达
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    pi = relationship("PiProformaInvoice")
    stages = relationship("ShShipmentStage", back_populates="shipment", cascade="all, delete-orphan")
    items = relationship("ShShipmentItem", back_populates="shipment", cascade="all, delete-orphan")

class ShShipmentStage(Base):
    """出货阶段表 - 支持多阶段出货"""
    __tablename__ = "sh_shipment_stage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(Integer, ForeignKey("sh_shipment.id"), nullable=False)
    stage_name = Column(String(50))               # 阶段名称：出货1、出货2、出货3...
    stage_no = Column(Integer, default=1)         # 阶段序号
    
    # 出货信息
    shipment_date = Column(DateTime)              # 出货日期
    container_no = Column(String(100))            # 柜号
    bl_no = Column(String(100))                   # 提单号
    quantity = Column(DECIMAL(15, 4), default=0)  # 出货数量
    
    # CI/PL 文档
    ci_document = Column(String(500))             # CI文档路径
    pl_document = Column(String(500))             # PL文档路径
    
    # 库存信息（关联库存管理）
    inventory_quantity = Column(DECIMAL(15, 4), default=0)   # 当前库存数量
    inventory_amount = Column(DECIMAL(15, 4), default=0)     # 库存金额
    storage_location = Column(String(200))         # 存放位置
    
    # 客户付款状态
    payment_status = Column(Integer, default=1)    # 1=未收款, 2=部分收款, 3=已收齐
    
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    shipment = relationship("ShShipment", back_populates="stages")

class ShShipmentItem(Base):
    """出货明细（19列）"""
    __tablename__ = "sh_shipment_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(Integer, ForeignKey("sh_shipment.id"), nullable=False)
    stage_id = Column(Integer, ForeignKey("sh_shipment_stage.id"), nullable=True)
    pi_item_id = Column(Integer)
    product_id = Column(Integer, ForeignKey("prd_customer_product.id"), nullable=False)  # Phase 5
    
    # 原始订单信息
    customer_code = Column(String(50))             # 客户编号
    oe_number = Column(String(100))                # OE号
    product_image = Column(String(500))            # 产品图片
    order_quantity = Column(DECIMAL(15, 4))        # 订单数量
    order_unit_price = Column(DECIMAL(15, 4))     # 订单单价
    order_total_amount = Column(DECIMAL(15, 4))   # 订单总金额
    cartons_estimated = Column(Integer)           # 预计箱数
    volume_estimated = Column(DECIMAL(15, 6))      # 预计体积 m³
    gross_weight_kg = Column(DECIMAL(15, 4))      # 毛重 kg
    
    # 出货信息
    shipment_quantity = Column(DECIMAL(15, 4))    # 出货数量
    shipment_unit_price = Column(DECIMAL(15, 4))  # 出货单价
    shipment_total_amount = Column(DECIMAL(15, 4)) # 出货金额
    shipment_cartons = Column(Integer)             # 出货箱数
    shipment_volume = Column(DECIMAL(15, 6))      # 出货体积 m³
    shipment_weight = Column(DECIMAL(15, 4))      # 出货重量 kg
    
    # 剩余计算
    remaining_quantity = Column(DECIMAL(15, 4))    # 剩余数量
    remaining_cartons = Column(Integer)            # 剩余箱数
    remaining_volume = Column(DECIMAL(15, 6))      # 剩余体积
    
    # 兼容旧字段
    quantity = Column(DECIMAL(15, 4), nullable=False)
    unit_price = Column(DECIMAL(15, 4))
    total_price = Column(DECIMAL(15, 4))
    carton_no = Column(String(100))
    net_weight = Column(DECIMAL(12, 4))
    gross_weight = Column(DECIMAL(12, 4))
    dimension = Column(String(200))
    cartons_shipped = Column(DECIMAL(12, 2))
    volume_shipped_m3 = Column(DECIMAL(12, 6))
    remark = Column(String(500))

    shipment = relationship("ShShipment", back_populates="items")
    # product = relationship("PrdCustomerProduct")  # Phase 5 移除
    stage = relationship("ShShipmentStage")

class ShCiDocument(Base):
    __tablename__ = "sh_ci_document"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(Integer, ForeignKey("sh_shipment.id"), nullable=False)
    stage_id = Column(Integer, ForeignKey("sh_shipment_stage.id"), nullable=True)  # 关联到具体阶段
    invoice_no = Column(String(50))               # 发票号
    invoice_date = Column(DateTime)               # 发票日期
    exporter = Column(String(200))                # 出口商
    exporter_address = Column(String(500))         # 出口商地址
    exporter_phone = Column(String(50))            # 出口商电话
    exporter_fax = Column(String(50))              # 出口商传真
    importer = Column(String(200))                # 进口商
    importer_address = Column(String(500))         # 进口商地址
    importer_phone = Column(String(50))            # 进口商电话
    importer_fax = Column(String(50))              # 进口商传真
    loading_port = Column(String(100))            # 装货港
    destination_port = Column(String(100))        # 目的港
    transport_way = Column(String(50))             # 运输方式
    payment_terms = Column(String(100))            # 付款条款
    total_amount = Column(DECIMAL(15, 4))         # 总金额
    marks = Column(String(200))                   # 嘜头
    created_at = Column(DateTime, default=datetime.now)

    shipment = relationship("ShShipment")
    stage = relationship("ShShipmentStage")

class ShPlDocument(Base):
    __tablename__ = "sh_pl_document"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(Integer, ForeignKey("sh_shipment.id"), nullable=False)
    stage_id = Column(Integer, ForeignKey("sh_shipment_stage.id"), nullable=True)  # 关联到具体阶段
    pl_no = Column(String(50))                     # 装箱单号
    pl_date = Column(DateTime)                     # 装箱单日期
    total_cartons = Column(Integer)               # 总箱数
    total_gross_weight = Column(DECIMAL(12, 4))   # 总毛重
    total_net_weight = Column(DECIMAL(12, 4))     # 总净重
    total_volume = Column(DECIMAL(12, 6))         # 总体积
    remark = Column(Text)                         # 备注
    created_at = Column(DateTime, default=datetime.now)

    shipment = relationship("ShShipment")
    stage = relationship("ShShipmentStage")
