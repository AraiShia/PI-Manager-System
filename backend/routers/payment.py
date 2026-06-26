from fastapi import APIRouter, Depends, HTTPException, Query
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

@router.get("/receivables")
def read_customer_payments(
    customer_id: int = Query(None, description="客户ID过滤"),
    pi_no: str = Query(None, description="PI号模糊查询"),
    only_unpaid: bool = Query(False, description="仅显示未结清 PI"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    客户付款列表（spec #45：PI号 / 客户名称 / 付款1-3 / 未付款 / 查看水单）

    每一行 = 一张 PI（按 PI 聚合前 3 笔实收）

    列说明：
        pi_no, customer_name, total_amount, paid_amount, unpaid_amount,
        payment1/2/3 (amount + actual_amount + arrival_date + water_image + receipt_no + payment_id),
        latest_water_image, latest_receipt_no, receipt_count, pi_status

    单笔水单查看/编辑请使用：
        GET    /api/payments/receivables/by-pi/{pi_id}   按 PI 取所有水单
        GET    /api/payments/receivables/{payment_id}    单条详情
        PUT    /api/payments/receivables/{payment_id}    编辑水单
    """
    from models import ArCustomerPayment, PiProformaInvoice
    from sqlalchemy import func

    pi_q = db.query(PiProformaInvoice)
    if customer_id is not None:
        pi_q = pi_q.filter(PiProformaInvoice.customer_id == customer_id)
    if pi_no:
        pi_q = pi_q.filter(PiProformaInvoice.pi_no.ilike(f"%{pi_no}%"))

    pis = pi_q.order_by(PiProformaInvoice.id.desc()).all()
    pi_ids = [p.id for p in pis]

    receipts_by_pi: dict = {pid: [] for pid in pi_ids}
    if pi_ids:
        rcpts = (
            db.query(ArCustomerPayment)
            .filter(ArCustomerPayment.pi_id.in_(pi_ids))
            .order_by(ArCustomerPayment.payment_date.asc(), ArCustomerPayment.id.asc())
            .all()
        )
        for r in rcpts:
            receipts_by_pi.setdefault(r.pi_id, []).append(r)

    total_paid_sum = dict(
        db.query(ArCustomerPayment.pi_id, func.coalesce(func.sum(ArCustomerPayment.actual_amount), 0))
        .filter(ArCustomerPayment.pi_id.in_(pi_ids))
        .group_by(ArCustomerPayment.pi_id)
        .all()
    ) if pi_ids else {}

    items = []
    for pi in pis:
        rcpts = receipts_by_pi.get(pi.id, [])
        paid_total = float(total_paid_sum.get(pi.id, 0) or 0)
        total_amt = float(pi.total_amount or 0)
        unpaid_amt = round(max(total_amt - paid_total, 0.0), 2)

        if only_unpaid and unpaid_amt <= 0:
            continue

        def _slot(idx: int):
            if idx >= len(rcpts):
                return None
            r = rcpts[idx]
            return {
                "amount": float(r.amount or 0),
                "actual_amount": float(r.actual_amount or 0),
                "arrival_date": r.payment_date.isoformat()[:10] if r.payment_date else None,
                "water_image": r.water_image,
                "receipt_no": r.receipt_no,
                "payment_id": r.id,
            }

        latest = rcpts[-1] if rcpts else None
        items.append({
            "pi_id": pi.id,
            "pi_no": pi.pi_no,
            "customer_id": pi.customer_id,
            "customer_name": pi.customer.customer_name if pi.customer else None,
            "total_amount": round(total_amt, 2),
            "paid_amount": round(paid_total, 2),
            "unpaid_amount": unpaid_amt,
            "payment1": _slot(0),
            "payment2": _slot(1),
            "payment3": _slot(2),
            "receipt_count": len(rcpts),
            "latest_water_image": latest.water_image if latest else None,
            "latest_receipt_no": latest.receipt_no if latest else None,
            "pi_status": pi.status,
        })

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": items[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

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
