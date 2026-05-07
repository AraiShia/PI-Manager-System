from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from crud.pi import (
    create_pi_invoice, get_pi_invoice, get_pi_invoices, update_pi_status, get_price_history,
    update_pi_invoice
)
from schemas.pi import PIInvoiceCreate, PIInvoiceResponse, PIInvoiceUpdate

router = APIRouter(prefix="/api/pi", tags=["PI管理"])

@router.post("/", response_model=PIInvoiceResponse)
def create_pi_api(pi: PIInvoiceCreate, db: Session = Depends(get_db)):
    try:
        return create_pi_invoice(db, pi)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[PIInvoiceResponse])
def read_pi_list(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_pi_invoices(db, skip=skip, limit=limit)

@router.get("/{pi_id}", response_model=PIInvoiceResponse)
def read_pi(pi_id: int, db: Session = Depends(get_db)):
    db_pi = get_pi_invoice(db, pi_id)
    if db_pi is None:
        raise HTTPException(status_code=404, detail="PI单不存在")
    return db_pi

@router.put("/{pi_id}", response_model=PIInvoiceResponse)
def update_pi_api(pi_id: int, pi_update: PIInvoiceUpdate, db: Session = Depends(get_db)):
    try:
        db_pi = update_pi_invoice(db, pi_id, pi_update)
        if db_pi is None:
            raise HTTPException(status_code=404, detail="PI单不存在")
        return db_pi
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/price-history/{customer_id}/{product_id}")
def read_price_history(customer_id: int, product_id: int, db: Session = Depends(get_db)):
    history = get_price_history(db, customer_id, product_id)
    if history is None:
        return {"message": "暂无历史价格记录"}
    return {
        "unit_price": history.unit_price,
        "remark": history.remark,
        "created_at": history.created_at
    }
