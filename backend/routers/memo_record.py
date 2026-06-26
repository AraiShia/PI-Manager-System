from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from crud import memo_record
from schemas.memo_record import MemoRecordCreate, MemoRecordUpdate, MemoRecordResponse

router = APIRouter(prefix="/api/memos", tags=["备忘录"])


@router.post("/", response_model=MemoRecordResponse)
def create_memo_api(memo: MemoRecordCreate, db: Session = Depends(get_db)):
    return memo_record.create_memo(db, memo)


@router.get("/", response_model=List[MemoRecordResponse])
def get_memos_api(
    entity_type: str = Query(..., description="实体类型"),
    entity_id: int = Query(..., description="实体ID"),
    field_name: Optional[str] = Query(None, description="字段名"),
    db: Session = Depends(get_db)
):
    return memo_record.get_memos(db, entity_type, entity_id, field_name)


@router.get("/{memo_id}", response_model=MemoRecordResponse)
def get_memo_api(memo_id: int, db: Session = Depends(get_db)):
    db_memo = memo_record.get_memo_by_id(db, memo_id)
    if not db_memo:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="备忘录不存在")
    return db_memo


@router.put("/{memo_id}", response_model=MemoRecordResponse)
def update_memo_api(memo_id: int, memo: MemoRecordUpdate, db: Session = Depends(get_db)):
    db_memo = memo_record.update_memo(db, memo_id, memo)
    if not db_memo:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="备忘录不存在")
    return db_memo


@router.delete("/{memo_id}")
def delete_memo_api(memo_id: int, db: Session = Depends(get_db)):
    success = memo_record.delete_memo(db, memo_id)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="备忘录不存在")
    return {"message": "删除成功"}
