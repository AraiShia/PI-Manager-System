from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class ArCustomerPayment(Base):
    __tablename__ = "ar_customer_payment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    receipt_no = Column(String(50), nullable=False, unique=True)
    pi_id = Column(Integer, ForeignKey("pi_proforma_invoice.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("crm_customer.id"), nullable=False)
    amount = Column(DECIMAL(15, 4), nullable=False)          # 应收金额
    handling_fee = Column(DECIMAL(15, 4))                     # 手续费
    actual_amount = Column(DECIMAL(15, 4))                    # 实际到账金额（amount - handling_fee）
    is_fully_paid = Column(Boolean, default=False)           # 是否收齐
    order_ids = Column(String(500))                           # 款项对应的订单ID列表（JSON格式）
    payment_date = Column(DateTime, nullable=False)
    remittance_bank = Column(String(200))
    currency = Column(String(10))
    water_image = Column(String(500))                        # 水单图片
    payment_method = Column(String(50))                      # 付款方式
    remark = Column(String(500))                              # 备注
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)

    pi = relationship("PiProformaInvoice")
    customer = relationship("CrmCustomer")

class ApSupplierPaymentStage(Base):
    __tablename__ = "ap_supplier_payment_stage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(Integer, ForeignKey("ap_supplier_payment.id"), nullable=False)
    stage_type = Column(String(20))                          # deposit=定金, balance1=尾款1, balance2=尾款2
    stage_name = Column(String(50))                          # 阶段名称：定金、尾款1、尾款2
    amount = Column(DECIMAL(15, 4), nullable=False)          # 应付金额
    paid_amount = Column(DECIMAL(15, 4), default=0)          # 已付金额
    status = Column(Integer, default=1)                     # 1=待付, 2=部分付, 3=已付
    payment_date = Column(DateTime)                          # 付款日期
    payment_proof = Column(String(500))                      # 付款凭证
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    payment = relationship("ApSupplierPayment", back_populates="stages")

class ApSupplierPayment(Base):
    __tablename__ = "ap_supplier_payment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10), nullable=False)
    payment_no = Column(String(50), nullable=False, unique=True)
    po_id = Column(Integer, ForeignKey("po_purchase_order.id"))
    supplier_id = Column(Integer, ForeignKey("sup_supplier.id"), nullable=False)

    total_amount = Column(DECIMAL(15, 4))                   # 总应付金额
    paid_amount = Column(DECIMAL(15, 4), default=0)         # 已付金额汇总
    unpaid_amount = Column(DECIMAL(15, 4))                  # 未付金额汇总

    payment_date = Column(DateTime)                          # 付款日期
    payment_stage = Column(String(50))                       # 付款阶段
    actual_amount = Column(DECIMAL(15, 4))                   # 实际付款金额
    payment_method = Column(String(50))                      # 付款方式

    status = Column(Integer, default=1)                       # 1=待付款, 2=部分付款, 3=已付清
    payment_proof = Column(String(500))                      # 付款凭证
    remark = Column(String(500))
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    po = relationship("PoPurchaseOrder")
    supplier = relationship("SupSupplier")
    stages = relationship("ApSupplierPaymentStage", back_populates="payment")