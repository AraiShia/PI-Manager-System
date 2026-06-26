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
    PiProformaInvoiceItem,  # 新增：用于获取原始订单信息
    PrdCustomerProduct
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

def generate_shipment_no(db: Session, dept_code: str = "S") -> str:
    """生成出货单号：部门+YYYYMMDD+1位36进制序号"""
    from datetime import datetime
    today = datetime.now().strftime("%Y%m%d")
    
    # 36进制字符集
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    
    # 查找当天最大序号
    prefix = f"{dept_code}-{today}-"
    from sqlalchemy import text
    last_no = db.execute(text(
        "SELECT shipment_no FROM sh_shipment WHERE shipment_no LIKE :prefix ORDER BY shipment_no DESC LIMIT 1"
    ), {"prefix": f"{prefix}%"}).fetchone()
    
    if last_no:
        last_seq = last_no[0][-1]  # 取最后一位
        if last_seq in chars:
            idx = chars.index(last_seq) + 1
            if idx >= len(chars):
                idx = 0  # 循环回到0
        else:
            idx = 0
    else:
        idx = 0
    
    return f"{prefix}{chars[idx]}"


def create_shipment_from_pending(db: Session, pending_item_ids: list[int], user_id: int, dept_code: str = "S", ci_no: str = None):
    """从待出货队列创建出货单"""
    from backend.models.pending_shipment import ShPendingShipmentItem
    
    # 获取待出货项
    pending_items = db.query(ShPendingShipmentItem).filter(
        ShPendingShipmentItem.id.in_(pending_item_ids),
        ShPendingShipmentItem.status == 2  # 已确认状态
    ).all()
    
    if not pending_items:
        raise ValueError("没有已确认的待出货项")
    
    # 创建出货单主表
    db_shipment = ShShipment(
        shipment_no=generate_shipment_no(db, dept_code),
        dept_id=dept_code,
        status=1,
        payment_status=1,
        created_by=user_id,
        ci_no=ci_no or generate_shipment_no(db, dept_code)
    )
    db.add(db_shipment)
    db.commit()
    db.refresh(db_shipment)
    
    # 收集PI号
    pi_ids = set()
    total_amount = 0
    total_cartons = 0
    total_gross_weight = 0.0
    total_volume = 0.0
    total_quantity = 0
    
    for item in pending_items:
        pi_ids.add(item.pi_id)
        
        # 获取PI明细信息
        pi_item = db.query(PiProformaInvoiceItem).filter_by(id=item.pi_item_id).first()
        if not pi_item:
            continue
        
        product = db.query(PrdCustomerProduct).filter(PrdCustomerProduct.id == item.product_id).first()

        quantity = float(pi_item.quantity or 0)
        unit_price = float(pi_item.unit_price or 0)
        total_price = quantity * unit_price
        
        cartons_shipped = 0
        volume_shipped_m3 = 0.0
        gross_weight = 0.0
        
        if product and product.carton_volume_m3 and product.units_per_carton:
            cartons_shipped = int(quantity / product.units_per_carton) if product.units_per_carton else 0
            volume_shipped_m3 = cartons_shipped * float(product.carton_volume_m3) if product.carton_volume_m3 else 0
        
        if product and product.gross_weight_kg:
            gross_weight = cartons_shipped * float(product.gross_weight_kg) if product.gross_weight_kg else 0
        
        # 创建出货明细
        db_item = ShShipmentItem(
            shipment_id=db_shipment.id,
            pi_item_id=item.pi_item_id,
            product_id=item.product_id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
            cartons_shipped=cartons_shipped,
            volume_shipped_m3=volume_shipped_m3,
            gross_weight=gross_weight
        )
        db.add(db_item)
        
        # 更新汇总
        total_amount += total_price
        total_cartons += cartons_shipped
        total_gross_weight += gross_weight
        total_volume += volume_shipped_m3
        total_quantity += quantity
        
        # 标记待出货项为已出货
        item.status = 3
    
    # 更新出货单汇总
    db_shipment.total_amount = total_amount
    db_shipment.total_cartons = total_cartons
    db_shipment.total_gross_weight = total_gross_weight
    db_shipment.total_volume = total_volume
    db_shipment.pi_nos = ",".join(str(pid) for pid in sorted(pi_ids))
    
    db.commit()
    db.refresh(db_shipment)
    
    return db_shipment

def create_shipment(db: Session, shipment: ShipmentCreate) -> ShShipment:
    """创建出货单（支持多阶段）"""
    import logging
    logger = logging.getLogger(__name__)

    shipment_start = datetime.now()
    logger.info(f"\n{'═' * 80}")
    logger.info(f"[🚚 出货单创建流程开始] create_shipment()")
    logger.info(f"{'═' * 80}")
    logger.info(f"  参数:")
    logger.info(f"    PI_ID: {shipment.pi_id}")
    logger.info(f"    Dept_ID: {shipment.dept_id}")
    logger.info(f"    Stages数量: {len(shipment.stages)}")
    logger.info(f"    Items数量: {len(shipment.items) if hasattr(shipment, 'items') and shipment.items else 0}")

    # 步骤1: 验证PI
    logger.info(f"\n[步骤1/5] 验证PI订单...")
    pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == shipment.pi_id).first()
    if not pi:
        logger.error(f"[❌ 错误] PI不存在: pi_id={shipment.pi_id}")
        raise ValueError("PI不存在")

    logger.info(f"[✅ PI验证成功]")
    logger.info(f"  PI_ID: {pi.id}")
    logger.info(f"  PI_NO: {pi.pi_no}")
    logger.info(f"  客户ID: {pi.customer_id}")

    # 步骤2: 创建出货单主表
    logger.info(f"\n[步骤2/5] 创建出货单主表...")
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

    logger.info(f"[✅ 出货单主表创建成功]")
    logger.info(f"  Shipment ID: {db_shipment.id}")
    logger.info(f"  Shipment NO: {db_shipment.shipment_no}")
    logger.info(f"  Status: {db_shipment.status} (1=待出货)")

    # 步骤3: 创建出货阶段
    logger.info(f"\n[步骤3/5] 创建出货阶段 (共{len(shipment.stages)}个)...")
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

        logger.info(f"  [Stage {idx}/{len(shipment.stages)}]")
        logger.info(f"    Stage Name: {stage_data.stage_name or f'出货{idx}'}")
        logger.info(f"    Quantity: {stage_data.quantity or 0}")
        logger.info(f"    Container NO: {stage_data.container_no}")
        logger.info(f"    B/L NO: {stage_data.bl_no}")

    logger.info(f"[✅ 所有出货阶段创建完成] 总数量: {total_quantity}")

    # 步骤4: 创建出货明细
    logger.info(f"\n[步骤4/5] 创建出货明细...")
    total_amount = 0
    total_cartons = 0
    total_gross_weight = 0.0
    total_volume = 0.0
    items_count = 0

    if shipment.items:
        for item_idx, item in enumerate(shipment.items, start=1):
            product = db.query(PrdCustomerProduct).filter(PrdCustomerProduct.id == item.product_id).first()

            # 检查库存（可选，跳过检查以避免错误）
            inventory = db.query(InvInventory).filter(
                InvInventory.product_id == item.product_id
            ).first()

            # 获取PI订单项信息（用于填充原始订单数据）
            pi_item = None
            order_quantity = 0
            order_unit_price = 0
            order_total_amount = 0
            oe_number = None
            customer_code = None
            product_image = None

            if item.pi_item_id:
                pi_item = db.query(PiProformaInvoiceItem).filter(
                    PiProformaInvoiceItem.id == item.pi_item_id
                ).first()
                if pi_item:
                    order_quantity = float(pi_item.quantity or 0)
                    order_unit_price = float(pi_item.unit_price or 0)
                    order_total_amount = float(pi_item.total_price or 0)
                    oe_number = pi_item.oe_number
                    customer_code = pi_item.customer_code
                    # 如果PI项有临时图片，使用临时图片；否则使用产品图片
                    product_image = getattr(pi_item, 'temp_image', None) or (product.product_image if product else None)

            # 如果没有PI项信息，尝试从产品获取客户编号
            if not customer_code and product:
                # 尝试从客户信息获取customer_code
                pass  # 后续可以从CRM获取

            unit_price = item.unit_price or 0
            total_price = item.quantity * unit_price
            total_amount += total_price

            # 计算箱数和体积（基于出货数量）
            cartons_shipped = 0
            volume_shipped_m3 = 0.0
            if product and product.carton_volume_m3 and product.units_per_carton:
                cartons_shipped = int(item.quantity / float(product.units_per_carton)) if float(product.units_per_carton) > 0 else 0
                volume_shipped_m3 = cartons_shipped * float(product.carton_volume_m3) if product.carton_volume_m3 else 0
                total_cartons += cartons_shipped
                total_volume += volume_shipped_m3

            gross_weight = 0.0
            if product and product.gross_weight_kg:
                gross_weight = cartons_shipped * float(product.gross_weight_kg) if product.gross_weight_kg else 0
                total_gross_weight += gross_weight

            # 计算预计值（基于订单数量）
            cartons_estimated = 0
            volume_estimated = 0.0
            gross_weight_estimated = 0.0
            if product and order_quantity > 0:
                if product.units_per_carton and float(product.units_per_carton) > 0:
                    cartons_estimated = int(order_quantity / float(product.units_per_carton))
                if product.carton_volume_m3 and cartons_estimated > 0:
                    volume_estimated = cartons_estimated * float(product.carton_volume_m3)
                if product.gross_weight_kg and cartons_estimated > 0:
                    gross_weight_estimated = cartons_estimated * float(product.gross_weight_kg)

            # 计算剩余值
            remaining_quantity = order_quantity - float(item.quantity) if order_quantity > 0 else 0
            remaining_cartons = cartons_estimated - cartons_shipped if cartons_estimated > 0 else 0
            remaining_volume = volume_estimated - volume_shipped_m3 if volume_estimated > 0 else 0

            db_item = ShShipmentItem(
                shipment_id=db_shipment.id,
                stage_id=item.stage_id,  # 关联到具体阶段
                pi_item_id=item.pi_item_id,
                product_id=item.product_id,

                # ===== 原始订单信息（来自PI订单项） =====
                customer_code=customer_code,           # 客户编号
                oe_number=oe_number,                   # OE号
                product_image=product_image,           # 产品图片
                order_quantity=order_quantity,         # 订单数量
                order_unit_price=order_unit_price,     # 订单单价 (USD)
                order_total_amount=order_total_amount, # 订单总金额 (USD)
                cartons_estimated=cartons_estimated,   # 预计总箱数
                volume_estimated=volume_estimated,     # 预计总体积 m³
                gross_weight_kg=gross_weight_estimated,# 预计总重量 kg

                # ===== 出货信息 =====
                shipment_quantity=item.quantity,       # 出货数量
                shipment_unit_price=unit_price,        # 出货单价 (USD)
                shipment_total_amount=total_price,     # 出货金额 (USD)
                shipment_cartons=cartons_shipped,      # 出货箱数
                shipment_volume=volume_shipped_m3,     # 出货体积 m³
                shipment_weight=gross_weight,          # 出货重量 kg

                # ===== 库存/剩余信息 =====
                remaining_quantity=remaining_quantity, # 剩余数量
                remaining_cartons=remaining_cartons,   # 剩余箱数
                remaining_volume=remaining_volume,     # 剩余体积 m³

                # ===== 兼容旧字段（保持向后兼容） =====
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
            items_count += 1

            logger.info(f"  [Item {item_idx}]")
            logger.info(f"    Product ID: {item.product_id}")
            logger.info(f"    [原始订单] 数量={order_quantity}, 单价={order_unit_price}, 总额={order_total_amount} USD")
            logger.info(f"    [出货信息] 数量={item.quantity}, 单价={unit_price}, 总额={total_price} USD")
            logger.info(f"    [装箱信息] 箱数={cartons_shipped}, 体积={volume_shipped_m3} m³, 重量={gross_weight} kg")
            logger.info(f"    [剩余信息] 数量={remaining_quantity}, 箱数={remaining_cartons}, 体积={remaining_volume} m³")

            # 扣减库存（如果有库存记录）
            if inventory:
                old_pending = float(inventory.pending_quantity)
                old_shipped = float(inventory.shipped_quantity)

                inventory.pending_quantity = old_pending - float(item.quantity)
                inventory.shipped_quantity = old_shipped + float(item.quantity)

                logger.info(f"    [库存扣减]")
                logger.info(f"      待出库: {old_pending} → {inventory.pending_quantity}")
                logger.info(f"      已出库: {old_shipped} → {inventory.shipped_quantity}")

                # 更新阶段库存信息
                if item.stage_id:
                    stage = db.query(ShShipmentStage).filter(ShShipmentStage.id == item.stage_id).first()
                    if stage:
                        stage.inventory_quantity = inventory.pending_quantity
                        stage.inventory_amount = float(inventory.pending_quantity) * unit_price

    logger.info(f"[✅ 出货明细创建完成]")
    logger.info(f"  Items数量: {items_count}")
    logger.info(f"  总金额: {total_amount} USD")
    logger.info(f"  总箱数: {total_cartons}")
    logger.info(f"  总重量: {total_gross_weight} kg")
    logger.info(f"  总体积: {total_volume} m³")

    # 步骤5: 提交事务并更新汇总数据
    logger.info(f"\n[步骤5/5] 提交事务并更新汇总数据...")

    # 更新出货单汇总信息
    logger.info(f"  更新出货单汇总数据...")
    db_shipment.total_amount = total_amount
    db_shipment.total_cartons = total_cartons
    db_shipment.total_gross_weight = total_gross_weight
    db_shipment.total_volume = total_volume

    db.commit()
    db.refresh(db_shipment)
    logger.info(f"[✅ 提交成功]")

    # 输出最终结果
    shipment_duration = (datetime.now() - shipment_start).total_seconds()
    logger.info(f"\n{'═' * 80}")
    logger.info(f"[✅ 出货单创建流程完成]")
    logger.info(f"{'═' * 80}")
    logger.info(f"  统计信息:")
    logger.info(f"    Shipment ID: {db_shipment.id}")
    logger.info(f"    Shipment NO: {db_shipment.shipment_no}")
    logger.info(f"    PI_ID: {db_shipment.pi_id}")
    logger.info(f"    Stages数量: {len(shipment.stages)}")
    logger.info(f"    Items数量: {items_count}")
    logger.info(f"    总金额: {total_amount} USD")
    logger.info(f"    总箱数: {total_cartons}")
    logger.info(f"    总重量: {total_gross_weight} kg")
    logger.info(f"    总体积: {total_volume} m³")
    logger.info(f"    总耗时: {shipment_duration:.3f}s")
    logger.info(f"    Status: {db_shipment.status} (1=待出货)")
    logger.info(f"{'═' * 80}\n")

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
    import logging
    logger = logging.getLogger(__name__)

    confirm_start = datetime.now()
    logger.info(f"\n{'═' * 80}")
    logger.info(f"[✅ 出货确认流程开始] confirm_shipment()")
    logger.info(f"{'═' * 80}")
    logger.info(f"  参数:")
    logger.info(f"    Shipment ID: {shipment_id}")

    # 步骤1: 查询出货单
    logger.info(f"\n[步骤1/3] 查询出货单...")
    shipment = db.query(ShShipment).filter(ShShipment.id == shipment_id).first()
    if not shipment:
        logger.error(f"[❌ 错误] 出货单不存在: {shipment_id}")
        raise ValueError("出货单不存在")

    logger.info(f"[✅ 出货单查询成功]")
    logger.info(f"  Shipment ID: {shipment.id}")
    logger.info(f"  Shipment NO: {shipment.shipment_no}")
    logger.info(f"  PI_ID: {shipment.pi_id}")
    logger.info(f"  当前状态: {shipment.status} (1=待出货)")
    logger.info(f"  Items数量: {len(shipment.items) if shipment.items else 0}")

    # 步骤2: 更新库存状态
    logger.info(f"\n[步骤2/3] 更新库存状态...")
    items_updated = 0
    for item_idx, item in enumerate(shipment.items or [], start=1):
        inventory = db.query(InvInventory).filter(
            InvInventory.product_id == item.product_id
        ).first()
        if inventory:
            old_location = inventory.current_location
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
            items_updated += 1

            logger.info(f"  [Item {item_idx}]")
            logger.info(f"    Product ID: {item.product_id}")
            logger.info(f"    Quantity: {item.quantity}")
            logger.info(f"    Location: {old_location} → IN_TRANSIT")

    logger.info(f"[✅ 库存状态更新完成]")
    logger.info(f"  更新的Items数量: {items_updated}")

    # 步骤3: 更新出货单状态
    logger.info(f"\n[步骤3/3] 更新出货单状态...")
    old_status = shipment.status
    shipment.status = 2  # 出货中

    db.commit()
    db.refresh(shipment)

    logger.info(f"[✅ 状态更新完成]")
    logger.info(f"  Status: {old_status} → {shipment.status} (2=出货中)")

    # 输出最终结果
    confirm_duration = (datetime.now() - confirm_start).total_seconds()
    logger.info(f"\n{'═' * 80}")
    logger.info(f"[✅ 出货确认流程完成]")
    logger.info(f"{'═' * 80}")
    logger.info(f"  统计信息:")
    logger.info(f"    Shipment ID: {shipment.id}")
    logger.info(f"    Shipment NO: {shipment.shipment_no}")
    logger.info(f"    最终状态: {shipment.status} (2=出货中)")
    logger.info(f"    更新Items数: {items_updated}")
    logger.info(f"    耗时: {confirm_duration:.3f}s")
    logger.info(f"{'═' * 80}\n")

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


def get_shippable_items(db: Session, pi_ids: list) -> list:
    """获取可出货的产品列表（来自PI订单）"""
    from models import PiProformaInvoiceItem, PrdCustomerProduct, CrmCustomer

    items = db.query(PiProformaInvoiceItem).filter(
        PiProformaInvoiceItem.pi_id.in_(pi_ids)
    ).all()

    result = []
    for item in items:
        # 获取产品信息
        product = db.query(PrdCustomerProduct).filter(PrdCustomerProduct.id == item.product_id).first() if item.product_id else None
        
        # 获取PI信息
        pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == item.pi_id).first()
        pi_no = pi.pi_no if pi else ""
        customer_name = ""
        customer_code = ""
        if pi and pi.customer_id:
            customer = db.query(CrmCustomer).filter(CrmCustomer.id == pi.customer_id).first()
            if customer:
                customer_name = customer.customer_name or ""
                customer_code = customer.customer_code or ""
        
        # 获取已出货数量（从 sh_shipment_item）
        shipped_qty = db.query(ShShipmentItem).filter(
            ShShipmentItem.pi_item_id == item.id
        ).all()
        total_shipped = sum(float(s.shipment_quantity or s.quantity or 0) for s in shipped_qty)
        
        order_qty = float(item.quantity or 0)
        remaining_qty = order_qty - total_shipped
        
        result.append({
            "pi_item_id": item.id,
            "pi_id": item.pi_id,
            "pi_no": pi_no,
            "product_id": item.product_id,
            "product_name": product.detail_desc if product else item.detail_desc,
            "customer_code": customer_code,
            "customer_name": customer_name,
            "oe_number": item.oe_number or "",
            "customer_model": item.customer_code or "",
            "product_code": product.customer_product_code if product else "",
            "order_quantity": order_qty,
            "shipped_quantity": total_shipped,
            "remaining_quantity": max(0, remaining_qty),
            "unit_price": float(item.unit_price or 0),
            "total_amount": float(item.total_price or order_qty * float(item.unit_price or 0)),
            # 包装信息（用于前端自动计算箱数/体积/重量）
            "pack_spec": item.pack_spec or "",           # 装箱规格 "20 pcs/ctn"
            "carton_gross_weight": float(item.carton_gross_weight or 0),  # 单箱毛重 kg
            "carton_length_cm": float(item.carton_length_cm or 0),        # 外箱长 cm
            "carton_width_cm": float(item.carton_width_cm or 0),          # 外箱宽 cm
            "carton_height_cm": float(item.carton_height_cm or 0),        # 外箱高 cm
            "product_image": getattr(product, 'image_url', None) if product else None,
        })
    
    return result


def create_shipment_from_orders(db: Session, dept_id: str, pi_ids: list, items: list) -> ShShipment:
    """从订单创建出货单（2026-06-15 新增）"""
    from models import PiProformaInvoiceItem, PiProformaInvoice, PrdCustomerProduct, CrmCustomer
    
    # 1. 验证PI存在
    pis = db.query(PiProformaInvoice).filter(PiProformaInvoice.id.in_(pi_ids)).all()
    if not pis:
        raise ValueError("PI不存在")
    
    # 2. 生成出货单号
    shipment_no = generate_shipment_no(db, dept_id)
    
    # 3. 创建出货单
    db_shipment = ShShipment(
        dept_id=dept_id,
        shipment_no=shipment_no,
        pi_id=pi_ids[0] if pi_ids else None,  # 主PI
        status=1,  # 待出货
        payment_status=1,  # 未收款
    )
    db.add(db_shipment)
    db.flush()
    
    total_amount = 0
    total_cartons = 0
    total_gross_weight = 0.0
    total_volume = 0.0
    total_quantity = 0
    
    # 4. 创建出货明细
    for item_data in items:
        pi_item_id = item_data.get('pi_item_id')
        shipment_qty = item_data.get('shipment_quantity', 0)
        unit_price = item_data.get('unit_price', 0)
        
        # 获取原始订单信息
        pi_item = db.query(PiProformaInvoiceItem).filter_by(id=pi_item_id).first()
        if not pi_item:
            continue
        
        product = db.query(PrdCustomerProduct).filter(PrdCustomerProduct.id == item_data.get('product_id')).first() if item_data.get('product_id') else None
        
        # 获取客户信息
        customer_code = ""
        if pi_item.pi_id:
            pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == pi_item.pi_id).first()
            if pi and pi.customer_id:
                customer = db.query(CrmCustomer).filter(CrmCustomer.id == pi.customer_id).first()
                if customer:
                    customer_code = customer.customer_code or ""
        
        # 计算体积和重量 — 优先用前端传入的值，否则从 PI item 计算
        cartons = int(item_data.get('cartons', 0)) or 0
        volume = float(item_data.get('volume_m3', 0)) or 0.0
        weight = float(item_data.get('weight_kg', 0)) or 0.0

        # 前端未传时自动计算
        if not cartons or not volume or not weight:
            # 装箱规格 (units per carton)
            units_per_carton = None
            if pi_item.pack_spec:
                import re
                match = re.match(r'(\d+)', str(pi_item.pack_spec).strip())
                if match:
                    units_per_carton = int(match.group(1))
            if not units_per_carton and product and hasattr(product, 'units_per_carton') and product.units_per_carton:
                try:
                    units_per_carton = int(product.units_per_carton)
                except (ValueError, TypeError):
                    pass

            if not cartons and units_per_carton and units_per_carton > 0:
                cartons = int(shipment_qty / units_per_carton)
                if shipment_qty % units_per_carton > 0:
                    cartons += 1
            if pi_item.carton_count and not cartons:
                cartons = int(pi_item.carton_count)

            if not weight:
                if pi_item.carton_gross_weight:
                    weight = float(pi_item.carton_gross_weight)
                elif product and hasattr(product, 'gross_weight_kg') and product.gross_weight_kg:
                    weight = float(product.gross_weight_kg) * max(cartons, 1)

            if not volume:
                if pi_item.carton_length_cm and pi_item.carton_width_cm and pi_item.carton_height_cm:
                    vol_cm3 = float(pi_item.carton_length_cm) * float(pi_item.carton_width_cm) * float(pi_item.carton_height_cm)
                    volume = vol_cm3 * max(cartons, 1) / 1_000_000
                elif product and hasattr(product, 'carton_volume_m3') and product.carton_volume_m3:
                    volume = float(product.carton_volume_m3) * max(cartons, 1)
        
        shipment_amount = shipment_qty * unit_price
        
        # 创建出货明细（使用19列格式）
        shipment_item = ShShipmentItem(
            shipment_id=db_shipment.id,
            pi_item_id=pi_item_id,
            product_id=item_data.get('product_id'),
            # 原始订单信息
            customer_code=customer_code,
            oe_number=pi_item.oe_number or "",
            product_image=getattr(product, 'image_url', None) if product else None,
            order_quantity=float(pi_item.quantity or 0),
            order_unit_price=float(pi_item.unit_price or 0),
            order_total_amount=float(pi_item.total_price or 0),
            cartons_estimated=cartons,
            volume_estimated=volume,
            gross_weight_kg=weight,
            # 出货信息
            shipment_quantity=shipment_qty,
            shipment_unit_price=unit_price,
            shipment_total_amount=shipment_amount,
            shipment_cartons=cartons,
            shipment_volume=volume,
            shipment_weight=weight,
            # 兼容旧字段
            quantity=shipment_qty,
            unit_price=unit_price,
            total_price=shipment_amount,
            cartons_shipped=cartons,
            volume_shipped_m3=volume,
            gross_weight=weight,
        )
        db.add(shipment_item)
        
        # 更新汇总
        total_amount += shipment_amount
        total_cartons += cartons
        total_gross_weight += weight
        total_volume += volume
        total_quantity += shipment_qty
    
    # 更新出货单汇总
    db_shipment.total_amount = total_amount
    db_shipment.total_cartons = total_cartons
    db_shipment.total_gross_weight = total_gross_weight
    db_shipment.total_volume = total_volume
    db_shipment.total_quantity = total_quantity
    
    db.commit()
    db.refresh(db_shipment)
    
    return db_shipment
