"""
客户回复API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from schemas.customer_reply import CustomerReplyCreate, CustomerReplyUpdate, CustomerReplyResponse
from crud.customer_reply import (
    get_customer_replies, get_customer_replies_by_pi, get_latest_reply_by_pi,
    get_customer_replies_by_customer, get_customer_reply,
    create_customer_reply, update_customer_reply, delete_customer_reply
)

router = APIRouter(prefix="/api/customer-replies", tags=["客户回复"])


@router.get("", response_model=List[CustomerReplyResponse])
def get_all_replies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取所有客户回复"""
    return get_customer_replies(db, skip=skip, limit=limit)


@router.get("/pi/{pi_id}", response_model=List[CustomerReplyResponse])
def get_replies_by_pi(pi_id: int, db: Session = Depends(get_db)):
    """获取某PI的所有客户回复"""
    return get_customer_replies_by_pi(db, pi_id)


@router.get("/pi/{pi_id}/latest", response_model=Optional[CustomerReplyResponse])
def get_latest_reply(pi_id: int, db: Session = Depends(get_db)):
    """获取某PI的最新客户回复"""
    return get_latest_reply_by_pi(db, pi_id)


@router.get("/customer/{customer_id}", response_model=List[CustomerReplyResponse])
def get_replies_by_customer(customer_id: int, db: Session = Depends(get_db)):
    """获取某客户的所有回复"""
    return get_customer_replies_by_customer(db, customer_id)


@router.post("", response_model=CustomerReplyResponse)
def create_reply(reply: CustomerReplyCreate, db: Session = Depends(get_db)):
    """新增客户回复"""
    return create_customer_reply(db, reply)


@router.put("/{reply_id}", response_model=CustomerReplyResponse)
def update_reply(reply_id: int, reply: CustomerReplyUpdate, db: Session = Depends(get_db)):
    """更新客户回复"""
    db_reply = update_customer_reply(db, reply_id, reply)
    if not db_reply:
        raise HTTPException(status_code=404, detail="回复不存在")
    return db_reply


@router.delete("/{reply_id}")
def delete_reply(reply_id: int, db: Session = Depends(get_db)):
    """删除客户回复"""
    success = delete_customer_reply(db, reply_id)
    if not success:
        raise HTTPException(status_code=404, detail="回复不存在")
    return {"message": "删除成功"}
