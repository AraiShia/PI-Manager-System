from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from crud.purchase import (
    create_purchase_order, create_grouped_purchase_orders, get_purchase_order, get_purchase_orders,
    update_purchase_status, create_1688_purchase, get_1688_purchases,
    update_purchase_order, get_purchase_orders_by_supplier,
    get_product_latest_purchase, create_1688_purchase_batch
)
from schemas.purchase import (
    PurchaseOrderCreate, PurchaseOrderResponse, PurchaseOrderDetailResponse, PurchaseOrderUpdate,
    Po1688PurchaseItem, Po1688PurchaseBatchCreate
)
router = APIRouter(prefix="/api/purchase-orders", tags=["采购管理"])
@router.post("/", response_model=PurchaseOrderResponse)
def create_purchase_order_api(purchase: PurchaseOrderCreate, db: Session = Depends(get_db)):
    try:
        return create_purchase_order(db, purchase)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[PurchaseOrderResponse])
def read_purchase_orders(skip: int = 0, limit: int = 100, status: int = None, pi_id: int = None, db: Session = Depends(get_db)):
    """[2026-06-23 修复] 列表中手动 join PI 与供应商，把 pi_no / supplier_name 填进响应，
    前端采购管理 Tab 才能展示（否则两列永远是空字符串，看起来像"无采购单"）"""
    from models import PiProformaInvoice, SupSupplier
    pos = get_purchase_orders(db, skip=skip, limit=limit, status=status, pi_id=pi_id)
    if not pos:
        return []
    # 批量取 PI 号、供应商名
    pi_ids = {po.pi_id for po in pos if po.pi_id}
    sup_ids = {po.supplier_id for po in pos if po.supplier_id}
    pi_no_map = {}
    if pi_ids:
        for pi in db.query(PiProformaInvoice).filter(PiProformaInvoice.id.in_(pi_ids)).all():
            pi_no_map[pi.id] = pi.pi_no
    sup_name_map = {}
    if sup_ids:
        for s in db.query(SupSupplier).filter(SupSupplier.id.in_(sup_ids)).all():
            sup_name_map[s.id] = s.supplier_name
    result = []
    for po in pos:
        result.append({
            "id": po.id,
            "po_no": po.po_no,
            "dept_id": po.dept_id,
            "pi_id": po.pi_id,
            "supplier_id": po.supplier_id,
            "pi_no": pi_no_map.get(po.pi_id, ""),
            "supplier_name": sup_name_map.get(po.supplier_id, ""),
            "total_amount": po.total_amount,
            "status": po.status,
            "created_at": po.created_at,
        })
    return result

@router.get("/{po_id}", response_model=PurchaseOrderDetailResponse)
def read_purchase_order(po_id: int, db: Session = Depends(get_db)):
    """[2026-06-17 计划] 返回采购单详情(包含 items, 每个 item 含 snapshot 字段)"""
    db_po = get_purchase_order(db, po_id)
    if db_po is None:
        raise HTTPException(status_code=404, detail="采购单不存在")
    # 触发 lazy load items
    _ = db_po.items
    return db_po

@router.put("/{po_id}", response_model=PurchaseOrderResponse)
def update_purchase_order_api(po_id: int, purchase_update: PurchaseOrderUpdate, db: Session = Depends(get_db)):
    try:
        db_po = update_purchase_order(db, po_id, purchase_update)
        if db_po is None:
            raise HTTPException(status_code=404, detail="采购单不存在")
        return db_po
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{po_id}/confirm")
def confirm_purchase(po_id: int, db: Session = Depends(get_db)):
    db_po = update_purchase_status(db, po_id, 2)
    if db_po is None:
        raise HTTPException(status_code=404, detail="采购单不存在")
    return {"message": "采购已确认", "purchase_order": db_po}

@router.post("/{po_id}/inbound")
def inbound_purchase(po_id: int, db: Session = Depends(get_db)):
    db_po = update_purchase_status(db, po_id, 3)
    if db_po is None:
        raise HTTPException(status_code=404, detail="采购单不存在")
    return {"message": "已入库", "purchase_order": db_po}

@router.post("/1688")
def create_1688_purchase_api(purchase_data: PurchaseOrderCreate, db: Session = Depends(get_db)):
    """[2026-06-17 计划] 按 supplier_id 分组生成采购单, 同时记录 1688 采购明细

    [2026-06-23 修复] 入参改用 PurchaseOrderCreate 而不是 Po1688PurchaseBatchCreate：
    - Po1688PurchaseBatchCreate.items 用的是 Po1688PurchaseItem（无 quantity 字段），
      FastAPI 解析时会丢弃前端的 quantity → PurchaseOrderCreate 校验报
      "items.0.quantity Field required"
    - PurchaseOrderCreate 字段更全，能完整接收前端发来的 items 数组
    - 1688 采购明细通过从 items 中提取 1688 字段构造，单独走 create_1688_purchase_batch
    """
    # 兼容 dict 与 pydantic
    if hasattr(purchase_data, "model_dump"):
        data = purchase_data.model_dump()
    elif hasattr(purchase_data, "dict"):
        data = purchase_data.dict()
    else:
        data = dict(purchase_data)

    # 1) 1688 采购明细：从完整 items 中提取 1688 维度字段
    created_records: list = []
    src_items = data.get("items") or []
    if src_items:
        batch_items = []
        for it in src_items:
            batch_items.append(Po1688PurchaseItem(
                product_id=it.get("product_id"),
                supplier_name=it.get("supplier_name") or data.get("supplier_name"),
                product_url=it.get("link") or it.get("product_url"),
                product_remark=it.get("remark"),
                color=it.get("color"),
                invoice_type=it.get("invoice_type"),
                labeling_fee=it.get("labeling_fee"),
                shipping_fee=it.get("shipping_fee"),
                shipping_method=it.get("shipping_method"),
                carton_count=it.get("carton_count"),
                freight=it.get("freight"),
                unit_price=it.get("unit_price"),
                tax_fee=it.get("tax_fee"),
                payment_method=it.get("payment_method"),
                gross_weight=it.get("gross_weight"),
            ))
        batch = Po1688PurchaseBatchCreate(
            dept_id=data.get("dept_id"),
            po_id=data.get("po_id"),
            pi_id=data.get("pi_id"),
            screenshot=data.get("screenshot"),
            remark=data.get("remark"),
            items=batch_items,
        )
        try:
            created_records = create_1688_purchase_batch(db, batch)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # 2) 按 supplier_id 分组生成采购单（用完整 data 走 PurchaseOrderCreate 校验）
    try:
        payload = PurchaseOrderCreate(**data)
        purchase_orders = create_grouped_purchase_orders(db, payload)
    except ValueError as e:
        # 缺少 supplier_id / 供应商不存在 / PI 不存在等校验失败 → 400
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "purchase_orders": purchase_orders,
        "records": created_records,
    }

@router.get("/1688")
def read_1688_purchases(pi_id: int = None, product_id: int = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_1688_purchases(db, pi_id=pi_id, product_id=product_id, skip=skip, limit=limit)

@router.get("/by-supplier/{supplier_id}", response_model=list[PurchaseOrderResponse])
def read_purchases_by_supplier(supplier_id: int, db: Session = Depends(get_db)):
    return get_purchase_orders_by_supplier(db, supplier_id)

@router.get("/product/{product_id}/latest")
def read_product_latest_purchase(product_id: int, db: Session = Depends(get_db)):
    """获取产品最近一次采购记录（包含费用和发票信息）"""
    record = get_product_latest_purchase(db, product_id)
    if record:
        return {"success": True, "record": record}
    return {"success": False, "record": None}
