from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from crud.payment import (
    create_customer_payment, get_customer_payments, get_customer_payment,
    create_supplier_payment, get_supplier_payments, get_supplier_payment,
    get_unmatched_payments
)
from schemas.payment import CustomerPaymentCreate, SupplierPaymentCreate, CustomerPaymentResponse, SupplierPaymentResponse

router = APIRouter(prefix="/api/payments", tags=["收付款管理"])

@router.post("/receivables", response_model=CustomerPaymentResponse)
def create_customer_payment_api(payment: CustomerPaymentCreate, db: Session = Depends(get_db)):
    try:
        return create_customer_payment(db, payment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/receivables", response_model=list[CustomerPaymentResponse])
def read_customer_payments(skip: int = 0, limit: int = 100, pi_id: int = None, customer_id: int = None, db: Session = Depends(get_db)):
    return get_customer_payments(db, skip=skip, limit=limit, pi_id=pi_id, customer_id=customer_id)

@router.get("/receivables/{payment_id}", response_model=CustomerPaymentResponse)
def read_customer_payment(payment_id: int, db: Session = Depends(get_db)):
    db_payment = get_customer_payment(db, payment_id)
    if db_payment is None:
        raise HTTPException(status_code=404, detail="收款记录不存在")
    return db_payment

@router.post("/payables", response_model=SupplierPaymentResponse)
def create_supplier_payment_api(payment: SupplierPaymentCreate, db: Session = Depends(get_db)):
    try:
        return create_supplier_payment(db, payment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/payables", response_model=list[SupplierPaymentResponse])
def read_supplier_payments(skip: int = 0, limit: int = 100, purchase_order_id: int = None, supplier_id: int = None, db: Session = Depends(get_db)):
    return get_supplier_payments(db, skip=skip, limit=limit, purchase_order_id=purchase_order_id, supplier_id=supplier_id)

@router.get("/payables/{payment_id}", response_model=SupplierPaymentResponse)
def read_supplier_payment(payment_id: int, db: Session = Depends(get_db)):
    db_payment = get_supplier_payment(db, payment_id)
    if db_payment is None:
        raise HTTPException(status_code=404, detail="付款记录不存在")
    return db_payment

@router.get("/unmatched")
def read_unmatched_payments(db: Session = Depends(get_db)):
    return get_unmatched_payments(db)
