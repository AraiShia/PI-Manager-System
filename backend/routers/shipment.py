from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from crud.shipment import (
    create_shipment, confirm_shipment, get_shipment, get_shipments, get_available_inventory, update_shipment,
    create_shipment_stage, update_shipment_stage, delete_shipment_stage, get_shipment_stages,
    create_shipment_from_pending, get_shippable_items, create_shipment_from_orders
)
from schemas.shipment import ShipmentCreate, ShipmentUpdate, ShipmentResponse, ShipmentStageCreate, ShipmentStageResponse
import traceback

router = APIRouter(prefix="/api/shipments", tags=["出货管理"])

def serialize_shipment(shipment):
    """序列化出货单，避免懒加载问题"""
    # 获取PI号
    pi_no = None
    if shipment.pi:
        pi_no = shipment.pi.pi_no
    
    # 获取阶段数量
    stages_count = 0
    try:
        stages_count = len(shipment.stages) if shipment.stages else 0
    except (AttributeError, TypeError):
        pass
    
    return {
        "id": shipment.id,
        "dept_id": shipment.dept_id,
        "pi_id": shipment.pi_id,
        "pi_no": pi_no,
        "shipment_no": shipment.shipment_no,
        "ci_no": getattr(shipment, "ci_no", "") or "",
        "ci_locked": shipment.ci_locked if hasattr(shipment, 'ci_locked') else False,
        "customs_no": getattr(shipment, 'customs_no', None),
        "pi_nos": getattr(shipment, 'pi_nos', None),
        "total_amount": float(shipment.total_amount) if shipment.total_amount else 0,
        "total_cartons": shipment.total_cartons or 0,
        "total_gross_weight": float(shipment.total_gross_weight) if shipment.total_gross_weight else 0,
        "total_volume": float(shipment.total_volume) if shipment.total_volume else 0,
        "total_quantity": getattr(shipment, 'total_quantity', 0) or 0,
        "payment_status": shipment.payment_status or 1,
        "status": shipment.status or 1,
        "stages_count": stages_count,
        "created_at": shipment.created_at.isoformat() if shipment.created_at else None,
    }

def serialize_shipment_detail(shipment, db: Session = None):
    """序列化出货单详情（包含stages + items，剩余列自动计算）"""
    import re
    result = serialize_shipment(shipment)

    # stages
    stages = []
    try:
        for stage in (shipment.stages or []):
            stages.append({
                "id": stage.id,
                "shipment_id": stage.shipment_id,
                "stage_name": stage.stage_name,
                "stage_no": stage.stage_no,
                "shipment_date": stage.shipment_date.isoformat()[:10] if stage.shipment_date else None,
                "container_no": stage.container_no,
                "bl_no": stage.bl_no,
                "quantity": float(stage.quantity) if stage.quantity else 0,
                "ci_document": stage.ci_document,
                "pl_document": stage.pl_document,
                "storage_location": stage.storage_location,
                "payment_status": stage.payment_status or 1,
                "remark": stage.remark
            })
    except Exception as e:
        print(f"[DEBUG] Error serializing stages: {e}")
    result["stages"] = stages

    # items（19列）
    items = []
    for item in (shipment.items or []):
        try:
            order_qty = float(item.order_quantity or 0)
            ship_qty = float(item.shipment_quantity or 0)
            items.append({
                "id": item.id,
                "pi_item_id": getattr(item, 'pi_item_id', None),
                "customer_code": item.customer_code or "",
                "oe_number": item.oe_number or "",
                "product_image": item.product_image or "",
                "order_quantity": order_qty,
                "order_unit_price": float(item.order_unit_price or 0),
                "order_total_amount": float(item.order_total_amount or 0),
                "cartons_estimated": item.cartons_estimated or 0,
                "volume_estimated": float(item.volume_estimated or 0),
                "gross_weight_kg": float(item.gross_weight_kg or 0),
                "shipment_quantity": ship_qty,
                "shipment_unit_price": float(item.shipment_unit_price or 0),
                "shipment_total_amount": float(item.shipment_total_amount or 0),
                "shipment_cartons": item.shipment_cartons or 0,
                "shipment_volume": float(item.shipment_volume or 0),
                "shipment_weight": float(item.shipment_weight or 0),
                # 剩余列 — 自动计算
                "remaining_quantity": max(0, order_qty - ship_qty),
                "remaining_cartons": 0,
                "remaining_volume": 0.0,
            })
        except Exception as e:
            print(f"[DEBUG] Error serializing shipment item: {e}")
            items.append({})

    # 后处理：计算剩余箱数和体积
    for item_data in items:
        if not item_data:
            continue
        remaining_qty = item_data.get('remaining_quantity', 0)
        if remaining_qty <= 0:
            continue

        rem_cartons = 0
        pi_item_id = item_data.get('pi_item_id')
        if pi_item_id and db:
            try:
                from models.pi import PiProformaInvoiceItem as _PII
                pii = db.query(_PII).filter(_PII.id == pi_item_id).first()
                if pii and pii.pack_spec:
                    m = re.match(r'(\d+)', str(pii.pack_spec).strip())
                    if m:
                        upc = int(m.group(1))
                        if upc > 0:
                            rem_cartons = int(remaining_qty / upc)
                            if remaining_qty % upc > 0:
                                rem_cartons += 1
            except Exception:
                pass
        item_data['remaining_cartons'] = rem_cartons

        rem_volume = 0.0
        if pi_item_id and db and rem_cartons > 0:
            try:
                from models.pi import PiProformaInvoiceItem as _PII2
                pii2 = db.query(_PII2).filter(_PII2.id == pi_item_id).first()
                if pii2:
                    l = float(pii2.carton_length_cm or 0)
                    w = float(pii2.carton_width_cm or 0)
                    h = float(pii2.carton_height_cm or 0)
                    if l > 0 and w > 0 and h > 0:
                        rem_volume = round(l * w * h * rem_cartons / 1_000_000, 3)
            except Exception:
                pass
        item_data['remaining_volume'] = rem_volume

    result["items"] = items
    return result

@router.post("/")
def create_shipment_api(shipment: ShipmentCreate, db: Session = Depends(get_db)):
    try:
        result = create_shipment(db, shipment)
        # 2026-06-10: 修复 T6.2 — 创建出货单返回完整 items
        return serialize_shipment_detail(result, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[ShipmentResponse])
def read_shipments(skip: int = 0, limit: int = 100, pi_id: int = None, status: int = None, db: Session = Depends(get_db)):
    shipments = get_shipments(db, skip=skip, limit=limit, pi_id=pi_id, status=status)
    return [serialize_shipment(s) for s in shipments]

# 必须在 /{shipment_id} 之前，否则会被当作 id 解析
@router.get("/inventory")
def read_available_inventory(pi_id: int, db: Session = Depends(get_db)):
    return get_available_inventory(db, pi_id)

# 必须在 /{shipment_id} 之前，否则会被当作 id 解析
@router.get("/shippable-items")
def get_shippable_items_api(pi_ids: str, db: Session = Depends(get_db)):
    """获取可出货的产品列表（来自PI订单）"""
    try:
        pi_id_list = [int(x.strip()) for x in pi_ids.split(",") if x.strip()]
        items = get_shippable_items(db, pi_id_list)
        return items
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# 必须在 /{shipment_id} 之前，否则会被当作 id 解析
@router.post("/from-orders")
def create_shipment_from_orders_api(req: dict, db: Session = Depends(get_db)):
    """从订单创建出货单"""
    try:
        dept_id = req.get("dept_id", "S")
        pi_ids = req.get("pi_ids", [])
        items = req.get("items", [])
        
        if not pi_ids:
            raise HTTPException(status_code=400, detail="pi_ids 不能为空")
        
        if not items:
            raise HTTPException(status_code=400, detail="items 不能为空")
        
        result = create_shipment_from_orders(db, dept_id, pi_ids, items)
        
        return {
            "success": True,
            "shipment_id": result.id,
            "shipment_no": result.shipment_no
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{shipment_id}")
def read_shipment(shipment_id: int, db: Session = Depends(get_db)):
    db_shipment = get_shipment(db, shipment_id)
    if db_shipment is None:
        raise HTTPException(status_code=404, detail="出货单不存在")
    return serialize_shipment_detail(db_shipment, db)

@router.post("/{shipment_id}/confirm")
def confirm_shipment_api(shipment_id: int, db: Session = Depends(get_db)):
    try:
        return confirm_shipment(db, shipment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{shipment_id}")
def update_shipment_api(shipment_id: int, shipment: ShipmentUpdate, db: Session = Depends(get_db)):
    print(f"[DEBUG] update_shipment_api called with shipment_id={shipment_id}")
    print(f"[DEBUG] shipment data: {shipment}")
    try:
        shipment_dict = shipment.model_dump(exclude_unset=True)
        print(f"[DEBUG] shipment_dict (exclude_unset): {shipment_dict}")
        result = update_shipment(db, shipment_id, shipment_dict)
        print(f"[DEBUG] update_shipment result: {result}")
        # 返回序列化后的字典，而不是 ORM 对象
        return serialize_shipment(result)
    except ValueError as e:
        print(f"[DEBUG] ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[DEBUG] Exception: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{shipment_id}/stages", response_model=list[ShipmentStageResponse])
def read_shipment_stages_api(shipment_id: int, db: Session = Depends(get_db)):
    """获取出货阶段列表"""
    return get_shipment_stages(db, shipment_id)

@router.post("/{shipment_id}/stages", response_model=ShipmentStageResponse)
def create_shipment_stage_api(shipment_id: int, stage: ShipmentStageCreate, db: Session = Depends(get_db)):
    """独立创建出货阶段"""
    try:
        return create_shipment_stage(db, shipment_id, stage.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{shipment_id}/stages/{stage_id}", response_model=ShipmentStageResponse)
def update_shipment_stage_api(shipment_id: int, stage_id: int, stage: ShipmentStageCreate, db: Session = Depends(get_db)):
    """更新出货阶段"""
    try:
        return update_shipment_stage(db, stage_id, stage.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{shipment_id}/stages/{stage_id}")
def delete_shipment_stage_api(shipment_id: int, stage_id: int, db: Session = Depends(get_db)):
    """删除出货阶段"""
    try:
        delete_shipment_stage(db, stage_id)
        return {"message": "阶段已删除"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/create-from-pending")
def create_from_pending(req: dict, db: Session = Depends(get_db)):
    """从待出货队列创建出货单"""
    try:
        result = create_shipment_from_pending(
            db,
            pending_item_ids=req.get("item_ids", []),
            user_id=req.get("user_id", 1),
            dept_code=req.get("dept_code", "S")
        )
        return {"success": True, "shipment": serialize_shipment(result)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
