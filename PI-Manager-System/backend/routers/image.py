from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from models.product import PrdProduct, PrdProductImage
import os
import uuid
from datetime import datetime

router = APIRouter()

# 图片存储目录
IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(IMAGE_DIR, exist_ok=True)

# 默认图片路径
DEFAULT_IMAGE_URL = "http://localhost:8000/images/default_product.png"


@router.post("/upload")
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    上传图片，单个文件
    """
    print(f"DEBUG - 接收到图片上传请求: {file.filename}")
    
    # 验证文件类型
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.filename}")
    
    # 生成唯一文件名
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(IMAGE_DIR, filename)
    
    # 保存文件
    with open(filepath, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # 构建URL
    file_url = f"http://localhost:8000/images/{filename}"
    
    return {
        "url": file_url,
        "filename": filename,
        "message": "图片上传成功"
    }


@router.post("/upload-multiple")
async def upload_multiple_images(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    """
    上传图片，多个文件
    """
    uploaded_files = []
    
    print(f"DEBUG - 接收到多图片上传请求，数量: {len(files)}")
    
    for file in files:
        # 验证文件类型
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            continue
        
        # 生成唯一文件名
        ext = os.path.splitext(file.filename)[1]
        filename = f"{uuid.uuid4()}{ext}"
        filepath = os.path.join(IMAGE_DIR, filename)
        
        # 保存文件
        with open(filepath, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 构建URL
        file_url = f"http://localhost:8000/images/{filename}"
        uploaded_files.append(file_url)
    
    return {
        "files": uploaded_files,
        "message": f"成功上传 {len(uploaded_files)} 个文件"
    }