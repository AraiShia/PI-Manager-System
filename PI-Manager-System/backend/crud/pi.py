from sqlalchemy.orm import Session
from datetime import datetime
from models import (
    PiProformaInvoice, 
    PiProformaInvoiceItem, 
    PiPaymentStage, 
    PiProformaInvoiceVersion,
    PiPriceHistory,
    CrmCustomer
)
from schemas import PIInvoiceCreate, PIInvoiceUpdate
from utils.number_generator import NumberGenerator

def create_pi_invoice(db: Session, pi: PIInvoiceCreate) -> PiProformaInvoice:
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == pi.customer_id).first()
    if not customer:
        raise ValueError("客户不存在")
    
    pi_no = NumberGenerator.generate_pi_no(db, pi.dept_id, customer.customer_code)
    
    total_amount = sum(item.quantity * item.unit_price for item in pi.items)
    
    db_pi = PiProformaInvoice(
        pi_no=pi_no,
        dept_id=pi.dept_id,
        customer_id=pi.customer_id,
        total_amount=total_amount,
        currency=pi.currency,
        status=1
    )
    
    db.add(db_pi)
    db.commit()
    db.refresh(db_pi)
    
    for item in pi.items:
        total_price = item.quantity * item.unit_price
        
        db_item = PiProformaInvoiceItem(
            pi_id=db_pi.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=total_price,
            customer_code=item.customer_code,
            detail_desc=item.detail_desc,
            remark=item.remark
        )
        db.add(db_item)
        
        price_history = PiPriceHistory(
            dept_id=pi.dept_id,
            customer_id=pi.customer_id,
            product_id=item.product_id,
            pi_id=db_pi.id,
            unit_price=item.unit_price,
            remark=item.remark
        )
        db.add(price_history)
    
    for stage in pi.payment_stages:
        db_stage = PiPaymentStage(
            pi_id=db_pi.id,
            stage_type=stage.stage_type,
            stage_no=stage.stage_no,
            amount=stage.amount,
            due_date=stage.due_date,
            status=1
        )
        db.add(db_stage)
    
    db.commit()
    db.refresh(db_pi)
    
    return db_pi

def get_pi_invoice(db: Session, pi_id: int) -> PiProformaInvoice:
    return db.query(PiProformaInvoice).filter(PiProformaInvoice.id == pi_id).first()

def get_pi_invoice_by_no(db: Session, pi_no: str) -> PiProformaInvoice:
    return db.query(PiProformaInvoice).filter(PiProformaInvoice.pi_no == pi_no).first()

def get_pi_invoices(db: Session, skip: int = 0, limit: int = 100):
    return db.query(PiProformaInvoice).offset(skip).limit(limit).all()

def update_pi_status(db: Session, pi_id: int, status: int) -> PiProformaInvoice:
    db_pi = get_pi_invoice(db, pi_id)
    if not db_pi:
        return None
    
    db_pi.status = status
    db.commit()
    db.refresh(db_pi)
    return db_pi

def get_price_history(db: Session, customer_id: int, product_id: int):
    return db.query(PiPriceHistory).filter(
        PiPriceHistory.customer_id == customer_id,
        PiPriceHistory.product_id == product_id
    ).order_by(PiPriceHistory.created_at.desc()).first()

def update_pi_invoice(db: Session, pi_id: int, pi_update: PIInvoiceUpdate) -> PiProformaInvoice:
    db_pi = get_pi_invoice(db, pi_id)
    if not db_pi:
        return None
    
    if pi_update.customer_id is not None:
        customer = db.query(CrmCustomer).filter(CrmCustomer.id == pi_update.customer_id).first()
        if not customer:
            raise ValueError("客户不存在")
        db_pi.customer_id = pi_update.customer_id
    
    if pi_update.currency is not None:
        db_pi.currency = pi_update.currency
    
    if pi_update.status is not None:
        db_pi.status = pi_update.status
    
    if pi_update.items is not None and len(pi_update.items) > 0:
        db.query(PiProformaInvoiceItem).filter(PiProformaInvoiceItem.pi_id == pi_id).delete()
        
        total_amount = 0
        for item in pi_update.items:
            total_price = item.quantity * item.unit_price
            total_amount += total_price
            
            db_item = PiProformaInvoiceItem(
                pi_id=pi_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=total_price,
                customer_code=item.customer_code,
                detail_desc=item.detail_desc,
                remark=item.remark
            )
            db.add(db_item)
        
        db_pi.total_amount = total_amount
    
    db.commit()
    db.refresh(db_pi)
    return db_pi
