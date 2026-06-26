from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
from models import (
    PoPurchaseOrder,
    PoPurchaseOrderItem,
    Po1688Purchase,
    PiProformaInvoice,
    SupSupplier,
    PrdCustomerProduct
)
from schemas import PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderItemCreate
from utils.number_generator import NumberGenerator
# FixPlan Task 3: 导入同步函数
from crud.pi_sync import (
    _sync_pi_item_from_po,
    _sync_pi_item_from_1688,
)


def _get_pi_or_raise(db: Session, pi_id: int) -> PiProformaInvoice:
    pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == pi_id).first()
    if not pi:
        raise ValueError("PI不存在")
    return pi


def _resolve_item_supplier_id(item, fallback_supplier_id=None) -> int:
    supplier_id = getattr(item, "supplier_id", None) or fallback_supplier_id
    if not supplier_id:
        raise ValueError("存在商品缺少 supplier_id，无法生成采购单")
    return supplier_id


def _calculate_item_total(item) -> float:
    return (
        float(getattr(item, "quantity", 0) or 0) * float(getattr(item, "unit_price", 0) or 0)
        + float(getattr(item, "labeling_fee", 0) or 0)
        + float(getattr(item, "tax_fee", 0) or 0)
        + float(getattr(item, "shipping_fee", 0) or 0)
        + float(getattr(item, "freight", 0) or 0)
    )


def _build_purchase_order_item(po_id: int, item, product=None) -> PoPurchaseOrderItem:
    cartons_estimated = 0
    volume_estimated_m3 = 0
    product_units_per_carton = getattr(product, "units_per_carton", None)
    product_carton_volume = getattr(product, "carton_volume_m3", None)
    if product and product_carton_volume and product_units_per_carton:
        cartons_estimated = int(item.quantity / product_units_per_carton) if product_units_per_carton else 0
        volume_estimated_m3 = cartons_estimated * float(product_carton_volume) if product_carton_volume else 0

    return PoPurchaseOrderItem(
        po_id=po_id,
        product_id=item.product_id,
        pi_item_id=getattr(item, "pi_item_id", None),
        product_name_snapshot=getattr(item, "product_name", None) or getattr(product, "product_name", None),
        customer_model_snapshot=getattr(item, "customer_model", None) or getattr(product, "customer_model", None),
        factory_code=getattr(item, "factory_code", None),
        product_image=getattr(item, "product_image", None),
        color=getattr(item, "color", None),
        detail_requirement=getattr(item, "detail_requirement", None),
        line_1688_url=getattr(item, "link", None),
        quantity=item.quantity,
        unit_price=item.unit_price,
        total_price=_calculate_item_total(item),
        price_ex_factory=getattr(item, "price_ex_factory", None),
        price_ex_factory_tax=getattr(item, "price_ex_factory_tax", None),
        price_fob=getattr(item, "price_fob", None),
        price_fob_tax=getattr(item, "price_fob_tax", None),
        cartons_estimated=cartons_estimated,
        volume_estimated_m3=volume_estimated_m3,
        inbound_status=1,
        labeling_fee=getattr(item, "labeling_fee", None),
        tax_fee=getattr(item, "tax_fee", None),
        shipping_fee=getattr(item, "shipping_fee", None),
        freight=getattr(item, "freight", None),
    )


def create_grouped_purchase_orders(db: Session, purchase: PurchaseOrderCreate) -> list[PoPurchaseOrder]:
    import logging
    logger = logging.getLogger(__name__)

    purchase_start = datetime.now()
    logger.info(f"\n{'═' * 80}")
    logger.info(f"[🛒 采购订单创建流程开始] create_grouped_purchase_orders()")
    logger.info(f"{'═' * 80}")
    logger.info(f"  PI_ID: {purchase.pi_id}")
    logger.info(f"  Items数量: {len(purchase.items)}")
    logger.info(f"  部门ID: {purchase.dept_id}")

    # 步骤1: 验证PI
    logger.info(f"\n[步骤1/6] 验证PI订单...")
    pi = _get_pi_or_raise(db, purchase.pi_id)
    logger.info(f"[✅ PI验证成功]")
    logger.info(f"  PI_ID: {pi.id}")
    logger.info(f"  PI_NO: {pi.pi_no}")
    logger.info(f"  客户ID: {pi.customer_id}")
    logger.info(f"  状态: {pi.status}")

    # 步骤2: 按供应商分组
    logger.info(f"\n[步骤2/6] 按供应商分组Items...")
    grouped_items = {}

    for idx, item in enumerate(purchase.items):
        supplier_id = _resolve_item_supplier_id(item, getattr(purchase, "supplier_id", None))
        grouped_items.setdefault(supplier_id, []).append(item)
        logger.debug(f"  Item {idx+1}: product_id={item.product_id}, supplier_id={supplier_id}, qty={item.quantity}")

    logger.info(f"[✅ 分组完成]")
    logger.info(f"  供应商数量: {len(grouped_items)}")
    for supplier_id, items in grouped_items.items():
        logger.info(f"    Supplier {supplier_id}: {len(items)} items")

    created_orders = []
    total_po_amount = Decimal('0')

    # 步骤3: 创建采购单
    for group_idx, (supplier_id, items) in enumerate(grouped_items.items(), start=1):
        po_start = datetime.now()
        logger.info(f"\n{'─' * 60}")
        logger.info(f"[步骤3/6] 创建采购单 #{group_idx}/{len(grouped_items)}]")
        logger.info(f"  Supplier ID: {supplier_id}")
        logger.info(f"  Items数: {len(items)}")

        supplier = db.query(SupSupplier).filter(SupSupplier.id == supplier_id).first()
        if not supplier:
            logger.error(f"[❌ 错误] 供应商不存在: {supplier_id}")
            raise ValueError(f"供应商不存在: {supplier_id}")

        logger.info(f"[✅ 供应商验证成功]")
        logger.info(f"  供应商ID: {supplier.id}")
        logger.info(f"  供应商名称: {supplier.supplier_name}")
        logger.info(f"  供应商编号: {supplier.supplier_code}")

        supplier_code = str(supplier.id).zfill(3)
        po_no = NumberGenerator.generate_po_no(db, pi.pi_no, supplier_code)
        logger.info(f"[✅ PO号生成]: {po_no}")

        po_total_amount = sum(_calculate_item_total(item) for item in items)
        # 2026-06-23：po_total_amount 是 float，必须转 Decimal 才能与 Decimal 累加
        po_total_amount = Decimal(str(po_total_amount))
        total_po_amount += po_total_amount

        db_po = PoPurchaseOrder(
            po_no=po_no,
            pi_id=purchase.pi_id,
            supplier_id=supplier_id,
            total_amount=po_total_amount,
            currency=getattr(purchase, 'currency', None) or 'USD',
            status=1,
            dept_id=purchase.dept_id,
        )
        db.add(db_po)
        db.flush()

        logger.info(f"[✅ PO主表创建成功]")
        logger.info(f"  PO_ID: {db_po.id}")
        logger.info(f"  PO_NO: {db_po.po_no}")
        logger.info(f"  总金额: {po_total_amount} USD")

        # 步骤4: 创建PO明细项
        logger.info(f"\n  [步骤4/6] 创建PO明细项 ({len(items)}个)...")
        items_created = 0

        for item_idx, item in enumerate(items, start=1):
            product = db.query(PrdCustomerProduct).filter(PrdCustomerProduct.id == item.product_id).first()
            db.add(_build_purchase_order_item(db_po.id, item, product))
            items_created += 1

            item_total = _calculate_item_total(item)
            logger.info(f"    [Item {item_idx}/{len(items)}]")
            logger.info(f"      Product ID: {item.product_id}")
            logger.info(f"      Quantity: {item.quantity}")
            logger.info(f"      Unit Price: {item.unit_price} USD")
            logger.info(f"      Total: {item_total} USD")
            if product:
                logger.info(f"      Product Model: {product.customer_model}")

        logger.info(f"  [✅ 所有明细项创建完成]: {items_created}/{len(items)} 个")
        created_orders.append(db_po)

        po_duration = (datetime.now() - po_start).total_seconds()
        logger.info(f"  [⏱️ PO创建耗时]: {po_duration:.3f}s")
        logger.info(f"{'─' * 60}\n")

    # 步骤5: 提交事务
    logger.info(f"\n[步骤5/6] 提交数据库事务...")
    db.commit()
    logger.info(f"[✅ 提交成功]")

    # 刷新对象
    logger.info(f"[刷新采购单对象...]")
    for order in created_orders:
        db.refresh(order)
    logger.info(f"[✅ 刷新完成]")

    # 步骤6: 同步回写PI订单项
    logger.info(f"\n[步骤6/6] 同步数据到PI订单项...")
    sync_success_count = 0
    sync_fail_count = 0

    try:
        from models.pi import PiProformaInvoiceItem
        for order in created_orders:
            for item in order.items:  # type: ignore
                pi_item = db.query(PiProformaInvoiceItem).filter(
                    PiProformaInvoiceItem.id == item.pi_item_id
                ).first()
                if pi_item:
                    supplier = db.query(SupSupplier).filter(
                        SupSupplier.id == order.supplier_id
                    ).first()
                    _sync_pi_item_from_po(db, pi_item, item, supplier)
                    db.refresh(pi_item)  # 重新加载同步后的字段
                    sync_success_count += 1
                    logger.debug(f"  同步成功: pi_item_id={pi_item.id}")
    except Exception as sync_err:
        sync_fail_count += 1
        logger.warning(f"[⚠️ PI同步失败] (非阻塞): {sync_err}")

    logger.info(f"[✅ PI同步完成] 成功={sync_success_count}, 失败={sync_fail_count}")

    # 输出最终结果
    purchase_duration = (datetime.now() - purchase_start).total_seconds()
    logger.info(f"\n{'═' * 80}")
    logger.info(f"[✅ 采购订单创建流程完成]")
    logger.info(f"{'═' * 80}")
    logger.info(f"  统计信息:")
    logger.info(f"    创建PO数量: {len(created_orders)}")
    logger.info(f"    总PO金额: {total_po_amount} USD")
    logger.info(f"    总耗时: {purchase_duration:.3f}s")
    logger.info(f"\n  创建的采购单:")
    for idx, order in enumerate(created_orders, start=1):
        logger.info(f"    [{idx}] PO_ID={order.id}, PO_NO={order.po_no}, 金额={order.total_amount} USD, 供应商ID={order.supplier_id}")
    logger.info(f"{'═' * 80}\n")

    return created_orders


def create_purchase_order(db: Session, purchase: PurchaseOrderCreate) -> PoPurchaseOrder:
    orders = create_grouped_purchase_orders(db, purchase)
    if len(orders) != 1:
        raise ValueError("create_purchase_order 仅允许返回单个供应商采购单")
    return orders[0]


def create_purchase_order_legacy(db: Session, purchase: PurchaseOrderCreate) -> PoPurchaseOrder:
    pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == purchase.pi_id).first()
    if not pi:
        raise ValueError("PI不存在")

    supplier = db.query(SupSupplier).filter(SupSupplier.id == purchase.supplier_id).first()
    if not supplier:
        raise ValueError("供应商不存在")

    supplier_code = str(supplier.id).zfill(3)
    po_no = NumberGenerator.generate_po_no(db, pi.pi_no, supplier_code)

    total_amount = sum(item.quantity * item.unit_price for item in purchase.items)

    db_po = PoPurchaseOrder(
        po_no=po_no,
        pi_id=purchase.pi_id,
        supplier_id=purchase.supplier_id,
        total_amount=total_amount,
        currency=getattr(purchase, 'currency', None) or 'USD',
        status=1,
        dept_id=purchase.dept_id
    )

    db.add(db_po)
    db.commit()
    db.refresh(db_po)

    for item in purchase.items:
        product = db.query(PrdCustomerProduct).filter(PrdCustomerProduct.id == item.product_id).first()

        cartons_estimated = 0
        volume_estimated_m3 = 0
        if product and product.carton_volume_m3 and product.units_per_carton:
            cartons_estimated = int(item.quantity / product.units_per_carton) if product.units_per_carton else 0
            volume_estimated_m3 = cartons_estimated * float(product.carton_volume_m3) if product.carton_volume_m3 else 0

        db_item = PoPurchaseOrderItem(
            po_id=db_po.id,
            product_id=item.product_id,
            pi_item_id=item.pi_item_id,
            factory_code=item.factory_code,
            product_image=item.product_image,
            color=item.color,
            detail_requirement=item.detail_requirement,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.quantity * item.unit_price,
            price_ex_factory=item.price_ex_factory,
            price_ex_factory_tax=item.price_ex_factory_tax,
            price_fob=item.price_fob,
            price_fob_tax=item.price_fob_tax,
            cartons_estimated=cartons_estimated,
            volume_estimated_m3=volume_estimated_m3,
            inbound_status=1,  # 默认已采购状态（黄色）
            # 采购费用字段（2026-06-15 新增）
            labeling_fee=item.labeling_fee,
            tax_fee=item.tax_fee,
            shipping_fee=item.shipping_fee,
            freight=item.freight,
        )
        db.add(db_item)

    db.commit()
    db.refresh(db_po)

    return db_po

def get_purchase_order(db: Session, po_id: int) -> PoPurchaseOrder:
    return db.query(PoPurchaseOrder).filter(PoPurchaseOrder.id == po_id).first()

def get_purchase_order_by_no(db: Session, po_no: str) -> PoPurchaseOrder:
    return db.query(PoPurchaseOrder).filter(PoPurchaseOrder.po_no == po_no).first()

def get_purchase_orders(db: Session, skip: int = 0, limit: int = 100, status: int = None, pi_id: int = None):
    query = db.query(PoPurchaseOrder)
    if status is not None:
        query = query.filter(PoPurchaseOrder.status == status)
    if pi_id is not None:
        query = query.filter(PoPurchaseOrder.pi_id == pi_id)
    return query.offset(skip).limit(limit).all()

def get_purchase_orders_by_supplier(db: Session, supplier_id: int):
    return db.query(PoPurchaseOrder).filter(PoPurchaseOrder.supplier_id == supplier_id).all()

def update_purchase_status(db: Session, po_id: int, status: int) -> PoPurchaseOrder:
    db_po = get_purchase_order(db, po_id)
    if not db_po:
        return None

    db_po.status = status
    db.commit()
    db.refresh(db_po)
    return db_po

def update_purchase_order(db: Session, po_id: int, purchase_update) -> PoPurchaseOrder:
    db_po = get_purchase_order(db, po_id)
    if not db_po:
        return None

    if purchase_update.supplier_id is not None:
        supplier = db.query(SupSupplier).filter(SupSupplier.id == purchase_update.supplier_id).first()
        if not supplier:
            raise ValueError("供应商不存在")
        db_po.supplier_id = purchase_update.supplier_id

    if purchase_update.status is not None:
        db_po.status = purchase_update.status

    if purchase_update.items is not None and len(purchase_update.items) > 0:
        db.query(PoPurchaseOrderItem).filter(PoPurchaseOrderItem.po_id == po_id).delete()

        total_amount = 0
        for item in purchase_update.items:
            product = db.query(PrdCustomerProduct).filter(PrdCustomerProduct.id == item.product_id).first()
            total_price = _calculate_item_total(item)
            total_amount += total_price

            db.add(_build_purchase_order_item(po_id, item, product))

        db_po.total_amount = total_amount

    db.commit()
    db.refresh(db_po)
    return db_po

def create_1688_purchase(db: Session, purchase_data):
    db_purchase = Po1688Purchase(
        pi_id=purchase_data.pi_id,
        po_id=purchase_data.po_id,
        product_id=purchase_data.product_id,
        supplier_name=purchase_data.supplier_name,
        product_url=purchase_data.product_url,
        product_remark=purchase_data.product_remark,
        color=purchase_data.color,
        invoice_type=purchase_data.invoice_type,
        labeling_fee=purchase_data.labeling_fee,
        shipping_fee=purchase_data.shipping_fee,
        shipping_method=purchase_data.shipping_method,
        carton_count=purchase_data.carton_count,
        freight=purchase_data.freight,
        payment_method=purchase_data.payment_method,
        gross_weight=purchase_data.gross_weight,
        unit_price=getattr(purchase_data, 'unit_price', None),   # 2026-06-09 任务 5
        tax_fee=getattr(purchase_data, 'tax_fee', None),         # 2026-06-09 任务 5
        status=1
    )
    db.add(db_purchase)
    db.commit()
    db.refresh(db_purchase)
    return db_purchase


def create_1688_purchase_batch(db: Session, batch_data):
    """2026-06-09 任务 5：商品单价并入产品信息 - 一 PI 多产品维度批量创建

    items: List[Po1688PurchaseItem]
    """
    # 2026-06-09 修复 1：空 items 显式拒绝，避免静默"成功提交 0 条"
    items = getattr(batch_data, "items", None) or []
    if not items:
        raise ValueError("items 不能为空")

    # 2026-06-09 修复：移除 dept_id="D01" 死代码（schema 必填，getattr 不会触发默认）
    shared = {
        "dept_id": batch_data.dept_id,
        "po_id": batch_data.po_id,
        "pi_id": batch_data.pi_id,
    }
    created = []
    try:
        for item in items:
            db_purchase = Po1688Purchase(
                **shared,
                product_id=item.product_id,
                supplier_name=item.supplier_name,
                product_url=item.product_url,
                product_remark=item.product_remark,
                color=item.color,
                invoice_type=item.invoice_type,
                labeling_fee=item.labeling_fee,
                shipping_fee=item.shipping_fee,
                shipping_method=item.shipping_method,
                carton_count=item.carton_count,
                freight=item.freight,
                unit_price=item.unit_price,
                tax_fee=item.tax_fee,
                payment_method=item.payment_method,
                gross_weight=item.gross_weight,
                status=1,
            )
            db.add(db_purchase)
            created.append(db_purchase)
        # 2026-06-09 修复 3：批量事务回滚保护 - 任一失败整体回滚
        db.commit()

        # FixPlan Task 3: 线上(1688/微信)采购提交后,同步回写PI订单项
        try:
            from models.pi import PiProformaInvoiceItem
            for p in created:
                # 通过 product_id + pi_id 找到对应的 PI 订单项
                pi_item = db.query(PiProformaInvoiceItem).filter(
                    PiProformaInvoiceItem.pi_id == batch_data.pi_id,
                    PiProformaInvoiceItem.product_id == p.product_id
                ).first()
                if pi_item:
                    _sync_pi_item_from_1688(db, pi_item, p)
                    db.refresh(pi_item)
        except Exception as sync_err_1688:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[purchase] _sync_pi_item_from_1688 failed (non-blocking): {sync_err_1688}")

    except Exception:
        db.rollback()
        created = []
        raise
    for p in created:
        db.refresh(p)
    return created

def get_1688_purchases(db: Session, pi_id: int = None, po_id: int = None, product_id: int = None, skip: int = 0, limit: int = 100):
    query = db.query(Po1688Purchase)
    if pi_id is not None:
        query = query.filter(Po1688Purchase.pi_id == pi_id)
    if po_id is not None:
        query = query.filter(Po1688Purchase.po_id == po_id)
    if product_id is not None:
        query = query.filter(Po1688Purchase.product_id == product_id)
    return query.offset(skip).limit(limit).all()

def get_1688_purchase(db: Session, purchase_id: int):
    return db.query(Po1688Purchase).filter(Po1688Purchase.id == purchase_id).first()

def update_1688_purchase(db: Session, purchase_id: int, purchase_data):
    db_purchase = get_1688_purchase(db, purchase_id)
    if not db_purchase:
        return None

    if purchase_data.supplier_name is not None:
        db_purchase.supplier_name = purchase_data.supplier_name
    if purchase_data.product_url is not None:
        db_purchase.product_url = purchase_data.product_url
    if purchase_data.product_remark is not None:
        db_purchase.product_remark = purchase_data.product_remark
    if purchase_data.color is not None:
        db_purchase.color = purchase_data.color
    if purchase_data.invoice_type is not None:
        db_purchase.invoice_type = purchase_data.invoice_type
    if purchase_data.labeling_fee is not None:
        db_purchase.labeling_fee = purchase_data.labeling_fee
    if purchase_data.shipping_fee is not None:
        db_purchase.shipping_fee = purchase_data.shipping_fee
    if purchase_data.shipping_method is not None:
        db_purchase.shipping_method = purchase_data.shipping_method
    if purchase_data.carton_count is not None:
        db_purchase.carton_count = purchase_data.carton_count
    if purchase_data.freight is not None:
        db_purchase.freight = purchase_data.freight
    if purchase_data.payment_method is not None:
        db_purchase.payment_method = purchase_data.payment_method
    if purchase_data.gross_weight is not None:
        db_purchase.gross_weight = purchase_data.gross_weight
    if purchase_data.status is not None:
        db_purchase.status = purchase_data.status

    db.commit()
    db.refresh(db_purchase)
    return db_purchase

def get_product_latest_purchase(db: Session, product_id: int):
    """获取产品最近一次采购记录（包含费用和发票信息）"""
    # 查询该产品最近的1688采购记录
    latest = db.query(Po1688Purchase).filter(
        Po1688Purchase.product_id == product_id
    ).order_by(Po1688Purchase.created_at.desc()).first()
    
    if not latest:
        return None
    
    # 查询采购订单信息
    po = None
    if latest.po_id:
        po = db.query(PoPurchaseOrder).filter(PoPurchaseOrder.id == latest.po_id).first()
    
    # 查询采购订单明细项（获取采购价等）
    po_item = None
    if latest.po_id:
        po_item = db.query(PoPurchaseOrderItem).filter(
            PoPurchaseOrderItem.po_id == latest.po_id,
            PoPurchaseOrderItem.product_id == product_id
        ).first()
    
    # 构造返回数据
    record = {
        # 基本信息
        "purchase_id": latest.id,
        "po_id": latest.po_id,
        "product_id": product_id,
        "purchase_date": latest.created_at.strftime('%Y-%m-%d') if latest.created_at else None,
        "platform": "1688",

        # 费用信息
        "price": float(po_item.unit_price) if po_item and po_item.unit_price else 0,
        "unit_price": float(latest.unit_price) if latest.unit_price else (float(po_item.unit_price) if po_item and po_item.unit_price else 0),  # 2026-06-09 任务 4
        "labeling_fee": float(latest.labeling_fee) if latest.labeling_fee else 0,
        "tax_fee": float(latest.tax_fee) if latest.tax_fee else 0,  # 2026-06-09 任务 4：从 Po1688Purchase 读
        "shipping_fee": float(latest.shipping_fee) if latest.shipping_fee else 0,
        "freight": float(latest.freight) if latest.freight else 0,

        # 链接信息
        "link": latest.product_url,

        # 发票信息
        "invoice_type": latest.invoice_type,
        "has_invoice": latest.invoice_type is not None and latest.invoice_type != "",

        # 供应商信息
        "supplier_name": latest.supplier_name,

        # 备注
        "remark": latest.product_remark,
    }
    
    return record
