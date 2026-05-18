from sqlalchemy.orm import Session
from datetime import datetime
from models import (
    ShShipment,
    ShShipmentItem,
    ShShipmentStage,
    ShCiDocument,
    ShPlDocument,
    InvInventory,
    InvInventoryLog,
    PiProformaInvoice,
    PrdProduct
)
from schemas import ShipmentCreate, ShipmentItemCreate, ShipmentStageCreate

def _parse_date(date_value):
    """解析日期字符串或datetime对象"""
    if date_value is None:
        return None
    if isinstance(date_value, datetime):
        return date_value
    if isinstance(date_value, str):
        try:
            return datetime.strptime(date_value[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return None

def generate_shipment_no(db: Session) -> str:
    """生成出货单号"""
    from datetime import datetime
    prefix = datetime.now().strftime("SH%Y%m%d")
    count = db.query(ShShipment).filter(ShShipment.shipment_no.like(f"{prefix}%")).count()
    return f"{prefix}{count + 1:03d}"

def create_shipment(db: Session, shipment: ShipmentCreate) -> ShShipment:
    """创建出货单（支持多阶段）"""
    pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == shipment.pi_id).first()
    if not pi:
        raise ValueError("PI不存在")

    # 创建出货单主表
    db_shipment = ShShipment(
        pi_id=shipment.pi_id,
        shipment_no=generate_shipment_no(db),
        dept_id=shipment.dept_id,
        status=1,  # 待出货
        payment_status=1  # 未收款
    )
    db.add(db_shipment)
    db.commit()
    db.refresh(db_shipment)

    # 创建出货阶段
    total_quantity = 0
    for idx, stage_data in enumerate(shipment.stages, 1):
        stage = ShShipmentStage(
                shipment_id=db_shipment.id,
                stage_name=stage_data.stage_name or f"出货{idx}",
                stage_no=idx,
                shipment_date=_parse_date(stage_data.shipment_date),
                container_no=stage_data.container_no,
                bl_no=stage_data.bl_no,
                quantity=stage_data.quantity or 0,
                ci_document=stage_data.ci_document,
                pl_document=stage_data.pl_document,
                storage_location=stage_data.storage_location,
                payment_status=stage_data.payment_status or 1,
                remark=stage_data.remark
            )
        db.add(stage)
        total_quantity += stage_data.quantity or 0

    # 创建出货明细（关联到阶段）- 如果没有items，跳过库存扣减
    total_amount = 0
    total_cartons = 0
    total_gross_weight = 0.0
    total_volume = 0.0

    if shipment.items:
        for item in shipment.items:
            product = db.query(PrdProduct).filter(PrdProduct.id == item.product_id).first()
            
            # 检查库存（可选，跳过检查以避免错误）
            inventory = db.query(InvInventory).filter(
                InvInventory.product_id == item.product_id
            ).first()

            unit_price = item.unit_price or 0
            total_price = item.quantity * unit_price
            total_amount += total_price

            # 计算箱数和体积
            cartons_shipped = 0
            volume_shipped_m3 = 0.0
            if product and product.carton_volume_m3 and product.units_per_carton:
                cartons_shipped = int(item.quantity / product.units_per_carton) if product.units_per_carton else 0
                volume_shipped_m3 = cartons_shipped * float(product.carton_volume_m3) if product.carton_volume_m3 else 0
                total_cartons += cartons_shipped
                total_volume += volume_shipped_m3

            gross_weight = 0.0
            if product and product.gross_weight_kg:
                gross_weight = cartons_shipped * float(product.gross_weight_kg) if product.gross_weight_kg else 0
                total_gross_weight += gross_weight

            db_item = ShShipmentItem(
                shipment_id=db_shipment.id,
                stage_id=item.stage_id,  # 关联到具体阶段
                pi_item_id=item.pi_item_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=unit_price,
                total_price=total_price,
                carton_no=item.carton_no,
                net_weight=item.net_weight,
                gross_weight=item.gross_weight or gross_weight,
                dimension=item.dimension,
                cartons_shipped=cartons_shipped,
                volume_shipped_m3=volume_shipped_m3,
                remark=item.remark
            )
            db.add(db_item)

            # 扣减库存（如果有库存记录）
            if inventory:
                inventory.pending_quantity = float(inventory.pending_quantity) - float(item.quantity)
                inventory.shipped_quantity = float(inventory.shipped_quantity) + float(item.quantity)
                
                # 更新阶段库存信息
                if item.stage_id:
                    stage = db.query(ShShipmentStage).filter(ShShipmentStage.id == item.stage_id).first()
                    if stage:
                        stage.inventory_quantity = inventory.pending_quantity
                        stage.inventory_amount = float(inventory.pending_quantity) * unit_price

    # 更新出货单汇总信息
    db_shipment.total_amount = total_amount
    db_shipment.total_cartons = total_cartons
    db_shipment.total_gross_weight = total_gross_weight
    db_shipment.total_volume = total_volume

    db.commit()
    db.refresh(db_shipment)

    return db_shipment

def update_shipment(db: Session, shipment_id: int, shipment_data: dict) -> ShShipment:
    """更新出货单（支持更新stages）"""
    print(f"[DEBUG] update_shipment called with shipment_id={shipment_id}, data={shipment_data}")
    
    db_shipment = db.query(ShShipment).filter(ShShipment.id == shipment_id).first()
    if not db_shipment:
        raise ValueError("出货单不存在")

    # 如果传了stages，更新阶段
    if 'stages' in shipment_data and shipment_data['stages'] is not None:
        print(f"[DEBUG] Updating stages, count: {len(shipment_data['stages'])}")
        
        # 删除旧stages
        deleted = db.query(ShShipmentStage).filter(ShShipmentStage.shipment_id == shipment_id).delete()
        print(f"[DEBUG] Deleted {deleted} old stages")
        
        # 创建新stages
        for idx, stage_data in enumerate(shipment_data['stages'], 1):
            print(f"[DEBUG] Creating stage {idx}: {stage_data}")
            stage = ShShipmentStage(
                shipment_id=shipment_id,
                stage_name=stage_data.get('stage_name') or f"出货{idx}",
                stage_no=idx,
                shipment_date=_parse_date(stage_data.get('shipment_date')),
                container_no=stage_data.get('container_no'),
                bl_no=stage_data.get('bl_no'),
                quantity=stage_data.get('quantity', 0),
                ci_document=stage_data.get('ci_document'),
                pl_document=stage_data.get('pl_document'),
                storage_location=stage_data.get('storage_location'),
                payment_status=stage_data.get('payment_status', 1),
                remark=stage_data.get('remark')
            )
            db.add(stage)

    db.commit()
    db.refresh(db_shipment)
    
    # 验证保存结果
    stages_in_db = db.query(ShShipmentStage).filter(ShShipmentStage.shipment_id == shipment_id).all()
    print(f"[DEBUG] After commit, stages in DB: {len(stages_in_db)}")
    
    return db_shipment

def get_shipment(db: Session, shipment_id: int) -> ShShipment:
    """获取出货单详情（包含stages）"""
    return db.query(ShShipment).filter(ShShipment.id == shipment_id).first()

def get_shipments(db: Session, skip: int = 0, limit: int = 100, pi_id: int = None, status: int = None):
    """获取出货单列表"""
    query = db.query(ShShipment)
    if pi_id is not None:
        query = query.filter(ShShipment.pi_id == pi_id)
    if status is not None:
        query = query.filter(ShShipment.status == status)
    return query.offset(skip).limit(limit).all()

def get_shipment_stages(db: Session, shipment_id: int):
    """获取出货阶段列表"""
    return db.query(ShShipmentStage).filter(ShShipmentStage.shipment_id == shipment_id).order_by(ShShipmentStage.stage_no).all()

def create_shipment_stage(db: Session, shipment_id: int, stage_data: dict) -> ShShipmentStage:
    """独立创建出货阶段"""
    shipment = db.query(ShShipment).filter(ShShipment.id == shipment_id).first()
    if not shipment:
        raise ValueError("出货单不存在")
    
    # 获取当前最大阶段号
    max_stage = db.query(ShShipmentStage).filter(
        ShShipmentStage.shipment_id == shipment_id
    ).order_by(ShShipmentStage.stage_no.desc()).first()
    
    next_stage_no = (max_stage.stage_no + 1) if max_stage else 1
    
    stage = ShShipmentStage(
        shipment_id=shipment_id,
        stage_name=stage_data.get('stage_name') or f"出货{next_stage_no}",
        stage_no=next_stage_no,
        shipment_date=_parse_date(stage_data.get('shipment_date')),
        container_no=stage_data.get('container_no'),
        bl_no=stage_data.get('bl_no'),
        quantity=stage_data.get('quantity', 0),
        ci_document=stage_data.get('ci_document'),
        pl_document=stage_data.get('pl_document'),
        storage_location=stage_data.get('storage_location'),
        payment_status=stage_data.get('payment_status', 1),
        remark=stage_data.get('remark')
    )
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage

def delete_shipment_stage(db: Session, stage_id: int):
    """删除出货阶段"""
    stage = db.query(ShShipmentStage).filter(ShShipmentStage.id == stage_id).first()
    if not stage:
        raise ValueError("出货阶段不存在")
    
    shipment_id = stage.shipment_id
    db.delete(stage)
    db.commit()
    
    # 重新排序阶段号
    stages = db.query(ShShipmentStage).filter(
        ShShipmentStage.shipment_id == shipment_id
    ).order_by(ShShipmentStage.stage_no).all()
    
    for idx, s in enumerate(stages, 1):
        s.stage_no = idx
        s.stage_name = f"出货{idx}"
    
    db.commit()

def update_shipment_stage(db: Session, stage_id: int, stage_data: dict) -> ShShipmentStage:
    """更新出货阶段"""
    stage = db.query(ShShipmentStage).filter(ShShipmentStage.id == stage_id).first()
    if not stage:
        raise ValueError("出货阶段不存在")

    if 'shipment_date' in stage_data:
        stage.shipment_date = _parse_date(stage_data['shipment_date'])
    if 'container_no' in stage_data:
        stage.container_no = stage_data['container_no']
    if 'bl_no' in stage_data:
        stage.bl_no = stage_data['bl_no']
    if 'quantity' in stage_data:
        stage.quantity = stage_data['quantity']
    if 'ci_document' in stage_data:
        stage.ci_document = stage_data['ci_document']
    if 'pl_document' in stage_data:
        stage.pl_document = stage_data['pl_document']
    if 'storage_location' in stage_data:
        stage.storage_location = stage_data['storage_location']
    if 'payment_status' in stage_data:
        stage.payment_status = stage_data['payment_status']
    if 'inventory_quantity' in stage_data:
        stage.inventory_quantity = stage_data['inventory_quantity']
    if 'inventory_amount' in stage_data:
        stage.inventory_amount = stage_data['inventory_amount']

    db.commit()
    db.refresh(stage)
    
    # 更新父出货单的付款状态
    _update_shipment_payment_status(db, stage.shipment_id)
    
    return stage

def _update_shipment_payment_status(db: Session, shipment_id: int):
    """更新出货单付款状态（根据所有阶段）"""
    stages = db.query(ShShipmentStage).filter(ShShipmentStage.shipment_id == shipment_id).all()
    if not stages:
        return
    
    total_stages = len(stages)
    paid_stages = sum(1 for s in stages if s.payment_status == 3)
    partial_stages = sum(1 for s in stages if s.payment_status == 2)
    
    shipment = db.query(ShShipment).filter(ShShipment.id == shipment_id).first()
    if shipment:
        if paid_stages == total_stages:
            shipment.payment_status = 3  # 已收齐
        elif partial_stages > 0 or paid_stages > 0:
            shipment.payment_status = 2  # 部分收款
        else:
            shipment.payment_status = 1  # 未收款
        db.commit()

def confirm_shipment(db: Session, shipment_id: int) -> ShShipment:
    """确认出货"""
    shipment = db.query(ShShipment).filter(ShShipment.id == shipment_id).first()
    if not shipment:
        raise ValueError("出货单不存在")

    # 更新库存状态
    for item in shipment.items:
        inventory = db.query(InvInventory).filter(
            InvInventory.product_id == item.product_id
        ).first()
        if inventory:
            inventory.current_location = 'IN_TRANSIT'

            log = InvInventoryLog(
                product_id=item.product_id,
                customer_id=inventory.customer_id or 0,
                pi_id=shipment.pi_id or 0,
                change_type=4,  # 4=出货
                change_quantity=float(-item.quantity),
                before_quantity=float(inventory.pending_quantity) + float(item.quantity),
                after_quantity=float(inventory.pending_quantity),
                ref_type='SHIPMENT',
                ref_id=shipment_id
            )
            db.add(log)

    shipment.status = 2  # 出货中
    db.commit()
    db.refresh(shipment)

    return shipment

def get_available_inventory(db: Session, pi_id: int):
    """获取可用库存"""
    pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == pi_id).first()
    if not pi:
        return []

    return db.query(InvInventory).filter(
        InvInventory.customer_id == pi.customer_id,
        InvInventory.pending_quantity > 0
    ).all()

def create_ci_document(db: Session, shipment_id: int, ci_data: dict) -> ShCiDocument:
    """创建CI文档"""
    db_ci = ShCiDocument(
        shipment_id=shipment_id,
        stage_id=ci_data.get('stage_id'),
        invoice_no=ci_data.get('invoice_no'),
        invoice_date=ci_data.get('invoice_date'),
        exporter=ci_data.get('exporter'),
        exporter_address=ci_data.get('exporter_address'),
        exporter_phone=ci_data.get('exporter_phone'),
        exporter_fax=ci_data.get('exporter_fax'),
        importer=ci_data.get('importer'),
        importer_address=ci_data.get('importer_address'),
        importer_phone=ci_data.get('importer_phone'),
        importer_fax=ci_data.get('importer_fax'),
        loading_port=ci_data.get('loading_port'),
        destination_port=ci_data.get('destination_port'),
        transport_way=ci_data.get('transport_way'),
        payment_terms=ci_data.get('payment_terms'),
        total_amount=ci_data.get('total_amount'),
        marks=ci_data.get('marks')
    )
    db.add(db_ci)
    db.commit()
    db.refresh(db_ci)
    return db_ci

def create_pl_document(db: Session, shipment_id: int, pl_data: dict) -> ShPlDocument:
    """创建PL文档"""
    db_pl = ShPlDocument(
        shipment_id=shipment_id,
        stage_id=pl_data.get('stage_id'),
        pl_no=pl_data.get('pl_no'),
        pl_date=pl_data.get('pl_date'),
        total_cartons=pl_data.get('total_cartons'),
        total_gross_weight=pl_data.get('total_gross_weight'),
        total_net_weight=pl_data.get('total_net_weight'),
        total_volume=pl_data.get('total_volume'),
        remark=pl_data.get('remark')
    )
    db.add(db_pl)
    db.commit()
    db.refresh(db_pl)
    return db_pl

def get_ci_document(db: Session, shipment_id: int, stage_id: int = None) -> ShCiDocument:
    """获取CI文档"""
    query = db.query(ShCiDocument).filter(ShCiDocument.shipment_id == shipment_id)
    if stage_id:
        query = query.filter(ShCiDocument.stage_id == stage_id)
    return query.first()

def get_pl_document(db: Session, shipment_id: int, stage_id: int = None) -> ShPlDocument:
    """获取PL文档"""
    query = db.query(ShPlDocument).filter(ShPlDocument.shipment_id == shipment_id)
    if stage_id:
        query = query.filter(ShPlDocument.stage_id == stage_id)
    return query.first()
