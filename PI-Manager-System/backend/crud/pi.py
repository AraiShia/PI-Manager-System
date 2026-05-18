from sqlalchemy.orm import Session
from datetime import datetime
from models import (
    PiProformaInvoice, 
    PiProformaInvoiceItem, 
    PiPaymentStage, 
    PiProformaInvoiceVersion,
    PiPriceHistory,
    CrmCustomer,
    PrdProduct
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
            oe_number=item.oe_number,
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
        raise ValueError("PI不存在")
    db_pi.status = status
    db.commit()
    return db_pi

def delete_pi_invoice(db: Session, pi_id: int):
    """删除PI订单"""
    db_pi = get_pi_invoice(db, pi_id)
    if not db_pi:
        raise ValueError("PI不存在")
    # 检查是否已完成，完成的不能删除
    if db_pi.status == 4:
        raise ValueError("已完成的PI不能删除")
    # 先删除关联的明细和付款阶段
    db.query(PiProformaInvoiceItem).filter(PiProformaInvoiceItem.pi_id == pi_id).delete()
    db.query(PiPaymentStage).filter(PiPaymentStage.pi_id == pi_id).delete()
    db.delete(db_pi)
    db.commit()

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
                oe_number=item.oe_number,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=total_price,
                customer_code=item.customer_code,
                detail_desc=item.detail_desc,
                remark=item.remark
            )
            db.add(db_item)
        
        db_pi.total_amount = total_amount
    
    # 处理付款阶段更新
    if pi_update.payment_stages is not None:
        db.query(PiPaymentStage).filter(PiPaymentStage.pi_id == pi_id).delete()
        for stage in pi_update.payment_stages:
            db_stage = PiPaymentStage(
                pi_id=pi_id,
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

def get_pi_invoice_detail(db: Session, pi_id: int):
    """获取PI详情，包含明细项、付款阶段、客户信息"""
    db_pi = get_pi_invoice(db, pi_id)
    if not db_pi:
        return None
    
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == db_pi.customer_id).first()
    items = db.query(PiProformaInvoiceItem).filter(PiProformaInvoiceItem.pi_id == pi_id).all()
    stages = db.query(PiPaymentStage).filter(PiPaymentStage.pi_id == pi_id).order_by(PiPaymentStage.id).all()
    
    result_items = []
    for item in items:
        product = db.query(PrdProduct).filter(PrdProduct.id == item.product_id).first()
        result_items.append({
            "id": item.id,
            "product_id": item.product_id,
            "oe_number": item.oe_number or (product.oe_number if product else None),
            "product_code": product.product_code if product else None,
            "customer_code": item.customer_code,
            "detail_desc": item.detail_desc,
            "quantity": float(item.quantity),
            "unit_price": float(item.unit_price),
            "total_price": float(item.total_price),
            "remark": item.remark
        })
    
    return {
        "id": db_pi.id,
        "dept_id": db_pi.dept_id,
        "pi_no": db_pi.pi_no,
        "customer_id": db_pi.customer_id,
        "customer_name": customer.customer_name if customer else None,
        "customer_code": customer.customer_code if customer else None,
        "total_amount": float(db_pi.total_amount) if db_pi.total_amount else 0,
        "currency": db_pi.currency or "USD",
        "status": db_pi.status or 1,
        "created_at": db_pi.created_at.isoformat() if db_pi.created_at else None,
        "updated_at": db_pi.updated_at.isoformat() if db_pi.updated_at else None,
        "items": result_items,
        "payment_stages": [
            {
                "id": s.id,
                "stage_type": s.stage_type,
                "stage_no": s.stage_no,
                "amount": float(s.amount),
                "due_date": s.due_date.isoformat()[:10] if s.due_date else None,
                "paid_date": s.paid_date.isoformat()[:10] if s.paid_date else None,
                "status": s.status or 1,
                "created_at": s.created_at.isoformat() if s.created_at else None
            }
            for s in stages
        ]
    }

def get_pi_invoices_with_customer(db: Session, skip: int = 0, limit: int = 100, status: int = None):
    """获取PI列表，包含客户信息"""
    query = db.query(
        PiProformaInvoice,
        CrmCustomer.customer_code,
        CrmCustomer.customer_name
    ).outerjoin(
        CrmCustomer, PiProformaInvoice.customer_id == CrmCustomer.id
    )
    if status is not None:
        query = query.filter(PiProformaInvoice.status == status)
    query = query.order_by(PiProformaInvoice.created_at.desc())
    results = query.offset(skip).limit(limit).all()
    return [
        {
            "id": pi.id,
            "dept_id": pi.dept_id,
            "pi_no": pi.pi_no,
            "customer_id": pi.customer_id,
            "customer_code": cc,
            "customer_name": cn,
            "total_amount": float(pi.total_amount) if pi.total_amount else 0,
            "currency": pi.currency or "USD",
            "status": pi.status or 1,
            "created_at": pi.created_at.isoformat() if pi.created_at else None,
            "updated_at": pi.updated_at.isoformat() if pi.updated_at else None
        }
        for pi, cc, cn in results
    ]
