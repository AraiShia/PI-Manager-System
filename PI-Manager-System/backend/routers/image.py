from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
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
async def upload_image(product_id: int = None, files: list[UploadFile] = File(None), db: Session = Depends(get_db)):
    """
    上传图片，可以是单张或多张
    """
    uploaded_files = []
    
    print(f"DEBUG - 接收到图片上传请求")
    print(f"DEBUG - product_id: {product_id}")
    print(f"DEBUG - files: {files}")
    print(f"DEBUG - files类型: {type(files)}")
    
    if not files:
        print(f"DEBUG - 文件列表为空")
        raise HTTPException(status_code=400, detail="没有上传任何文件")
    
    print(f"DEBUG - 文件数量: {len(files)}")
    
    for file in files:
        # 验证文件类型
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.filename}")
        
        # 生成唯一文件名
        ext = os.path.splitext(file.filename)[1]
        filename = f"{uuid.uuid4()}{ext}"
        filepath = os.path.join(IMAGE_DIR, filename)
        
        # 保存文件
        with open(filepath, "wb") as buffer:
            buffer.write(await file.read())
        
        # 构建URL
        file_url = f"http://localhost:8000/images/{filename}"
        uploaded_files.append(file_url)
        
        # 如果指定了产品ID，关联图片到产品
        if product_id:
            product = db.query(PrdProduct).filter(PrdProduct.id == product_id).first()
            if not product:
                raise HTTPException(status_code=404, detail="产品不存在")
            
            # 创建图片记录
            image = PrdProductImage(
                product_id=product_id,
                image_url=file_url,
                image_type=1,
                sort_order=0
            )
            db.add(image)
            
            # 如果产品没有默认图片，设置为第一张
            if not product.default_image_url:
                product.default_image_url = file_url
        
    if product_id:
        db.commit()
    
    return {"message": "图片上传成功", "files": uploaded_files}

@router.post("/{product_id}/default")
async def set_default_image(
    product_id: int, 
    image_url: str = Body(..., embed=True), 
    db: Session = Depends(get_db)
):
    """
    设置产品默认图片
    """
    product = db.query(PrdProduct).filter(PrdProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    
    product.default_image_url = image_url
    db.commit()
    db.refresh(product)
    
    return {"message": "默认图片设置成功", "product": product}

@router.get("/images/{filename}")
async def get_image(filename: str):
    """
    获取图片
    """
    filepath = os.path.join(IMAGE_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="图片不存在")
    
    return FileResponse(filepath)

@router.get("/{product_id}")
async def get_product_images(product_id: int, db: Session = Depends(get_db)):
    """
    获取产品的所有图片
    """
    images = db.query(PrdProductImage).filter(PrdProductImage.product_id == product_id).all()
    return {"images": [{"id": img.id, "url": img.image_url, "type": img.image_type} for img in images]}

@router.delete("/{image_id}")
async def delete_image(image_id: int, db: Session = Depends(get_db)):
    """
    删除图片
    """
    image = db.query(PrdProductImage).filter(PrdProductImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    # 删除文件
    filename = os.path.basename(image.image_url)
    filepath = os.path.join(IMAGE_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    
    db.delete(image)
    db.commit()
    
    return {"message": "图片删除成功"}
