from sqlalchemy.orm import Session
from datetime import datetime
from models import (
    ArCustomerPayment,
    ApSupplierPayment,
    PiProformaInvoice,
    PiPaymentStage,
    PoPurchaseOrder
)
from schemas import CustomerPaymentCreate, SupplierPaymentCreate

def create_customer_payment(db: Session, payment: CustomerPaymentCreate) -> ArCustomerPayment:
    pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == payment.pi_id).first()
    if not pi:
        raise ValueError("PI不存在")
    
    db_payment = ArCustomerPayment(
        pi_id=payment.pi_id,
        amount=payment.amount,
        payment_date=payment.payment_date,
        currency=payment.currency,
        fee=payment.fee,
        receipt_url=payment.receipt_url,
        remark=payment.remark
    )
    
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    
    update_pi_payment_status(db, payment.pi_id)
    
    return db_payment

def update_pi_payment_status(db: Session, pi_id: int):
    pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == pi_id).first()
    if not pi:
        return
    
    stages = db.query(PiPaymentStage).filter(PiPaymentStage.pi_id == pi_id).all()
    payments = db.query(ArCustomerPayment).filter(ArCustomerPayment.pi_id == pi_id).all()
    
    total_paid = sum(p.amount for p in payments)
    total_due = sum(s.amount for s in stages)
    
    if total_paid >= total_due:
        pi.status = 4
    elif total_paid > 0:
        has_deposit = any(s.stage_type == 'deposit' and s.status == 2 for s in stages)
        if has_deposit:
            pi.status = 2
        else:
            pi.status = 3
    
    db.commit()
    db.refresh(pi)

def get_customer_payments(db: Session, skip: int = 0, limit: int = 100, pi_id: int = None, customer_id: int = None):
    query = db.query(ArCustomerPayment)
    if pi_id is not None:
        query = query.filter(ArCustomerPayment.pi_id == pi_id)
    if customer_id is not None:
        pi_ids = [p.id for p in db.query(PiProformaInvoice).filter(PiProformaInvoice.customer_id == customer_id).all()]
        query = query.filter(ArCustomerPayment.pi_id.in_(pi_ids))
    return query.offset(skip).limit(limit).all()

def get_customer_payment(db: Session, payment_id: int) -> ArCustomerPayment:
    return db.query(ArCustomerPayment).filter(ArCustomerPayment.id == payment_id).first()

def create_supplier_payment(db: Session, payment: SupplierPaymentCreate) -> ApSupplierPayment:
    po = db.query(PoPurchaseOrder).filter(PoPurchaseOrder.id == payment.purchase_order_id).first()
    if not po:
        raise ValueError("采购单不存在")
    
    db_payment = ApSupplierPayment(
        purchase_order_id=payment.purchase_order_id,
        amount=payment.amount,
        payment_date=payment.payment_date,
        currency=payment.currency,
        fee=payment.fee,
        receipt_url=payment.receipt_url,
        remark=payment.remark
    )
    
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    
    return db_payment

def get_supplier_payments(db: Session, skip: int = 0, limit: int = 100, purchase_order_id: int = None, supplier_id: int = None):
    query = db.query(ApSupplierPayment)
    if purchase_order_id is not None:
        query = query.filter(ApSupplierPayment.purchase_order_id == purchase_order_id)
    if supplier_id is not None:
        po_ids = [p.id for p in db.query(PoPurchaseOrder).filter(PoPurchaseOrder.supplier_id == supplier_id).all()]
        query = query.filter(ApSupplierPayment.purchase_order_id.in_(po_ids))
    return query.offset(skip).limit(limit).all()

def get_supplier_payment(db: Session, payment_id: int) -> ApSupplierPayment:
    return db.query(ApSupplierPayment).filter(ApSupplierPayment.id == payment_id).first()

def get_unmatched_payments(db: Session):
    paid_pis = set(p.pi_id for p in db.query(ArCustomerPayment).all())
    all_pis = set(p.id for p in db.query(PiProformaInvoice).filter(PiProformaInvoice.status < 4).all())
    unmatched_pis = all_pis - paid_pis
    
    return db.query(PiProformaInvoice).filter(PiProformaInvoice.id.in_(unmatched_pis)).all()
