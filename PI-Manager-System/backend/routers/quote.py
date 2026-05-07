from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from crud.quote import (
    create_quote, get_quote, get_quotes, convert_quote_to_pi, 
    get_price_history_by_customer_product, update_quote_status
)
from schemas.quote import QuoteCreate, QuoteResponse

router = APIRouter(prefix="/api/quotes", tags=["报价单管理"])

@router.post("/", response_model=QuoteResponse)
def create_quote_api(quote: QuoteCreate, db: Session = Depends(get_db)):
    try:
        return create_quote(db, quote)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[QuoteResponse])
def read_quotes(skip: int = 0, limit: int = 100, status: int = None, customer_id: int = None, db: Session = Depends(get_db)):
    return get_quotes(db, skip=skip, limit=limit, status=status, customer_id=customer_id)

@router.get("/{quote_id}", response_model=QuoteResponse)
def read_quote(quote_id: int, db: Session = Depends(get_db)):
    db_quote = get_quote(db, quote_id)
    if db_quote is None:
        raise HTTPException(status_code=404, detail="报价单不存在")
    return db_quote

@router.post("/{quote_id}/convert")
def convert_quote_api(quote_id: int, db: Session = Depends(get_db)):
    try:
        pi = convert_quote_to_pi(db, quote_id)
        return {"message": "报价单已转为PI", "pi": pi}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/price-history")
def get_price_history(customer_id: int, product_id: int, db: Session = Depends(get_db)):
    return get_price_history_by_customer_product(db, customer_id, product_id)

@router.post("/{quote_id}/status")
def update_quote_status_api(quote_id: int, status: int, db: Session = Depends(get_db)):
    db_quote = update_quote_status(db, quote_id, status)
    if db_quote is None:
        raise HTTPException(status_code=404, detail="报价单不存在")
    return {"message": "状态已更新", "quote": db_quote}
