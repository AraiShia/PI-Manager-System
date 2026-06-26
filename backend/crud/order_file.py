from sqlalchemy.orm import Session
from models.order_file import OrderFile
from schemas.order_file import OrderFileCreate
import os


def create_order_file(db: Session, file_data: OrderFileCreate, user_id: int = None) -> OrderFile:
    db_file = OrderFile(
        pi_id=file_data.pi_id,
        product_id=file_data.product_id,
        file_type=file_data.file_type,
        original_name=file_data.original_name,
        stored_name=file_data.stored_name,
        file_path=file_data.file_path,
        file_size=file_data.file_size,
        file_ext=file_data.file_ext,
        uploaded_by=user_id
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file


def get_order_files(db: Session, pi_id: int, file_type: str = None):
    query = db.query(OrderFile).filter(OrderFile.pi_id == pi_id)
    if file_type:
        query = query.filter(OrderFile.file_type == file_type)
    return query.order_by(OrderFile.uploaded_at.desc()).all()


def get_order_file_by_id(db: Session, file_id: int) -> OrderFile:
    return db.query(OrderFile).filter(OrderFile.id == file_id).first()


def delete_order_file(db: Session, file_id: int) -> bool:
    db_file = db.query(OrderFile).filter(OrderFile.id == file_id).first()
    if db_file:
        file_path = db_file.file_path
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        db.delete(db_file)
        db.commit()
        return True
    return False
