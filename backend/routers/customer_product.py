"""
客户产品管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List
import json

from app.database import get_db
from crud.customer_product import (
    create_customer_product, get_customer_product, get_customer_products,
    get_customer_products_by_customer, update_customer_product, delete_customer_product,
    get_product_codes, get_product_oes, add_product_code, add_product_oe,
    delete_product_code, delete_product_oe, set_primary_code, set_primary_oe,
    batch_add_codes, batch_add_oes, search_by_oe_number, search_by_code,
    # Phase 2: 临时产品相关
    convert_temporary_to_official, get_temporary_products,
    # 2026-06-16 修复 log.txt 404：完整版转正+更新
    update_and_confirm_temporary,
)
from crud.customer import get_customer as get_customer_by_id
from schemas.customer_product import (
    CustomerProductCreate, CustomerProductUpdate, CustomerProductResponse,
    CustomerProductCodeCreate, CustomerProductCodeResponse,
    CustomerProductOECreate, CustomerProductOEResponse, CustomerProductListResponse,
    BatchImportRequest
)
from tasks.product_cleanup import cleanup_deleted_products

router = APIRouter(prefix="/api/customer-products", tags=["客户产品管理"])


def _build_response(customer_product, db: Session):
    """构建响应数据"""
    # 获取编号列表
    codes = get_product_codes(db, customer_product.id)
    
    # 获取OE号列表
    oes = get_product_oes(db, customer_product.id)
    
    # 获取客户名称
    customer = None
    try:
        customer = get_customer_by_id(db, customer_product.customer_id)
    except:
        pass
    
    # 获取类目名称
    category_name = None
    if customer_product.category_id:
        try:
            from models import PrdProductCategory
            category = db.query(PrdProductCategory).filter(
                PrdProductCategory.code == customer_product.category_id
            ).first()
            if category:
                category_name = category.name
        except:
            pass
        # 2026-06-23 修复：DB 表为空时，fallback 到前端 client/product_categories.py 的硬编码 CATEGORIES
        # （prd_product_category 表被清空后，所有产品的 category_name 都返回 None → 前端产品列表类别列空）
        if not category_name:
            _FALLBACK_CATEGORIES = {
                "C": "汽配件", "F": "办公家具", "B": "百货类",
                "C01": "发动机", "C02": "曲轴", "C03": "刹车片", "C09": "杂项",
                "F01": "椅子类", "F02": "桌子类", "F88": "工程定制",
                "B00": "百货类",
            }
            category_name = _FALLBACK_CATEGORIES.get(customer_product.category_id)
    
    # 构建响应
    primary_code = None
    for code in codes:
        if code.is_primary:
            primary_code = code.product_code
            break
    
    primary_oe = None
    for oe in oes:
        if oe.is_primary:
            primary_oe = oe.oe_number
            break
    
    # 解析副图JSON
    sub_images = []
    if customer_product.sub_images:
        try:
            sub_images = json.loads(customer_product.sub_images)
        except:
            pass
    
    return CustomerProductResponse(
        id=customer_product.id,
        customer_id=customer_product.customer_id,
        system_code=customer_product.system_code,  # ✨新增
        product_name=customer_product.product_name,
        customer_model=customer_product.customer_model,
        color=customer_product.color,
        customer_remark=customer_product.customer_remark,
        category_id=customer_product.category_id,
        category_name=category_name,
        price_usd=float(customer_product.price_usd) if customer_product.price_usd else None,
        price_rmb=float(customer_product.price_rmb) if customer_product.price_rmb else None,
        detail_desc=customer_product.detail_desc,
        brand=customer_product.brand,
        specifications=customer_product.specifications,
        image_url=customer_product.image_url,
        sub_images=sub_images,
        is_active=customer_product.is_active,
        # Phase 2: 临时产品标志
        is_temporary=bool(getattr(customer_product, "is_temporary", False)),
        created_at=customer_product.created_at,
        updated_at=customer_product.updated_at,
        customer_name=customer.customer_name if customer else None,
        code_count=len(codes),
        primary_code=primary_code,
        oe_count=len(oes),
        primary_oe=primary_oe,
        codes=[CustomerProductCodeResponse(
            id=code.id,
            customer_product_id=code.customer_product_id,
            product_code=code.product_code,
            is_primary=code.is_primary,
            remark=code.remark,
            created_at=code.created_at,
        ) for code in codes],
        oes=[CustomerProductOEResponse(
            id=oe.id,
            customer_product_id=oe.customer_product_id,
            oe_number=oe.oe_number,
            is_primary=oe.is_primary,
            remark=oe.remark,
            created_at=oe.created_at,
        ) for oe in oes],
    )


@router.get("", response_model=CustomerProductListResponse)
def list_customer_products(
    customer_id: Optional[int] = Query(None, description="客户ID"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    is_temporary: Optional[bool] = Query(None, description="Phase 2: 是否临时产品（True/False/None全部）"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取客户产品列表（Phase 2: 支持临时/正式产品筛选）"""
    skip = (page - 1) * page_size
    items, total = get_customer_products(
        db,
        customer_id=customer_id,
        search=search,
        skip=skip,
        limit=page_size,
        is_temporary=is_temporary,
    )

    return CustomerProductListResponse(
        items=[_build_response(item, db) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# ============ Phase 2: 临时产品端点 ============

@router.get("/temporary", response_model=List[CustomerProductResponse])
def list_temporary_products(
    customer_id: Optional[int] = Query(None, description="客户ID"),
    db: Session = Depends(get_db),
):
    """获取临时产品列表（Phase 2 新增）"""
    items, _ = get_temporary_products(db, customer_id=customer_id, limit=1000)
    return [_build_response(item, db) for item in items]


@router.post("/temporary", response_model=CustomerProductResponse, status_code=201)
def create_temporary_product(
    data: CustomerProductCreate,
    db: Session = Depends(get_db),
):
    """
    创建临时产品（Phase 2 新增）
    强制 is_temporary=True，单表存储
    """
    # 强制设为临时
    data.is_temporary = True
    customer_product = create_customer_product(db, data)
    return _build_response(customer_product, db)


@router.patch("/{product_id}/convert", response_model=CustomerProductResponse)
def convert_temporary_product_to_official(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    临时产品转正（Phase 2 新增）
    将 is_temporary=False，不创建新记录
    """
    customer_product = convert_temporary_to_official(db, product_id)
    if not customer_product:
        raise HTTPException(status_code=404, detail=f"客户产品 {product_id} 不存在")
    return _build_response(customer_product, db)


@router.post("/{product_id}/confirm", response_model=CustomerProductResponse)
def confirm_temporary_product_endpoint(
    product_id: int,
    full_data: dict,
    db: Session = Depends(get_db),
):
    """2026-06-16 修复 log.txt 404：完整版转正 + 字段更新

    兼容旧 `crud/product.py::confirm_temporary_product`（Phase 5 后 PrdProduct 表已删除）。
    直接更新 PrdCustomerProduct 记录并清除 `is_temporary` 标记。

    Path: POST /api/customer-products/{product_id}/confirm
    """
    customer_product = update_and_confirm_temporary(db, product_id, full_data)
    if not customer_product:
        raise HTTPException(status_code=404, detail=f"客户产品 {product_id} 不存在")
    return _build_response(customer_product, db)


@router.get("/by-customer/{customer_id}", response_model=List[CustomerProductResponse])
def get_products_by_customer(customer_id: int, db: Session = Depends(get_db)):
    """获取指定客户的所有产品"""
    items = get_customer_products_by_customer(db, customer_id)
    return [_build_response(item, db) for item in items]


@router.get("/by-oe/{oe_number}", response_model=List[CustomerProductResponse])
def search_by_oe(oe_number: str, db: Session = Depends(get_db)):
    """通过OE号搜索产品"""
    items = search_by_oe_number(db, oe_number)
    return [_build_response(item, db) for item in items]


@router.get("/by-code/{code}", response_model=List[CustomerProductResponse])
def search_by_product_code(code: str, db: Session = Depends(get_db)):
    """通过编号搜索产品"""
    items = search_by_code(db, code)
    return [_build_response(item, db) for item in items]


@router.get("/by-system-code/{system_code}", response_model=Optional[CustomerProductResponse])
def get_customer_product_by_system_code_api(system_code: str, db: Session = Depends(get_db)):
    """通过系统编号获取单个客户产品"""
    from crud.customer_product import get_customer_product_by_system_code
    customer_product = get_customer_product_by_system_code(db, system_code)
    if not customer_product:
        raise HTTPException(status_code=404, detail="客户产品不存在")
    return _build_response(customer_product, db)


@router.get("/{product_id}", response_model=CustomerProductResponse)
def get_customer_product_by_id(product_id: int, db: Session = Depends(get_db)):
    """获取单个客户产品"""
    customer_product = get_customer_product(db, product_id)
    if not customer_product:
        raise HTTPException(status_code=404, detail="客户产品不存在")
    return _build_response(customer_product, db)


@router.post("", response_model=CustomerProductResponse)
def create_customer_product_api(data: CustomerProductCreate, db: Session = Depends(get_db)):
    """创建客户产品"""
    # 检查客户是否存在
    customer = get_customer_by_id(db, data.customer_id)
    if not customer:
        raise HTTPException(status_code=400, detail="客户不存在")
    
    customer_product = create_customer_product(db, data)
    return _build_response(customer_product, db)


@router.put("/{product_id}", response_model=CustomerProductResponse)
def update_customer_product_api(product_id: int, data: CustomerProductUpdate, db: Session = Depends(get_db)):
    """更新客户产品"""
    customer_product = update_customer_product(db, product_id, data)
    if not customer_product:
        raise HTTPException(status_code=404, detail="客户产品不存在")
    return _build_response(customer_product, db)


@router.delete("/{product_id}")
def delete_customer_product_by_id(
    product_id: int, 
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    删除客户产品（异步软删除）
    
    1. 立即软删除（设置 is_active=False, deleted_at=当前时间）
    2. 后台任务在24小时后物理删除（可选）
    
    处理多用户冲突：
    - 使用行级锁（SELECT FOR UPDATE）防止并发删除
    - 检查产品是否已被其他用户删除
    """
    result = delete_customer_product(db, product_id, soft_only=True)
    
    if not result["success"]:
        if result["conflict"]:
            raise HTTPException(status_code=409, detail=result["message"])
        raise HTTPException(status_code=404, detail=result["message"])
    
    # 安排后台清理任务（24小时后物理删除）
    # 注意：这里的 background_tasks 可能为 None，在需要时可以通过调度器触发
    # 这里先记录日志，实际的定时清理可以通过 cron 或 scheduler 实现
    
    return {
        "message": "删除成功（将在24小时后物理删除）",
        "deleted_at": result.get("deleted_at"),
        "warning": "产品已标记为删除，可在24小时内恢复"
    }


# ========== 编号管理 ==========

@router.get("/{product_id}/codes", response_model=List[CustomerProductCodeResponse])
def get_product_codes_api(product_id: int, db: Session = Depends(get_db)):
    """获取客户产品的编号列表"""
    customer_product = get_customer_product(db, product_id)
    if not customer_product:
        raise HTTPException(status_code=404, detail="客户产品不存在")
    
    codes = get_product_codes(db, product_id)
    return [CustomerProductCodeResponse(
        id=code.id,
        customer_product_id=code.customer_product_id,
        product_code=code.product_code,
        is_primary=code.is_primary,
        remark=code.remark,
        created_at=code.created_at,
    ) for code in codes]


@router.post("/{product_id}/codes", response_model=CustomerProductCodeResponse)
def add_code(product_id: int, data: CustomerProductCodeCreate, db: Session = Depends(get_db)):
    """为客户产品添加编号"""
    customer_product = get_customer_product(db, product_id)
    if not customer_product:
        raise HTTPException(status_code=404, detail="客户产品不存在")
    
    code = add_product_code(db, product_id, data)
    return CustomerProductCodeResponse(
        id=code.id,
        customer_product_id=code.customer_product_id,
        product_code=code.product_code,
        is_primary=code.is_primary,
        remark=code.remark,
        created_at=code.created_at,
    )


@router.post("/codes/{code_id}/set-primary")
def set_primary_code_api(code_id: int, db: Session = Depends(get_db)):
    """设置主编号"""
    success = set_primary_code(db, code_id)
    if not success:
        raise HTTPException(status_code=404, detail="编号不存在")
    return {"message": "设置成功"}


@router.delete("/codes/{code_id}")
def delete_code(code_id: int, db: Session = Depends(get_db)):
    """删除编号"""
    success = delete_product_code(db, code_id)
    if not success:
        raise HTTPException(status_code=404, detail="编号不存在")
    return {"message": "删除成功"}


@router.post("/{product_id}/codes/batch")
def batch_import_codes(product_id: int, request: BatchImportRequest, db: Session = Depends(get_db)):
    """批量导入编号"""
    customer_product = get_customer_product(db, product_id)
    if not customer_product:
        raise HTTPException(status_code=404, detail="客户产品不存在")
    
    codes = batch_add_codes(db, product_id, request.items, request.set_first_as_primary)
    return {
        "message": f"成功导入 {len(codes)} 个编号",
        "count": len(codes)
    }


# ========== OE号管理 ==========

@router.get("/{product_id}/oes", response_model=List[CustomerProductOEResponse])
def get_product_oes_api(product_id: int, db: Session = Depends(get_db)):
    """获取客户产品的OE号列表"""
    customer_product = get_customer_product(db, product_id)
    if not customer_product:
        raise HTTPException(status_code=404, detail="客户产品不存在")
    
    oes = get_product_oes(db, product_id)
    return [CustomerProductOEResponse(
        id=oe.id,
        customer_product_id=oe.customer_product_id,
        oe_number=oe.oe_number,
        is_primary=oe.is_primary,
        remark=oe.remark,
        created_at=oe.created_at,
    ) for oe in oes]


@router.post("/{product_id}/oes", response_model=CustomerProductOEResponse)
def add_oe(product_id: int, data: CustomerProductOECreate, db: Session = Depends(get_db)):
    """为客户产品添加OE号"""
    customer_product = get_customer_product(db, product_id)
    if not customer_product:
        raise HTTPException(status_code=404, detail="客户产品不存在")
    
    oe = add_product_oe(db, product_id, data)
    return CustomerProductOEResponse(
        id=oe.id,
        customer_product_id=oe.customer_product_id,
        oe_number=oe.oe_number,
        is_primary=oe.is_primary,
        remark=oe.remark,
        created_at=oe.created_at,
    )


@router.post("/oes/{oe_id}/set-primary")
def set_primary_oe_api(oe_id: int, db: Session = Depends(get_db)):
    """设置主OE号"""
    success = set_primary_oe(db, oe_id)
    if not success:
        raise HTTPException(status_code=404, detail="OE号不存在")
    return {"message": "设置成功"}


@router.delete("/oes/{oe_id}")
def delete_oe(oe_id: int, db: Session = Depends(get_db)):
    """删除OE号"""
    success = delete_product_oe(db, oe_id)
    if not success:
        raise HTTPException(status_code=404, detail="OE号不存在")
    return {"message": "删除成功"}


@router.post("/{product_id}/oes/batch")
def batch_import_oes(product_id: int, request: BatchImportRequest, db: Session = Depends(get_db)):
    """批量导入OE号"""
    customer_product = get_customer_product(db, product_id)
    if not customer_product:
        raise HTTPException(status_code=404, detail="客户产品不存在")
    
    oes = batch_add_oes(db, product_id, request.items, request.set_first_as_primary)
    return {
        "message": f"成功导入 {len(oes)} 个OE号",
        "count": len(oes)
    }


# ========== 后台清理任务 ==========

@router.post("/cleanup")
def cleanup_deleted_products_api(
    hours: int = Query(24, description="超过多少小时的产品将被物理删除"),
    db: Session = Depends(get_db)
):
    """
    清理已软删除的产品（物理删除超过指定时间的产品）
    
    这是一个管理员操作，用于清理垃圾数据。
    建议通过定时任务（cron）自动执行。
    """
    count, error = cleanup_deleted_products(db, hours)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return {
        "message": f"成功清理 {count} 个产品",
        "deleted_count": count
    }