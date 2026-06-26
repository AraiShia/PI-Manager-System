from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from backend.crud.pending_shipment import (
    add_to_pending_queue,
    get_pending_items,
    remove_from_pending,
    confirm_pending_items
)

router = APIRouter(prefix="/api/pending-shipment", tags=["待出货队列"])


class AddPendingRequest(BaseModel):
    pi_item_ids: List[int]
    user_id: str


class ConfirmRequest(BaseModel):
    item_ids: List[int]


@router.post("")
def add_to_queue(req: AddPendingRequest, db: Session = Depends(get_db)):
    """添加产品到待出货队列"""
    items = add_to_pending_queue(db, req.pi_item_ids, req.user_id)
    return {"success": True, "count": len(items)}


@router.get("")
def list_pending(status: Optional[int] = None, db: Session = Depends(get_db)):
    """获取待出货队列列表"""
    items = get_pending_items(db, status)
    return items


@router.delete("/{item_id}")
def remove_item(item_id: int, db: Session = Depends(get_db)):
    """从待出货队列移除"""
    success = remove_from_pending(db, item_id)
    return {"success": success}


@router.post("/confirm")
def confirm_items(req: ConfirmRequest, db: Session = Depends(get_db)):
    """确认待出货项"""
    count = confirm_pending_items(db, req.item_ids)
    return {"success": True, "confirmed_count": count}
