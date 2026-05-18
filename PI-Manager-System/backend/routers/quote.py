from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from app.database import get_db
from models import CrmCustomer
from crud.quote import (
    create_quote, get_quote, get_quotes, get_quote_with_items,
    convert_quote_to_pi, get_price_history_by_customer_product,
    get_latest_price_by_customer_product, get_customer_products_with_prices,
    update_quote, update_quote_status, delete_quote
)
from schemas.quote import QuoteCreate, QuoteUpdate, QuoteResponse

router = APIRouter(prefix="/api/quotes", tags=["报价单管理"])


# ===== 固定路径路由必须在动态路径 /{quote_id} 之前 =====

@router.get("/customer/{customer_id}/products")
def get_customer_products_api(customer_id: int, db: Session = Depends(get_db)):
    """获取该客户所有采购过的产品及其最后一次采购价格"""
    return get_customer_products_with_prices(db, customer_id)


@router.get("/customer/{customer_id}/product/{product_id}/price")
def get_latest_price_api(customer_id: int, product_id: int, db: Session = Depends(get_db)):
    """获取客户采购该产品的最后一次价格"""
    return get_latest_price_by_customer_product(db, customer_id, product_id)


@router.get("/price-history")
def get_price_history(customer_id: int, product_id: int, db: Session = Depends(get_db)):
    return get_price_history_by_customer_product(db, customer_id, product_id)


# ===== CRUD 路由 =====

@router.post("/")
def create_quote_api(quote: QuoteCreate, db: Session = Depends(get_db)):
    try:
        result = create_quote(db, quote)
        customer = db.query(CrmCustomer).filter(CrmCustomer.id == result.customer_id).first()
        return {
            "id": result.id,
            "quote_no": result.quote_no,
            "dept_id": result.dept_id,
            "customer_id": result.customer_id,
            "customer_name": customer.customer_name if customer else None,
            "currency": result.currency,
            "total_amount": float(result.total_amount) if result.total_amount else 0,
            "valid_until": result.valid_until.isoformat()[:10] if result.valid_until else None,
            "status": result.status,
            "remark": result.remark,
            "created_at": result.created_at.isoformat() if result.created_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
def read_quotes(skip: int = 0, limit: int = 100, status: int = None, customer_id: int = None, db: Session = Depends(get_db)):
    quotes = get_quotes(db, skip=skip, limit=limit, status=status, customer_id=customer_id)
    result = []
    for q in quotes:
        customer = db.query(CrmCustomer).filter(CrmCustomer.id == q.customer_id).first()
        result.append({
            "id": q.id,
            "quote_no": q.quote_no,
            "dept_id": q.dept_id,
            "customer_id": q.customer_id,
            "customer_name": customer.customer_name if customer else None,
            "currency": q.currency,
            "total_amount": float(q.total_amount) if q.total_amount else 0,
            "valid_until": q.valid_until.isoformat()[:10] if q.valid_until else None,
            "status": q.status,
            "remark": q.remark,
            "created_at": q.created_at.isoformat() if q.created_at else None
        })
    return result


@router.get("/{quote_id}")
def read_quote(quote_id: int, db: Session = Depends(get_db)):
    quote = get_quote_with_items(db, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="报价单不存在")
    return quote


@router.put("/{quote_id}")
def update_quote_api(quote_id: int, quote_data: dict, db: Session = Depends(get_db)):
    try:
        return update_quote(db, quote_id, quote_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch-delete")
def batch_delete_quotes_api(quote_ids: List[int], db: Session = Depends(get_db)):
    """批量删除报价单"""
    deleted = 0
    errors = []
    for quote_id in quote_ids:
        try:
            delete_quote(db, quote_id)
            deleted += 1
        except ValueError as e:
            errors.append(f"ID {quote_id}: {str(e)}")
    return {"deleted": deleted, "total": len(quote_ids), "errors": errors}


@router.delete("/{quote_id}")
def delete_quote_api(quote_id: int, db: Session = Depends(get_db)):
    try:
        delete_quote(db, quote_id)
        return {"message": "报价单已删除"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{quote_id}/convert")
def convert_quote_api(quote_id: int, db: Session = Depends(get_db)):
    try:
        pi = convert_quote_to_pi(db, quote_id)
        return {"message": "报价单已转为PI", "pi_id": pi.id, "pi_no": pi.pi_no}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{quote_id}/status")
def update_quote_status_api(quote_id: int, status: int, db: Session = Depends(get_db)):
    db_quote = update_quote_status(db, quote_id, status)
    if db_quote is None:
        raise HTTPException(status_code=404, detail="报价单不存在")
    return {"message": "状态已更新", "status": db_quote.status}
