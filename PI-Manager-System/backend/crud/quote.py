from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from models import (
    QoQuote,
    QoQuoteItem,
    PiPriceHistory,
    CrmCustomer,
    PrdProduct
)
from schemas import QuoteCreate, QuoteItemCreate
from utils.number_generator import NumberGenerator

def create_quote(db: Session, quote: QuoteCreate) -> QoQuote:
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == quote.customer_id).first()
    if not customer:
        raise ValueError("客户不存在")
    
    quote_no = f"Q{customer.customer_code}{datetime.now().strftime('%y%m%d')}001"
    
    total_amount = sum(item.quantity * item.unit_price for item in quote.items)
    
    db_quote = QoQuote(
        quote_no=quote_no,
        dept_id=quote.dept_id,
        customer_id=quote.customer_id,
        total_amount=total_amount,
        currency=quote.currency,
        valid_until=quote.valid_until,
        status=1
    )
    
    db.add(db_quote)
    db.commit()
    db.refresh(db_quote)
    
    for item in quote.items:
        db_item = QoQuoteItem(
            quote_id=db_quote.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.quantity * item.unit_price,
            remark=item.remark
        )
        db.add(db_item)
    
    db.commit()
    db.refresh(db_quote)
    
    return db_quote

def get_quote(db: Session, quote_id: int) -> QoQuote:
    return db.query(QoQuote).filter(QoQuote.id == quote_id).first()

def get_quotes(db: Session, skip: int = 0, limit: int = 100, status: int = None, customer_id: int = None):
    query = db.query(QoQuote)
    if status is not None:
        query = query.filter(QoQuote.status == status)
    if customer_id is not None:
        query = query.filter(QoQuote.customer_id == customer_id)
    return query.offset(skip).limit(limit).all()

def get_price_history_by_customer_product(db: Session, customer_id: int, product_id: int):
    return db.query(PiPriceHistory).filter(
        PiPriceHistory.customer_id == customer_id,
        PiPriceHistory.product_id == product_id
    ).order_by(PiPriceHistory.created_at.desc()).first()

def convert_quote_to_pi(db: Session, quote_id: int):
    quote = get_quote(db, quote_id)
    if not quote:
        raise ValueError("报价单不存在")
    
    from crud.pi import create_pi_invoice
    from schemas.pi import PIInvoiceCreate, PIInvoiceItemCreate, PaymentStageCreate
    
    items = []
    for item in quote.items:
        items.append(PIInvoiceItemCreate(
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            remark=item.remark
        ))
    
    pi_create = PIInvoiceCreate(
        dept_id=quote.dept_id,
        customer_id=quote.customer_id,
        currency=quote.currency,
        items=items,
        payment_stages=[
            PaymentStageCreate(
                stage_type='deposit',
                stage_no=1,
                amount=quote.total_amount * 0.3,
                due_date=datetime.now() + timedelta(days=7)
            ),
            PaymentStageCreate(
                stage_type='balance',
                stage_no=2,
                amount=quote.total_amount * 0.7,
                due_date=datetime.now() + timedelta(days=30)
            )
        ]
    )
    
    pi = create_pi_invoice(db, pi_create)
    
    quote.status = 2
    quote.converted_pi_id = pi.id
    db.commit()
    
    return pi

def update_quote_status(db: Session, quote_id: int, status: int) -> QoQuote:
    db_quote = get_quote(db, quote_id)
    if not db_quote:
        return None
    
    db_quote.status = status
    db.commit()
    db.refresh(db_quote)
    return db_quote
