from sqlalchemy.orm import Session
from models.memo_record import MemoRecord
from schemas.memo_record import MemoRecordCreate, MemoRecordUpdate
from datetime import datetime


def create_memo(db: Session, memo: MemoRecordCreate, user_id: int = None) -> MemoRecord:
    db_memo = MemoRecord(
        entity_type=memo.entity_type,
        entity_id=memo.entity_id,
        field_name=memo.field_name,
        content=memo.content,
        created_by=user_id
    )
    db.add(db_memo)
    db.commit()
    db.refresh(db_memo)
    return db_memo


def get_memos(db: Session, entity_type: str, entity_id: int, field_name: str = None):
    query = db.query(MemoRecord).filter(
        MemoRecord.entity_type == entity_type,
        MemoRecord.entity_id == entity_id
    )
    if field_name:
        query = query.filter(MemoRecord.field_name == field_name)
    return query.order_by(MemoRecord.created_at.desc()).all()


def get_memo_by_id(db: Session, memo_id: int) -> MemoRecord:
    return db.query(MemoRecord).filter(MemoRecord.id == memo_id).first()


def update_memo(db: Session, memo_id: int, memo: MemoRecordUpdate) -> MemoRecord:
    db_memo = db.query(MemoRecord).filter(MemoRecord.id == memo_id).first()
    if db_memo and memo.content is not None:
        db_memo.content = memo.content
        db_memo.updated_at = datetime.now()
        db.commit()
        db.refresh(db_memo)
    return db_memo


def delete_memo(db: Session, memo_id: int) -> bool:
    db_memo = db.query(MemoRecord).filter(MemoRecord.id == memo_id).first()
    if db_memo:
        db.delete(db_memo)
        db.commit()
        return True
    return False
