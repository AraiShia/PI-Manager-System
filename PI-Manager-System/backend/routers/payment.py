from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from crud.payment import (
    create_customer_payment, get_customer_payments, get_customer_payment, update_customer_payment,
    create_supplier_payment, get_supplier_payments, get_supplier_payment, update_supplier_payment,
    get_supplier_payment_stages, update_supplier_payment_stage,
    get_unmatched_payments
)
from schemas.payment import (
    CustomerPaymentCreate, CustomerPaymentUpdate, CustomerPaymentResponse,
    SupplierPaymentCreate, SupplierPaymentUpdate, SupplierPaymentResponse,
    SupplierPaymentStageCreate
)

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

@router.get("/receivables/by-pi/{pi_id}", response_model=list[CustomerPaymentResponse])
def read_customer_payments_by_pi(pi_id: int, db: Session = Depends(get_db)):
    """按 PI 获取客户付款记录"""
    return get_customer_payments(db, pi_id=pi_id)

@router.get("/receivables/{payment_id}", response_model=CustomerPaymentResponse)
def read_customer_payment(payment_id: int, db: Session = Depends(get_db)):
    db_payment = get_customer_payment(db, payment_id)
    if db_payment is None:
        raise HTTPException(status_code=404, detail="收款记录不存在")
    return db_payment

@router.put("/receivables/{payment_id}", response_model=CustomerPaymentResponse)
def update_customer_payment_api(payment_id: int, payment_update: CustomerPaymentUpdate, db: Session = Depends(get_db)):
    db_payment = update_customer_payment(db, payment_id, payment_update)
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
def read_supplier_payments(skip: int = 0, limit: int = 100, po_id: int = None, supplier_id: int = None, db: Session = Depends(get_db)):
    payments = get_supplier_payments(db, skip=skip, limit=limit, po_id=po_id, supplier_id=supplier_id)
    return [_serialize_supplier_payment(p) for p in payments]

@router.get("/payables/by-pi/{pi_id}", response_model=list[dict])
def read_supplier_payments_by_pi(pi_id: int, db: Session = Depends(get_db)):
    """按 PI 获取供应商付款记录"""
    from crud.payment import get_supplier_payments_by_pi
    payments = get_supplier_payments_by_pi(db, pi_id)
    return [_serialize_supplier_payment(p) for p in payments]

@router.get("/payables/{payment_id}", response_model=SupplierPaymentResponse)
def read_supplier_payment(payment_id: int, db: Session = Depends(get_db)):
    db_payment = get_supplier_payment(db, payment_id)
    if db_payment is None:
        raise HTTPException(status_code=404, detail="付款记录不存在")
    return _serialize_supplier_payment(db_payment)

def _serialize_supplier_payment(payment):
    """序列化供应商付款，避免懒加载"""
    return {
        "id": payment.id,
        "dept_id": payment.dept_id,
        "payment_no": payment.payment_no,
        "po_id": payment.po_id,
        "supplier_id": payment.supplier_id,
        "total_amount": float(payment.total_amount) if payment.total_amount else 0,
        "paid_amount": float(payment.paid_amount) if payment.paid_amount else 0,
        "unpaid_amount": float(payment.unpaid_amount) if payment.unpaid_amount else 0,
        "status": payment.status or 1,
        "payment_method": payment.payment_method,
        "remark": payment.remark,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
        # 不包含 stages，通过单独接口获取
    }

@router.put("/payables/{payment_id}", response_model=SupplierPaymentResponse)
def update_supplier_payment_api(payment_id: int, payment_update: SupplierPaymentUpdate, db: Session = Depends(get_db)):
    db_payment = update_supplier_payment(db, payment_id, payment_update)
    if db_payment is None:
        raise HTTPException(status_code=404, detail="付款记录不存在")
    return db_payment

@router.get("/payables/{payment_id}/stages")
def read_supplier_payment_stages(payment_id: int, db: Session = Depends(get_db)):
    return get_supplier_payment_stages(db, payment_id)

@router.post("/payables/stages/{stage_id}")
def update_supplier_payment_stage_api(stage_id: int, stage_type: str = None, paid_amount: float = None, db: Session = Depends(get_db)):
    stage = update_supplier_payment_stage(db, stage_id, stage_type, paid_amount)
    if not stage:
        raise HTTPException(status_code=404, detail="付款阶段不存在")
    return stage

@router.get("/unmatched")
def read_unmatched_payments(db: Session = Depends(get_db)):
    return get_unmatched_payments(db)