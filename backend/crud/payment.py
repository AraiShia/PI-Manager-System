from sqlalchemy.orm import Session
from datetime import datetime
from models import (
    ArCustomerPayment,
    ApSupplierPayment,
    ApSupplierPaymentStage,
    PiProformaInvoice,
    PiPaymentStage,
    PoPurchaseOrder
)
from schemas import CustomerPaymentCreate, CustomerPaymentUpdate, SupplierPaymentCreate, SupplierPaymentUpdate, SupplierPaymentStageCreate
from utils.number_generator import NumberGenerator
# FixPlan Task 3: 导入付款同步函数
from crud.pi_sync import _sync_pi_item_from_payment

def create_customer_payment(db: Session, payment: CustomerPaymentCreate) -> ArCustomerPayment:
    pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == payment.pi_id).first()
    if not pi:
        raise ValueError("PI不存在")

    receipt_no = NumberGenerator.generate_receipt_no(db, payment.dept_id)

    actual_amount = payment.actual_amount if payment.actual_amount is not None else (payment.amount - (payment.handling_fee or 0))

    db_payment = ArCustomerPayment(
        dept_id=payment.dept_id,
        receipt_no=receipt_no,
        pi_id=payment.pi_id,
        customer_id=payment.customer_id,
        amount=payment.amount,
        handling_fee=payment.handling_fee,
        actual_amount=actual_amount,
        is_fully_paid=False,
        payment_date=payment.payment_date,
        remittance_bank=payment.remittance_bank,
        currency=payment.currency,
        water_image=payment.water_image,
        payment_method=payment.payment_method,
        order_ids=payment.order_ids,
        remark=payment.remark
    )

    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)

    update_pi_payment_status(db, payment.pi_id)

    # FixPlan Task 3: 客户付款完成后,同步回写PI订单项的付款信息
    try:
        from models.pi import PiProformaInvoiceItem
        # 查找该PI下的所有订单项,逐条同步付款状态
        pi_items = db.query(PiProformaInvoiceItem).filter(
            PiProformaInvoiceItem.pi_id == payment.pi_id
        ).all()
        for pi_item in pi_items:
            _sync_pi_item_from_payment(db, pi_item, pi)
            db.refresh(pi_item)  # 重新加载同步后的字段(customer_prepayment/remaining_payment)
    except Exception as sync_err_pay:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[payment] _sync_pi_item_from_payment failed (non-blocking): {sync_err_pay}")

    return db_payment

def update_customer_payment(db: Session, payment_id: int, payment_update: CustomerPaymentUpdate) -> ArCustomerPayment:
    db_payment = get_customer_payment(db, payment_id)
    if not db_payment:
        return None

    if payment_update.amount is not None:
        db_payment.amount = payment_update.amount
    if payment_update.handling_fee is not None:
        db_payment.handling_fee = payment_update.handling_fee
    if payment_update.actual_amount is not None:
        db_payment.actual_amount = payment_update.actual_amount
    if payment_update.is_fully_paid is not None:
        db_payment.is_fully_paid = payment_update.is_fully_paid
    if payment_update.payment_date is not None:
        db_payment.payment_date = payment_update.payment_date
    if payment_update.remittance_bank is not None:
        db_payment.remittance_bank = payment_update.remittance_bank
    if payment_update.currency is not None:
        db_payment.currency = payment_update.currency
    if payment_update.water_image is not None:
        db_payment.water_image = payment_update.water_image
    if payment_update.remark is not None:
        db_payment.remark = payment_update.remark

    db.commit()
    db.refresh(db_payment)

    update_pi_payment_status(db, db_payment.pi_id)

    return db_payment

def update_pi_payment_status(db: Session, pi_id: int):
    """
    2026-06-16 PI 通路修复

    根据分期表（PiPaymentStage）和实收表（ArCustomerPayment）综合判断 PI 状态：

    数据通路约定：
        - PiPaymentStage.status == 2 表示该分期已付
        - ArCustomerPayment 是一条实际收款的"水单"，amount 必填，actual_amount 可空
        - 同一笔款可能同时存在于两表（同笔分期 + 配对水单），不应重复累加
          规则：以"水单"为准，分期表只用来标识"已付"的标志（is_paid flag）

    PI.status 取值：
        1 = 待付款（默认）
        2 = 已付定金（有 deposit 分期已付）
        3 = 部分付款（无 deposit 或未付齐）
        4 = 已结清（实收合计 >= PI 总金额）
    """
    pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == pi_id).first()
    if not pi:
        return

    stages = db.query(PiPaymentStage).filter(PiPaymentStage.pi_id == pi_id).all()
    payments = db.query(ArCustomerPayment).filter(ArCustomerPayment.pi_id == pi_id).all()

    # 已付合计：以水单为权威数据源
    receipt_paid = sum(float(p.actual_amount or p.amount or 0) for p in payments)
    # 兜底：如果没有水单，则取分期表实付合计
    stage_paid = sum(float(s.amount) for s in stages if s.status == 2)
    total_paid = receipt_paid if payments else stage_paid

    total_due = float(pi.total_amount or 0)

    if total_due > 0 and total_paid >= total_due:
        pi.status = 4
    elif stage_paid > 0 or receipt_paid > 0:
        has_deposit = any(s.stage_type == 'deposit' and s.status == 2 for s in stages)
        pi.status = 2 if has_deposit else 3
    # else: 保持原 status 不变（仍为 1=待付款）

    db.commit()
    db.refresh(pi)

def get_customer_payments(db: Session, skip: int = 0, limit: int = 100, pi_id: int = None, customer_id: int = None):
    query = db.query(ArCustomerPayment)
    if pi_id is not None:
        query = query.filter(ArCustomerPayment.pi_id == pi_id)
    if customer_id is not None:
        pi_ids = [p.id for p in db.query(PiProformaInvoice).filter(PiProformaInvoice.customer_id == customer_id).all()]
        if pi_ids:
            query = query.filter(ArCustomerPayment.pi_id.in_(pi_ids))
        else:
            query = query.filter(ArCustomerPayment.id == 0)
    return query.offset(skip).limit(limit).all()

def get_customer_payment(db: Session, payment_id: int) -> ArCustomerPayment:
    return db.query(ArCustomerPayment).filter(ArCustomerPayment.id == payment_id).first()

def create_supplier_payment(db: Session, payment: SupplierPaymentCreate) -> ApSupplierPayment:
    """创建供应商付款（主从表模式）"""
    po = None
    if payment.po_id:
        po = db.query(PoPurchaseOrder).filter(PoPurchaseOrder.id == payment.po_id).first()
        if not po:
            raise ValueError("采购单不存在")

    payment_no = NumberGenerator.generate_payment_no(db, payment.dept_id)

    # 从stages计算总金额
    total_amount = sum(float(s.amount) for s in payment.stages) if payment.stages else (po.total_amount if po else 0)
    paid_amount = sum(float(s.paid_amount or 0) for s in payment.stages) if payment.stages else 0
    unpaid_amount = total_amount - paid_amount

    db_payment = ApSupplierPayment(
        dept_id=payment.dept_id,
        payment_no=payment_no,
        po_id=payment.po_id,
        supplier_id=payment.supplier_id,
        total_amount=total_amount,
        paid_amount=paid_amount,
        unpaid_amount=unpaid_amount,
        payment_method=payment.payment_method,
        status=1 if unpaid_amount > 0 else 3,
        remark=payment.remark
    )

    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)

    # 创建付款阶段
    for stage_data in payment.stages:
        stage = ApSupplierPaymentStage(
            payment_id=db_payment.id,
            stage_type=stage_data.stage_type,
            stage_name=stage_data.stage_name or _generate_stage_name(stage_data.stage_type, payment.stages),
            amount=stage_data.amount,
            paid_amount=stage_data.paid_amount or 0,
            status=stage_data.status or 1,
            payment_date=stage_data.payment_date,
            payment_proof=stage_data.payment_proof,
            remark=stage_data.remark
        )
        db.add(stage)

    db.commit()
    db.refresh(db_payment)

    return db_payment

def _generate_stage_name(stage_type: str, all_stages: list) -> str:
    """生成阶段名称（尾款自动编号）"""
    if stage_type == 'deposit':
        return '定金'
    elif stage_type == 'balance':
        # 计算已有尾款数量
        balance_count = sum(1 for s in all_stages if s.stage_type == 'balance')
        return f'尾款{balance_count}'
    return stage_type

def update_supplier_payment(db: Session, payment_id: int, payment_update: SupplierPaymentUpdate) -> ApSupplierPayment:
    """更新供应商付款（支持更新stages）"""
    db_payment = get_supplier_payment(db, payment_id)
    if not db_payment:
        return None

    # 更新主表字段
    if payment_update.po_id is not None:
        db_payment.po_id = payment_update.po_id
    if payment_update.supplier_id is not None:
        db_payment.supplier_id = payment_update.supplier_id
    if payment_update.payment_method is not None:
        db_payment.payment_method = payment_update.payment_method
    if payment_update.remark is not None:
        db_payment.remark = payment_update.remark

    # 如果传了stages，更新从表
    if payment_update.stages is not None:
        # 删除旧stages
        db.query(ApSupplierPaymentStage).filter(ApSupplierPaymentStage.payment_id == payment_id).delete()
        
        # 创建新stages
        for stage_data in payment_update.stages:
            stage = ApSupplierPaymentStage(
                payment_id=payment_id,
                stage_type=stage_data.stage_type,
                stage_name=stage_data.stage_name or _generate_stage_name(stage_data.stage_type, payment_update.stages),
                amount=stage_data.amount,
                paid_amount=stage_data.paid_amount or 0,
                status=stage_data.status or 1,
                payment_date=stage_data.payment_date,
                payment_proof=stage_data.payment_proof,
                remark=stage_data.remark
            )
            db.add(stage)
        
        # 重新计算汇总金额
        total_amount = sum(float(s.amount) for s in payment_update.stages)
        paid_amount = sum(float(s.paid_amount or 0) for s in payment_update.stages)
        db_payment.total_amount = total_amount
        db_payment.paid_amount = paid_amount
        db_payment.unpaid_amount = total_amount - paid_amount
        db_payment.status = 3 if db_payment.unpaid_amount <= 0 else (2 if paid_amount > 0 else 1)

    db.commit()
    db.refresh(db_payment)

    return db_payment

def get_supplier_payments(db: Session, skip: int = 0, limit: int = 100, po_id: int = None, supplier_id: int = None):
    """获取供应商付款列表（包含stages）"""
    query = db.query(ApSupplierPayment)
    if po_id is not None:
        query = query.filter(ApSupplierPayment.po_id == po_id)
    if supplier_id is not None:
        query = query.filter(ApSupplierPayment.supplier_id == supplier_id)
    return query.offset(skip).limit(limit).all()

def get_supplier_payments_by_pi(db: Session, pi_id: int):
    """按 PI 获取供应商付款列表（通过采购单关联）"""
    from models import PoPurchaseOrder
    po_ids = [po.id for po in db.query(PoPurchaseOrder).filter(PoPurchaseOrder.pi_id == pi_id).all()]
    if not po_ids:
        return []
    return db.query(ApSupplierPayment).filter(ApSupplierPayment.po_id.in_(po_ids)).all()

def get_supplier_payment(db: Session, payment_id: int) -> ApSupplierPayment:
    """获取单个供应商付款（包含stages）"""
    return db.query(ApSupplierPayment).filter(ApSupplierPayment.id == payment_id).first()

def get_supplier_payment_stages(db: Session, payment_id: int):
    """获取付款阶段列表"""
    return db.query(ApSupplierPaymentStage).filter(ApSupplierPaymentStage.payment_id == payment_id).all()

def update_supplier_payment_stage(db: Session, stage_id: int, stage_type: str = None, paid_amount: float = None, payment_date: datetime = None, payment_proof: str = None) -> ApSupplierPaymentStage:
    """更新单个付款阶段"""
    stage = db.query(ApSupplierPaymentStage).filter(ApSupplierPaymentStage.id == stage_id).first()
    if not stage:
        return None

    if stage_type is not None:
        stage.stage_type = stage_type
    if paid_amount is not None:
        stage.paid_amount = paid_amount
        if stage.amount and paid_amount >= float(stage.amount):
            stage.status = 3  # 已付清
        elif paid_amount > 0:
            stage.status = 2  # 部分付款
    if payment_date is not None:
        stage.payment_date = payment_date
    if payment_proof is not None:
        stage.payment_proof = payment_proof

    db.commit()
    db.refresh(stage)

    # 更新父记录的paid_amount和status
    payment = db.query(ApSupplierPayment).filter(ApSupplierPayment.id == stage.payment_id).first()
    if payment:
        all_stages = get_supplier_payment_stages(db, payment.id)
        payment.paid_amount = sum(float(s.paid_amount or 0) for s in all_stages)
        payment.unpaid_amount = float(payment.total_amount) - payment.paid_amount

        if payment.unpaid_amount <= 0:
            payment.status = 3  # 已付清
        elif payment.paid_amount > 0:
            payment.status = 2  # 部分付款
        else:
            payment.status = 1  # 待付款

        db.commit()
        db.refresh(payment)

    return stage

def get_unmatched_payments(db: Session):
    paid_pis = set(p.pi_id for p in db.query(ArCustomerPayment).all())
    all_pis = set(p.id for p in db.query(PiProformaInvoice).filter(PiProformaInvoice.status < 4).all())
    unmatched_pis = all_pis - paid_pis

    if unmatched_pis:
        return db.query(PiProformaInvoice).filter(PiProformaInvoice.id.in_(unmatched_pis)).all()
    return []
