from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from crud.shipment import (
    create_shipment, confirm_shipment, get_shipment, get_shipments, get_available_inventory, update_shipment,
    create_shipment_stage, update_shipment_stage, delete_shipment_stage, get_shipment_stages
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
        "pi_no": pi_no,  # 添加PI号
        "shipment_no": shipment.shipment_no,
        "total_amount": float(shipment.total_amount) if shipment.total_amount else 0,
        "total_cartons": shipment.total_cartons,
        "total_gross_weight": float(shipment.total_gross_weight) if shipment.total_gross_weight else 0,
        "total_volume": float(shipment.total_volume) if shipment.total_volume else 0,
        "payment_status": shipment.payment_status or 1,
        "status": shipment.status or 1,
        "stages_count": stages_count,  # 阶段数量
        "created_at": shipment.created_at.isoformat() if shipment.created_at else None,
    }

def serialize_shipment_detail(shipment):
    """序列化出货单详情（包含stages）"""
    result = serialize_shipment(shipment)
    
    # 添加stages详情
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
    return result

@router.post("/")
def create_shipment_api(shipment: ShipmentCreate, db: Session = Depends(get_db)):
    try:
        result = create_shipment(db, shipment)
        return serialize_shipment(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[ShipmentResponse])
def read_shipments(skip: int = 0, limit: int = 100, pi_id: int = None, status: int = None, db: Session = Depends(get_db)):
    shipments = get_shipments(db, skip=skip, limit=limit, pi_id=pi_id, status=status)
    return [serialize_shipment(s) for s in shipments]

@router.get("/{shipment_id}")
def read_shipment(shipment_id: int, db: Session = Depends(get_db)):
    db_shipment = get_shipment(db, shipment_id)
    if db_shipment is None:
        raise HTTPException(status_code=404, detail="出货单不存在")
    return serialize_shipment_detail(db_shipment)

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

@router.get("/inventory")
def read_available_inventory(pi_id: int, db: Session = Depends(get_db)):
    return get_available_inventory(db, pi_id)

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
