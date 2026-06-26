from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil

from app.database import get_db
from crud import order_file as order_file_crud
from schemas.order_file import OrderFileCreate, OrderFileResponse

router = APIRouter(prefix="/api/order-files", tags=["订单文件"])

ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.xls', '.xlsx'}

# 获取 backend 目录的绝对路径
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_BASE_DIR = os.path.join(BACKEND_DIR, "uploads", "order_files")


@router.post("/upload/{pi_id}", response_model=OrderFileResponse)
async def upload_file(
    pi_id: int,
    file_type: str = Query(..., description="文件类型: contract, invoice, customs"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。支持的格式: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    upload_dir = os.path.join(UPLOAD_BASE_DIR, str(pi_id))
    os.makedirs(upload_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, unique_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)

    file_data = OrderFileCreate(
        pi_id=pi_id,
        file_type=file_type,
        original_name=file.filename,
        stored_name=unique_name,
        file_path=file_path,
        file_size=file_size,
        file_ext=ext
    )
    return order_file_crud.create_order_file(db, file_data)


@router.get("/{pi_id}", response_model=List[OrderFileResponse])
def get_files(
    pi_id: int,
    file_type: Optional[str] = Query(None, description="文件类型筛选"),
    db: Session = Depends(get_db)
):
    return order_file_crud.get_order_files(db, pi_id, file_type)


@router.get("/file/{file_id}", response_model=OrderFileResponse)
def get_file(file_id: int, db: Session = Depends(get_db)):
    db_file = order_file_crud.get_order_file_by_id(db, file_id)
    if not db_file:
        raise HTTPException(status_code=404, detail="文件不存在")
    return db_file


@router.delete("/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    success = order_file_crud.delete_order_file(db, file_id)
    if not success:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"message": "删除成功"}


@router.get("/download/{file_id}")
def download_file(file_id: int, db: Session = Depends(get_db)):
    db_file = order_file_crud.get_order_file_by_id(db, file_id)
    if not db_file:
        raise HTTPException(status_code=404, detail="文件不存在")

    if not os.path.exists(db_file.file_path):
        raise HTTPException(status_code=404, detail="文件已丢失")

    from fastapi.responses import FileResponse
    return FileResponse(
        path=db_file.file_path,
        filename=db_file.original_name,
        media_type="application/octet-stream"
    )
