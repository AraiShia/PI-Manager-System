from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from crud.product import (
    create_product, get_product, get_products, update_product, delete_product, 
    search_products, get_product_images, toggle_product_status, add_product_image, delete_product_image,
    confirm_temporary_product
)
from schemas.product import ProductCreate, ProductUpdate, ProductResponse, ProductImageResponse
from routers.auth import get_current_user, get_current_admin, get_current_user_optional
from models.user import SysUser
from functools import lru_cache
from datetime import datetime

router = APIRouter(prefix="/api/products", tags=["产品管理"])

@router.post("/", response_model=ProductResponse)
def create_product_api(product: ProductCreate, db: Session = Depends(get_db)):
    return create_product(db, product)

@router.get("/", response_model=list[ProductResponse])
def read_products(skip: int = 0, limit: int = 100, status: int = None, db: Session = Depends(get_db)):
    return get_products(db, skip=skip, limit=limit, status=status)

@router.get("/search", response_model=list[ProductResponse])
def search_products_api(keyword: str = "", category_id: int = None, category_code: str = None, status: int = None, customer_id: int = None, db: Session = Depends(get_db)):
    return search_products(db, keyword=keyword, category_id=category_id, category_code=category_code, status=status, customer_id=customer_id)

@router.get("/{product_id}/schemes")
def get_product_schemes(product_id: int, db: Session = Depends(get_db)):
    """获取产品的供应商方案列表（从PrdProductSupplier表读取，与产品管理同步）"""
    from models import PrdProduct, PrdProductSupplier, SupSupplier, CrmCustomer
    
    # 从PrdProductSupplier表读取（和产品管理使用同一数据源）
    result = db.query(
        PrdProductSupplier,
        SupSupplier.supplier_code,
        SupSupplier.supplier_name,
        CrmCustomer.customer_code,
        CrmCustomer.customer_name,
    ).join(
        SupSupplier, PrdProductSupplier.supplier_id == SupSupplier.id
    ).outerjoin(
        CrmCustomer, PrdProductSupplier.customer_id == CrmCustomer.id
    ).filter(
        PrdProductSupplier.product_id == product_id
    ).all()
    
    schemes = []
    for ps, sc, sn, cc, cn in result:
        schemes.append({
            "id": ps.id,
            "product_id": ps.product_id,
            "supplier_id": ps.supplier_id,
            "supplier_name": sn or "",
            "supplier_code": sc or "",
            "customer_id": ps.customer_id,
            "customer_name": cn or "通用",
            "factory_code": ps.factory_code or "",
            "purchase_price": float(ps.purchase_price) if ps.purchase_price else 0,
            "currency": ps.currency or "CNY",
            "units_per_carton": ps.units_per_carton,
            "carton_length_cm": float(ps.carton_length_cm) if ps.carton_length_cm else 0,
            "carton_width_cm": float(ps.carton_width_cm) if ps.carton_width_cm else 0,
            "carton_height_cm": float(ps.carton_height_cm) if ps.carton_height_cm else 0,
            "gross_weight_kg": float(ps.gross_weight_kg) if ps.gross_weight_kg else 0,
            "moq": ps.moq,
            "lead_time_days": ps.lead_time_days,
            "remark": ps.remark or "",
            "is_default": ps.is_default or False,
        })
    
    # 如果没有供应商方案，回退到产品表的价格作为默认方案
    if not schemes:
        product = db.query(PrdProduct).filter(PrdProduct.id == product_id).first()
        if product:
            schemes.append({
                "id": 0,
                "product_id": product_id,
                "supplier_id": product.supplier_id or 0,
                "supplier_name": "默认（未设置供应商方案）",
                "supplier_code": "",
                "customer_id": None,
                "customer_name": "通用",
                "factory_code": product.factory_code or "",
                "purchase_price": float(product.exw_price_incl) if product.exw_price_incl else 0,
                "currency": "CNY",
                "units_per_carton": product.units_per_carton,
                "carton_length_cm": float(product.carton_length_cm) if product.carton_length_cm else 0,
                "carton_width_cm": float(product.carton_width_cm) if product.carton_width_cm else 0,
                "carton_height_cm": float(product.carton_height_cm) if product.carton_height_cm else 0,
                "gross_weight_kg": float(product.gross_weight_kg) if product.gross_weight_kg else 0,
                "moq": None,
                "lead_time_days": None,
                "remark": "从产品基本信息读取",
                "is_default": True,
            })
    
    return schemes

@router.post("/{product_id}/schemes")
def create_product_scheme(product_id: int, scheme: dict, db: Session = Depends(get_db)):
    """为产品创建供应商方案（写入PrdProductSupplier表，与产品管理同步）"""
    from models import PrdProductSupplier
    
    db_scheme = PrdProductSupplier(
        product_id=product_id,
        supplier_id=scheme.get('supplier_id'),
        customer_id=scheme.get('customer_id'),
        factory_code=scheme.get('factory_code') or '',
        purchase_price=scheme.get('purchase_price') or scheme.get('exw_price_incl'),
        currency=scheme.get('currency', 'CNY'),
        units_per_carton=scheme.get('units_per_carton'),
        carton_length_cm=scheme.get('carton_length_cm'),
        carton_width_cm=scheme.get('carton_width_cm'),
        carton_height_cm=scheme.get('carton_height_cm'),
        gross_weight_kg=scheme.get('gross_weight_kg'),
        moq=scheme.get('moq'),
        lead_time_days=scheme.get('lead_time_days'),
        remark=scheme.get('remark', ''),
        is_default=scheme.get('is_default', False),
    )
    db.add(db_scheme)
    db.commit()
    db.refresh(db_scheme)
    return {"id": db_scheme.id, "success": True}

@router.delete("/{product_id}/schemes/{scheme_id}")
def delete_product_scheme(product_id: int, scheme_id: int, db: Session = Depends(get_db)):
    """删除供应商方案"""
    from models import PrdProductSupplier
    db_scheme = db.query(PrdProductSupplier).filter(
        PrdProductSupplier.id == scheme_id,
        PrdProductSupplier.product_id == product_id
    ).first()
    if db_scheme:
        db.delete(db_scheme)
        db.commit()
    return {"success": True}

@router.get("/{product_id}", response_model=ProductResponse)
def read_product(product_id: int, db: Session = Depends(get_db)):
    db_product = get_product(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="产品不存在")
    return db_product

@router.put("/{product_id}", response_model=ProductResponse)
def update_product_api(
    product_id: int, 
    product: ProductUpdate, 
    current_user: Optional[SysUser] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    db_product = get_product(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="产品不存在")
    
    # 检查权限：如果产品已导入且当前用户不是管理员，则拒绝修改
    if db_product.is_imported == 1:
        # 如果没有登录或者用户不是管理员，则拒绝修改
        if not current_user or not current_user.is_admin:
            raise HTTPException(
                status_code=403, 
                detail="产品已确认导入，只有管理员可以修改"
            )
    
    db_product = update_product(db, product_id, product)
    return db_product

@router.patch("/{product_id}/status", response_model=ProductResponse)
def toggle_product_status_api(product_id: int, db: Session = Depends(get_db)):
    db_product = toggle_product_status(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="产品不存在")
    return db_product

@router.delete("/{product_id}")
def delete_product_api(product_id: int, db: Session = Depends(get_db)):
    result = delete_product(db, product_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return {"message": result["message"]}

@router.post("/{product_id}/confirm")
def confirm_product(
    product_id: int, 
    full_data: dict,
    db: Session = Depends(get_db)
):
    """将临时产品转为正式产品
    
    Args:
        product_id: 产品ID
        full_data: 完整的产品数据字典
        
    Returns:
        200: 转正成功，返回更新后的产品信息
        404: 产品不存在
        409: 产品已被其他用户转正
    """
    try:
        product = confirm_temporary_product(db, product_id, full_data)
        
        return {
            "id": product.id,
            "product_code": product.product_code,
            "is_temporary": product.is_temporary,
            "detail_desc": product.detail_desc,
            "oe_number": product.oe_number,
            "brand": product.brand,
            "category_id": product.category_id,
            "supplier_id": product.supplier_id,
            "status": product.status
        }
    except ValueError as e:
        error_msg = str(e)
        if "CONFLICT" in error_msg:
            raise HTTPException(status_code=409, detail="该产品已被其他用户转正")
        else:
            raise HTTPException(status_code=404, detail=error_msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail="转正失败，请稍后重试")

@router.get("/{product_id}/images", response_model=list[ProductImageResponse])
def read_product_images(product_id: int, db: Session = Depends(get_db)):
    db_product = get_product(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="产品不存在")
    return get_product_images(db, product_id)

@router.post("/{product_id}/images", response_model=ProductImageResponse)
def add_product_image_api(
    product_id: int, 
    image_type: int = 1, 
    sort_order: int = 0,
    db: Session = Depends(get_db)
):
    db_product = get_product(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="产品不存在")
    
    return add_product_image(db, product_id, f"/api/products/{product_id}/images/placeholder", image_type, sort_order)

@router.delete("/images/{image_id}")
def delete_product_image_api(image_id: int, db: Session = Depends(get_db)):
    success = delete_product_image(db, image_id)
    if not success:
        raise HTTPException(status_code=404, detail="图片不存在")
    return {"message": "图片已删除"}

@router.patch("/{product_id}/confirm-import")
def confirm_import_product(
    product_id: int,
    current_user: Optional[SysUser] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """确认产品导入"""
    print(f"DEBUG - confirm_import_product called for product_id: {product_id}")
    print(f"DEBUG - current_user: {current_user}")
    
    db_product = get_product(db, product_id)
    if db_product is None:
        print(f"DEBUG - Product {product_id} not found")
        raise HTTPException(status_code=404, detail="产品不存在")
    
    if db_product.is_imported == 1:
        print(f"DEBUG - Product {product_id} already imported")
        raise HTTPException(status_code=400, detail="产品已确认导入")
    
    db_product.is_imported = 1
    db_product.imported_at = datetime.now()
    db_product.imported_by = current_user.id if current_user else 1
    db.commit()
    db.refresh(db_product)
    
    print(f"DEBUG - Product {product_id} imported successfully")
    return {"message": "产品导入已确认", "product": db_product}

@router.patch("/{product_id}/cancel-import")
def cancel_import_product(
    product_id: int,
    current_user: Optional[SysUser] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """取消产品导入确认（仅管理员）"""
    print(f"DEBUG - cancel_import_product called for product_id: {product_id}")
    print(f"DEBUG - current_user: {current_user}")
    
    db_product = get_product(db, product_id)
    if db_product is None:
        print(f"DEBUG - Product {product_id} not found")
        raise HTTPException(status_code=404, detail="产品不存在")
    
    if db_product.is_imported == 0:
        print(f"DEBUG - Product {product_id} not imported")
        raise HTTPException(status_code=400, detail="产品未确认导入")
    
    # 检查权限：只有管理员可以取消导入
    if not current_user or not current_user.is_admin:
        print(f"DEBUG - User {current_user} is not admin, access denied")
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    db_product.is_imported = 0
    db_product.imported_at = None
    db_product.imported_by = None
    db.commit()
    db.refresh(db_product)
    
    print(f"DEBUG - Product {product_id} import canceled successfully")
    return {"message": "产品导入确认已取消", "product": db_product}
