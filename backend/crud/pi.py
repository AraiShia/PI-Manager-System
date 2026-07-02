from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
from models import (
    PiProformaInvoice,
    PiProformaInvoiceItem,
    PiPaymentStage,
    PiProformaInvoiceVersion,
    PiPriceHistory,
    CrmCustomer,
    SupSupplier,
    PoPurchaseOrderItem,
    Po1688Purchase,
    PoInboundBatch,
)
from schemas import PIInvoiceCreate, PIInvoiceUpdate
from utils.number_generator import NumberGenerator
# Phase 4/5: 统一产品访问（Phase 5 移除 PrdProduct fallback）
from services.product_lookup import unified_product_lookup
# FixPlan Task 3: 导入入库同步函数
from crud.pi_sync import _sync_pi_item_from_inbound
import os

def create_pi_invoice(db: Session, pi: PIInvoiceCreate) -> PiProformaInvoice:
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == pi.customer_id).first()
    if not customer:
        raise ValueError("客户不存在")
    
    pi_no = NumberGenerator.generate_pi_no(db, pi.dept_id, customer.customer_code)
    
    total_amount = sum(item.quantity * item.unit_price for item in pi.items)
    
    db_pi = PiProformaInvoice(
        pi_no=pi_no,
        dept_id=pi.dept_id,
        customer_id=pi.customer_id,
        total_amount=total_amount,
        currency=pi.currency,
        status=1
    )
    
    db.add(db_pi)
    db.commit()
    db.refresh(db_pi)
    
    for item in pi.items:
        total_price = item.quantity * item.unit_price
        
        db_item = PiProformaInvoiceItem(
            pi_id=db_pi.id,
            product_id=item.product_id,
            oe_number=item.oe_number,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=total_price,
            customer_code=item.customer_code,
            detail_desc=item.detail_desc,
            remark=item.remark
        )
        db.add(db_item)
        
        price_history = PiPriceHistory(
            dept_id=pi.dept_id,
            customer_id=pi.customer_id,
            product_id=item.product_id,
            pi_id=db_pi.id,
            unit_price=item.unit_price,
            remark=item.remark
        )
        db.add(price_history)
    
    for stage in pi.payment_stages:
        db_stage = PiPaymentStage(
            pi_id=db_pi.id,
            stage_type=stage.stage_type,
            stage_no=stage.stage_no,
            amount=stage.amount,
            due_date=stage.due_date,
            status=1
        )
        db.add(db_stage)
    
    db.commit()
    db.refresh(db_pi)
    
    return db_pi

def get_pi_invoice(db: Session, pi_id: int) -> PiProformaInvoice:
    return db.query(PiProformaInvoice).filter(PiProformaInvoice.id == pi_id).first()

def get_pi_invoice_by_no(db: Session, pi_no: str) -> PiProformaInvoice:
    return db.query(PiProformaInvoice).filter(PiProformaInvoice.pi_no == pi_no).first()

def get_pi_invoices(db: Session, skip: int = 0, limit: int = 100):
    return db.query(PiProformaInvoice).offset(skip).limit(limit).all()

def update_pi_status(db: Session, pi_id: int, status: int) -> PiProformaInvoice:
    db_pi = get_pi_invoice(db, pi_id)
    if not db_pi:
        raise ValueError("PI不存在")
    db_pi.status = status
    db.commit()
    return db_pi

def delete_pi_invoice(db: Session, pi_id: int):
    """删除PI订单

    2026-07-02: 临时产品功能已去除，所有 PI 项均视为正式记录，
    删除时不再区分草稿/正式，直接执行删除。

    2026-06-15 Bug 修复：删除 items/payment_stages 改用 ORM cascade，
    不再手动 db.query(...).delete()，避免与 cascade 冲突触发 SQLAlchemy
    StaleDataError → 500。
    """
    db_pi = get_pi_invoice(db, pi_id)
    if not db_pi:
        raise ValueError("PI不存在")
    # 依赖 Pi.items / Pi.payment_stages 关系上的 cascade="all, delete-orphan"，
    # ORM 会自动删除关联明细和付款阶段，不要手动 db.query(...).delete()
    db.delete(db_pi)
    db.commit()

def get_price_history(db: Session, customer_id: int, product_id: int):
    return db.query(PiPriceHistory).filter(
        PiPriceHistory.customer_id == customer_id,
        PiPriceHistory.product_id == product_id
    ).order_by(PiPriceHistory.created_at.desc()).first()

def update_pi_invoice(db: Session, pi_id: int, pi_update: PIInvoiceUpdate) -> PiProformaInvoice:
    db_pi = get_pi_invoice(db, pi_id)
    if not db_pi:
        return None
    
    if pi_update.customer_id is not None:
        customer = db.query(CrmCustomer).filter(CrmCustomer.id == pi_update.customer_id).first()
        if not customer:
            raise ValueError("客户不存在")
        db_pi.customer_id = pi_update.customer_id
    
    if pi_update.currency is not None:
        db_pi.currency = pi_update.currency
    
    if pi_update.status is not None:
        db_pi.status = pi_update.status
    
    if pi_update.items is not None and len(pi_update.items) > 0:
        db.query(PiProformaInvoiceItem).filter(PiProformaInvoiceItem.pi_id == pi_id).delete()
        
        total_amount = 0
        for item in pi_update.items:
            total_price = item.quantity * item.unit_price
            total_amount += total_price
            
            db_item = PiProformaInvoiceItem(
                pi_id=pi_id,
                product_id=item.product_id,
                oe_number=item.oe_number,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=total_price,
                customer_code=item.customer_code,
                detail_desc=item.detail_desc,
                remark=item.remark
            )
            db.add(db_item)
        
        db_pi.total_amount = total_amount
    
    # 处理付款阶段更新
    if pi_update.payment_stages is not None:
        db.query(PiPaymentStage).filter(PiPaymentStage.pi_id == pi_id).delete()
        for stage in pi_update.payment_stages:
            db_stage = PiPaymentStage(
                pi_id=pi_id,
                stage_type=stage.stage_type,
                stage_no=stage.stage_no,
                amount=stage.amount,
                due_date=stage.due_date,
                status=1
            )
            db.add(db_stage)
    
    db.commit()
    db.refresh(db_pi)
    
    # 2026-06-23: PI 正式保存后，为每个 item 创建采购在途库存记录（黄）
    if pi_update.items and len(pi_update.items) > 0:
        _sync_inventory_for_pi(db, pi_id, db_pi.customer_id)
    
    return db_pi


def _sync_inventory_for_pi(db: Session, pi_id: int, customer_id: int):
    """PI 保存后同步创建/更新库存记录
    
    遍历 PI 的所有 item，为每个 item 创建采购在途库存（黄）。
    已存在则跳过（防重复）。
    """
    from crud.inventory import create_inventory_for_pi_item
    items = db.query(PiProformaInvoiceItem).filter(
        PiProformaInvoiceItem.pi_id == pi_id
    ).all()
    
    for item in items:
        try:
            create_inventory_for_pi_item(
                db=db,
                product_id=item.product_id,
                customer_id=customer_id,
                pi_id=pi_id,
                quantity=float(item.quantity or 0),
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"[_sync_inventory] PI={pi_id} item={item.id} product={item.product_id} "
                f"创建库存失败: {e}"
            )


def _compute_order_storage_status(db: Session, pi_id: int, items: list) -> str:
    """2026-06-23 收敛：订单级 storage_status 统一计算

    数据源：inv_inventory.total_quantity 聚合（保持原业务口径）。
    期望总数：所有 PI item 的 quantity 之和。
    判定：见 crud.storage_status.StorageStatus.from_order_inventory。
    """
    from crud.storage_status import StorageStatus
    expected_total = float(sum(float(getattr(i, "quantity", 0) or 0) for i in items))
    return StorageStatus.from_order_inventory(
        db, pi_id=pi_id, expected_total=expected_total
    )


def get_pi_invoice_detail(db: Session, pi_id: int):
    """获取PI详情，包含明细项、付款阶段、客户信息 - v1.1支持41列全覆盖
    
    2026-06-22 修复：添加 db.refresh() 确保读取最新数据
    问题现象：保存后立即查询，packaging等字段仍为None
    根因：SQLAlchemy session缓存导致读取到旧对象
    """
    db_pi = get_pi_invoice(db, pi_id)
    if not db_pi:
        return None
    
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == db_pi.customer_id).first()
    
    # 🔧 2026-06-22 修复：使用 expire_all() 清除缓存，确保从数据库读取最新数据
    # 解决保存后立即刷新时字段仍为空的问题
    db.expire_all()
    
    items = db.query(PiProformaInvoiceItem).filter(PiProformaInvoiceItem.pi_id == pi_id).all()
    
    # 🔍 DEBUG: 记录查询到的item数量和关键字段值（调试用）
    if items:
        print(f"[DEBUG-get_pi_detail] 查询到 {len(items)} 个订单项")
        for idx, item in enumerate(items[:3]):  # 只显示前3个
            packaging_val = getattr(item, 'packaging', None)
            purchase_val = getattr(item, 'purchase_option_name', None)
            print(f"[DEBUG-get_pi_detail]   items[{idx}] id={item.id}: packaging={packaging_val}, purchase_option_name={purchase_val}")
    
    stages = db.query(PiPaymentStage).filter(PiPaymentStage.pi_id == pi_id).order_by(PiPaymentStage.id).all()
    
    result_items = []
    for item in items:
        result_items.append(_build_item_detail_v11(db, item, customer, db_pi.created_at))
    
    return {
        "id": db_pi.id,
        "dept_id": db_pi.dept_id,
        "pi_no": db_pi.pi_no,
        "customer_id": db_pi.customer_id,
        "customer_name": customer.customer_name if customer else None,
        "customer_code": customer.customer_code if customer else None,
        "total_amount": float(db_pi.total_amount) if db_pi.total_amount else 0,
        "currency": db_pi.currency or "USD",
        "status": db_pi.status or 1,
        "created_at": db_pi.created_at.isoformat() if db_pi.created_at else None,
        "updated_at": db_pi.updated_at.isoformat() if db_pi.updated_at else None,
        # 2026-06-23 收敛：订单级 storage_status 改用 crud.storage_status.StorageStatus，
        # 与 routers/pi.py:78 列表端点同源，避免两处逻辑各写一份。
        # 期望总数量 = 所有 PI item 的 quantity 之和；inv_inventory.total_quantity 聚合后比较。
        "storage_status": _compute_order_storage_status(db, pi_id, items),
        "items": result_items,
        "payment_stages": [
            {
                "id": s.id,
                "stage_type": s.stage_type,
                "stage_no": s.stage_no,
                "amount": float(s.amount),
                "due_date": s.due_date.isoformat()[:10] if s.due_date else None,
                "paid_date": s.paid_date.isoformat()[:10] if s.paid_date else None,
                "status": s.status or 1,
                "created_at": s.created_at.isoformat() if s.created_at else None
            }
            for s in stages
        ]
    }

def _build_item_detail_v11(db: Session, item: PiProformaInvoiceItem, customer: CrmCustomer, pi_created_at=None) -> dict:
    """构建订单项详细数据 - v1.2版本，优先使用快照字段回退关联查询

    FixPlan Task 4: 21个新字段全部优先 item.<field> 快照，None 时回退关联查询
    满足报告 Risk 1-2: 采购/入库数据即使 PO 改了, PI 详情仍显示回写时的快照

    Args:
        db: 数据库会话
        item: 订单项
        customer: 客户
        pi_created_at: 订单创建时间（从PiProformaInvoice传入）
    """
    # 2026-06-23 收敛：storage_status 三值标准化（兼容 DB 旧值）
    from crud.storage_status import StorageStatus

    # Phase 4: 使用统一产品访问，优先 prd_customer_product，兼容 prd_product
    product = unified_product_lookup(
        db,
        item.product_id,
        customer_id=customer.id if customer else None,
    )

    # Phase 5: customer_model 优先取 item 自身字段（导入时直接写入），
    # 其次从产品的 customer_model 字段取
    customer_model = getattr(item, 'customer_model', None) or item.detail_desc
    if not customer_model and product:
        customer_model = product.oe_number  # UnifiedProduct.oe_number -> customer_model

    # Phase 5: 供应商信息从 PoPurchaseOrderItem 取
    po_item = db.query(PoPurchaseOrderItem).filter(
        PoPurchaseOrderItem.pi_item_id == item.id
    ).order_by(PoPurchaseOrderItem.id.desc()).first()
    # 1688店铺链接：从 Po1688Purchase 获取最近一次的 product_url
    po_1688 = db.query(Po1688Purchase).filter(
        Po1688Purchase.pi_id == item.pi_id,
        Po1688Purchase.product_id == item.product_id
    ).order_by(Po1688Purchase.id.desc()).first()
    po_supplier_name = None
    po_shop_url = po_1688.product_url if po_1688 else None
    po_delivery_date = None
    po_received_status = None
    po_warehouse_action = None
    po_warehouse_qty = None
    po_currency = None
    if po_item and po_item.po:
        po = po_item.po
        po_currency = getattr(po, 'currency', None) or 'USD'
        po_sup = db.query(SupSupplier).filter(SupSupplier.id == po.supplier_id).first()
        if po_sup:
            po_supplier_name = po_sup.supplier_name
        po_delivery_date = po.contract_date.strftime("%Y-%m-%d") if po.contract_date else None
        # inbound_status: 1=已采购(黄), 2=已入库(黑)
        po_received_status = "已收货" if po_item.inbound_status == 2 else ("已采购" if po_item.inbound_status == 1 else None)
        po_warehouse_action = "已入库" if po_item.inbound_status == 2 else ("已采购" if po_item.inbound_status == 1 else None)
    # 入库数量：从 PoInboundBatch（入库Dialog）获取实际入库数量，按 po_id + product_id 聚合
    if po_item and po_item.po_id:
        from sqlalchemy import func
        inbound_total = db.query(func.coalesce(func.sum(PoInboundBatch.quantity), 0)).filter(
            PoInboundBatch.po_id == po_item.po_id,
            PoInboundBatch.product_id == item.product_id,
            PoInboundBatch.status == 2  # 已验收
        ).scalar()
        po_warehouse_qty = float(inbound_total) if inbound_total and float(inbound_total) > 0 else None

    # 2026-06-15: 获取包装规格数据
    po_item_id = po_item.id if po_item else None
    package_data = {}
    package_obj = None
    if po_item_id:
        from crud.purchase_package import get_package_by_po_item
        package = get_package_by_po_item(db, po_item_id)
        if package:
            package_data = {
                "purchase_channel": package.purchase_channel,
                "carton_length_cm": float(package.carton_length_cm) if package.carton_length_cm else None,
                "carton_width_cm": float(package.carton_width_cm) if package.carton_width_cm else None,
                "carton_height_cm": float(package.carton_height_cm) if package.carton_height_cm else None,
                "units_per_carton": package.units_per_carton,
                "gross_weight_kg": float(package.gross_weight_kg) if package.gross_weight_kg else None,
                "boxes_count": package.boxes_count,
                "packing_type": package.packing_type,
            }
            # 用 SimpleNamespace 包装，让 helper 函数统一用 getattr 访问
            from types import SimpleNamespace
            package_obj = SimpleNamespace(**package_data)

    image_url = None
    if product and product.image_url:
        image_url = product.image_url

    # ============================================================
    # FixPlan Task 4: 快照字段优先策略
    # 所有 21 个新字段：优先 item.<field> 快照，None 时回退关联查询
    # ============================================================

    def _snapshot_or_fallback(snapshot_value, fallback_value):
        """
        辅助函数：优先使用快照值，None时回退到关联查询值
        
        Args:
            snapshot_value: item.<field> 快照字段值
            fallback_value: 关联查询的回退值
            
        Returns:
            优先返回 snapshot_value，否则 fallback_value
        """
        return snapshot_value if snapshot_value is not None else fallback_value

    # 2026-06-26: 统一采购价（快照优先），供 col 15/16/20 计算使用
    _purchase_price = _snapshot_or_fallback(
        getattr(item, 'purchase_price', None) and float(getattr(item, 'purchase_price', None)),
        float(package_obj.purchase_price) if package_obj and getattr(package_obj, 'purchase_price', None) else None
    )

    detail = {
        # === 元数据 ===
        "id": item.id,
        "product_id": item.product_id,
        "po_item_id": po_item_id,  # 2026-06-15: 添加采购单项ID用于保存包装规格
        
        # === 包装规格数据 (2026-06-15) ===
        # FixPlan Task 4: 优先快照字段，回退 package_data
        "purchase_channel": _snapshot_or_fallback(
            getattr(item, 'purchase_channel', None),
            package_data.get("purchase_channel")
        ),
        "carton_length_cm": _snapshot_or_fallback(
            getattr(item, 'carton_length_cm', None) and float(getattr(item, 'carton_length_cm', None)),
            package_data.get("carton_length_cm")
        ),
        "carton_width_cm": _snapshot_or_fallback(
            getattr(item, 'carton_width_cm', None) and float(getattr(item, 'carton_width_cm', None)),
            package_data.get("carton_width_cm")
        ),
        "carton_height_cm": _snapshot_or_fallback(
            getattr(item, 'carton_height_cm', None) and float(getattr(item, 'carton_height_cm', None)),
            package_data.get("carton_height_cm")
        ),
        "units_per_carton": _snapshot_or_fallback(
            getattr(item, 'units_per_carton', None),
            package_data.get("units_per_carton")
        ),
        "gross_weight_kg": _snapshot_or_fallback(
            getattr(item, 'gross_weight_kg', None) and float(getattr(item, 'gross_weight_kg', None)),
            package_data.get("gross_weight_kg")
        ),
        "boxes_count": _snapshot_or_fallback(
            getattr(item, 'boxes_count', None),
            package_data.get("boxes_count")
        ),
        "packing_type": _snapshot_or_fallback(
            getattr(item, 'packing_type', None) or getattr(item, 'packaging', None),
            package_data.get("packing_type")
        ),

        # === A组: 基础信息 (列0-9) ===
        "order_date": pi_created_at.strftime("%Y-%m-%d")[:10] if pi_created_at else None,
        "order_no": None,
        "customer_code": item.customer_code,
        # 产品名称：优先产品表，其次描述
        "product_name": product.product_name if product else item.detail_desc,
        "product_code": product.system_code if product else None,  # 系统编号, e.g., C02260000
        "oe_number": item.oe_number or (product.oe_number if product else None),
        "remark": item.remark,
        "detail_desc": item.detail_desc or (product.detail_desc if product else None),
        # 规格参数：从产品表获取
        "specification": getattr(product, 'specifications', None) if product else None,
        # 图片URL
        "image_url": image_url,
        "photo": image_url,  # 导出模板用 photo 字段
        # 颜色：从产品表或采购单获取
        "color": getattr(product, 'color', None) if product else (getattr(po_item, 'color', None) if po_item else None),
        "customer_model": customer_model,
        "product_feature": None,

        # === B组: 价格与财务 (列9-20) ===
        "quantity": float(item.quantity),
        "unit_price": float(item.unit_price),
        "total_price": float(item.total_price),
        "customer_reply": None,
        # FixPlan Task 4: prepayment/remaining_payment 优先快照字段
        "prepayment": _snapshot_or_fallback(
            getattr(item, 'customer_prepayment', None) and float(getattr(item, 'customer_prepayment', None)),
            None
        ),
        "remaining_payment": _snapshot_or_fallback(
            getattr(item, 'remaining_payment', None) and float(getattr(item, 'remaining_payment', None)),
            None
        ),
        # Fix 2026-06-23: col 15/16 用真实数据计算
        # Excel列15: 预估美金报价 = 采购价 × (1 + 基础毛利率) / 汇率
        # Excel列16: 预估毛利率 = 客户美金报价 × 汇率 / 采购总金额 × 100%
        # FixPlan Task 4: 采购价/运费/杂费 优先快照字段
        "purchase_price": _snapshot_or_fallback(
            getattr(item, 'purchase_price', None) and float(getattr(item, 'purchase_price', None)),
            float(package_obj.purchase_price) if package_obj and getattr(package_obj, 'purchase_price', None) else None
        ),
        "shipping_fee": _snapshot_or_fallback(
            getattr(item, 'shipping_fee', None) and float(getattr(item, 'shipping_fee', None)),
            None
        ),
        "misc_fee": _snapshot_or_fallback(
            getattr(item, 'misc_fee', None) and float(getattr(item, 'misc_fee', None)),
            None
        ),
        # Fix 2026-06-23: col 15/16 用真实数据计算
        # Excel列15: 预估美金报价 = 采购价 × (1 + 基础毛利率) / 汇率（RMB采购）或 ×(1+毛利率)（USD采购）
        "estimated_usd": _calculate_estimated_usd(
            _purchase_price,
            20.0,  # 基础毛利率 20%
            6.8,   # 默认汇率 6.8
            po_currency or 'RMB'
        ),
        # Excel列16: 预估毛利率 = (客户总收入 - 采购总成本) / 客户总收入 × 100%
        "profit_margin": _calculate_profit_margin(
            float(item.unit_price) if item.unit_price else None,
            6.8,  # 默认汇率
            _calculate_total_order_amount(
                _purchase_price,
                float(item.quantity) if item.quantity else None,
                _snapshot_or_fallback(
                    getattr(item, 'shipping_fee', None) and float(getattr(item, 'shipping_fee', None)),
                    None
                ),
                _snapshot_or_fallback(
                    getattr(item, 'misc_fee', None) and float(getattr(item, 'misc_fee', None)),
                    None
                )
            ),
            po_currency or 'RMB',
            float(item.quantity) if item.quantity else 0
        ),
        # FixPlan Task 4: 新增总订单金额字段（采购总金额）
        # Excel列20: 总金额 = 采购价 × 采购数 + 运费 + 杂费
        "total_order_amount": _snapshot_or_fallback(
            getattr(item, 'total_order_amount', None) and float(getattr(item, 'total_order_amount', None)),
            # 动态计算: 优先 item 自身快照字段，fallback 采购单包装规格
            _calculate_total_order_amount(
                getattr(item, 'purchase_price', None) and float(getattr(item, 'purchase_price', None)) or (float(package_obj.purchase_price) if package_obj and getattr(package_obj, 'purchase_price', None) else None),
                item.quantity,
                getattr(item, 'shipping_fee', None) and float(getattr(item, 'shipping_fee', None)) or (float(package_obj.shipping_fee) if package_obj and getattr(package_obj, 'shipping_fee', None) else None),
                getattr(item, 'misc_fee', None) and float(getattr(item, 'misc_fee', None)) or (float(package_obj.misc_fee) if package_obj and getattr(package_obj, 'misc_fee', None) else None)
            )
        ),
        "total_amount": float(item.total_price),

        # === C组: 供应商与采购 (列21-26) — 优先快照字段，fallback 关联查询 ===
        "supplier_name": _snapshot_or_fallback(
            getattr(item, 'supplier_name', None),
            po_supplier_name
        ),
        "shop_url": _snapshot_or_fallback(
            getattr(item, 'shop_url', None),
            po_shop_url
        ),
        "delivery_date": _snapshot_or_fallback(
            getattr(item, 'delivery_date', None) and (
                getattr(item, 'delivery_date', None).strftime("%Y-%m-%d") 
                if hasattr(getattr(item, 'delivery_date', None), 'strftime') 
                else str(getattr(item, 'delivery_date', None))
            ) if getattr(item, 'delivery_date', None) else None,
            po_delivery_date
        ),
        "received_status": po_received_status,
        # FixPlan Task 4: 定金/尾款 优先快照字段
        "factory_deposit": _snapshot_or_fallback(
            getattr(item, 'factory_deposit', None) and float(getattr(item, 'factory_deposit', None)),
            None  # 留空：历史数据无此字段
        ),
        "factory_balance": _snapshot_or_fallback(
            getattr(item, 'factory_balance', None) and float(getattr(item, 'factory_balance', None)),
            None  # 留空：历史数据无此字段
        ),

        # === D组: 物流入库 (列27-29) ===
        # 2026-06-23 收敛：删除 warehouse_action/warehouse_qty 别名，只暴露 storage_status/stocked_qty。
        # 通过 StorageStatus.normalize 兼容 DB 旧值（已采购/× 未入库/有库/partial/已部分入库）。
        "storage_status": StorageStatus.normalize(_snapshot_or_fallback(
            getattr(item, 'storage_status', None),
            po_warehouse_action
        )),
        "stocked_qty": _snapshot_or_fallback(
            getattr(item, 'stocked_qty', None) and float(getattr(item, 'stocked_qty', None)),
            po_warehouse_qty
        ),
        # Excel列29: 包装方式 - 优先快照字段 item.packaging，fallback packaging_method 或 packing_type
        "packaging": _snapshot_or_fallback(
            getattr(item, 'packaging', None),
            package_data.get("packing_type")
        ),
        "packaging_method": None,  # 保留兼容性
        
        # === E组: 产品细节 (列30-38) ===
        # FixPlan Task 4: purchase_option 重命名为 purchase_option_name 对齐 UI
        "purchase_option_name": _snapshot_or_fallback(
            getattr(item, 'purchase_option_name', None),
            None
        ),
        "product_detail": None,
        # FixPlan Task 4: 工厂编号 优先快照字段
        "factory_no": _snapshot_or_fallback(
            getattr(item, 'factory_code', None),
            package_obj.factory_code if package_obj and getattr(package_obj, 'factory_code', None) else (product.factory_code if product else None)
        ),
        # 2026-06-23 修复：carton_size 优先从 PI item 自身读取（update_pi_item 派生写入的），
        # 再 fallback 到 package/product。原来的写法完全忽略 item.carton_size，导致
        # 总表 Col 33 永远拿不到用户刚保存的纸箱尺寸
        "carton_size": (
            getattr(item, 'carton_size', None)
            or _format_carton_size(package_obj or product)
        ),
        # Excel列34: 打包规格 = 每个纸箱的装入产品数量
        "packing_spec": _snapshot_or_fallback(
            getattr(item, 'pack_spec', None),
            # 2026-06-23 修复：fallback 链加 packaging 派生
            # 1) 采购单 package_obj 的 units_per_carton
            # 2) product.units_per_carton
            # 3) item.packaging 派生（"1件/箱" / "1件多箱"+carton_count）
            _format_packing_spec_display(
                package_obj.units_per_carton if package_obj and getattr(package_obj, 'units_per_carton', None) else
                (getattr(product, 'units_per_carton', None) if product else None)
            ) or _derive_pack_spec_from_packaging(
                getattr(item, 'packaging', None),
                getattr(item, 'carton_count', None)
            )
        ),
        # Excel列35: 箱数 = 向上取整(数量 / 每箱装入数量)
        "carton_count": _snapshot_or_fallback(
            getattr(item, 'carton_count', None) and int(getattr(item, 'carton_count', None)),
            _calculate_carton_count(
                item.quantity,
                package_obj or product
            )
        ),
        # Excel列36: 预估体积 = 箱数 × 单箱体积 (m³)
        "estimated_volume": _snapshot_or_fallback(
            getattr(item, 'estimated_volume', None) and float(getattr(item, 'estimated_volume', None)),
            _calculate_estimated_volume(
                item.quantity,
                package_obj or product
            )
        ),
        # Excel列37: 整箱毛重 (kg) - 优先快照，fallback 包装规格/产品表
        "carton_gross_weight": _snapshot_or_fallback(
            getattr(item, 'carton_gross_weight', None) and float(getattr(item, 'carton_gross_weight', None)),
            float(package_obj.gross_weight_kg) if package_obj and getattr(package_obj, 'gross_weight_kg', None) else (float(product.gross_weight_kg) if product and product.gross_weight_kg else None)
        ),
        # Excel列38: 总重量 = 箱数 × 整箱毛重 (kg)
        "total_weight": _snapshot_or_fallback(
            getattr(item, 'total_weight', None) and float(getattr(item, 'total_weight', None)),
            _calculate_total_weight(
                item.quantity,
                package_obj or product
            )
        ),
        
        # === F组: 其他属性 (列39-40) ===
        # FixPlan Task 4: 品牌 优先快照字段
        "brand": _snapshot_or_fallback(
            getattr(item, 'brand', None),
            product.brand if product else None
        ),
        # 2026-06-23：注入产品默认报价，前端 col 10 报价列 fallback 用
        "price_rmb": float(product.price_rmb) if product and getattr(product, 'price_rmb', None) else None,
        "price_usd": float(product.price_usd) if product and getattr(product, 'price_usd', None) else None,
        "invoice_status": None
    }
    
    # 2026-06-26 修复："1件多箱"模式下，DB 的 carton_count 存的是"每件商品箱数"，
    # 需要乘以数量得到总箱数、总体积、总重量
    packaging_val = detail.get("packaging")
    if packaging_val == "1件多箱":
        carton_count_per_piece = int(getattr(item, 'carton_count', None) or 0)
        qty = int(item.quantity or 0)
        if carton_count_per_piece > 0 and qty > 0:
            total_cartons = qty * carton_count_per_piece
            detail["carton_count"] = total_cartons
            # 保留每件箱数，供前端编辑对话框回填"件数设置"
            detail["boxes_count"] = carton_count_per_piece

            # 单箱体积 (m³)
            carton_volume_m3 = getattr(item, 'carton_volume_m3', None) or _parse_carton_size_to_m3(detail.get("carton_size"))
            if carton_volume_m3:
                detail["estimated_volume"] = round(float(carton_volume_m3) * total_cartons, 4)

            # 单箱毛重 (kg)
            gross_weight = detail.get("carton_gross_weight")
            if gross_weight:
                detail["total_weight"] = round(float(gross_weight) * total_cartons, 2)

    return detail


def _parse_carton_size_to_m3(carton_size: Optional[str]) -> Optional[float]:
    """从纸箱尺寸字符串解析单箱体积(m³)，例如 '20x20x20cm' -> 0.008"""
    if not carton_size:
        return None
    import re
    parts = re.findall(r'\d+(?:\.\d+)?', str(carton_size))
    if len(parts) >= 3:
        try:
            l, w, h = map(float, parts[:3])
            return round(l * w * h / 1_000_000, 6)
        except (TypeError, ValueError):
            pass
    return None


def _format_carton_size(product_obj) -> str:
    """格式化纸箱尺寸"""
    if not product_obj:
        return None
    
    length = getattr(product_obj, 'carton_length_cm', None)
    width = getattr(product_obj, 'carton_width_cm', None)
    height = getattr(product_obj, 'carton_height_cm', None)
    
    if length and width and height:
        return f"{float(length):.0f}x{float(width):.0f}x{float(height):.0f}cm"
    return None

def _calculate_carton_count(quantity: float, product_obj) -> int:
    """计算箱数"""
    if not quantity or not product_obj:
        return None
    
    units_per_carton = getattr(product_obj, 'units_per_carton', None)
    if units_per_carton and units_per_carton > 0:
        import math
        return math.ceil(float(quantity) / units_per_carton)
    return None

def _calculate_estimated_volume(quantity: float, product_obj) -> float:
    """计算预估体积"""
    if not quantity or not product_obj:
        return None
    
    carton_volume = getattr(product_obj, 'carton_volume_m3', None)
    if carton_volume:
        carton_count = _calculate_carton_count(quantity, product_obj)
        if carton_count:
            return round(float(carton_volume) * carton_count, 4)
    return None

def _calculate_total_weight(quantity: float, product_obj) -> float:
    """计算总重量"""
    if not quantity or not product_obj:
        return None

    gross_weight = getattr(product_obj, 'gross_weight_kg', None)
    if gross_weight:
        carton_count = _calculate_carton_count(quantity, product_obj)
        if carton_count:
            return round(float(gross_weight) * carton_count, 2)
    return None


# ============== 动态计算函数 (基于Excel订单管理总表规则) ==============

def _calculate_total_order_amount(
    purchase_price: float,
    quantity: float,
    shipping_fee: float = 0,
    misc_fee: float = 0
) -> float:
    """
    计算采购总金额 (Excel列20)

    公式: 总金额 = 采购价 × 采购数 + 运费 + 杂费

    Args:
        purchase_price: 采购单价
        quantity: 采购数量
        shipping_fee: 运费 (默认0)
        misc_fee: 杂费 (默认0)

    Returns:
        float: 采购总金额, 保留2位小数; 如果参数缺失返回None

    示例:
        >>> _calculate_total_order_amount(95, 50, 100, 20)
        4870.0  # 95*50 + 100 + 20
    """
    if None in [purchase_price, quantity]:
        return None

    try:
        total = float(purchase_price) * float(quantity) + \
                float(shipping_fee or 0) + \
                float(misc_fee or 0)
        return round(total, 2)
    except (TypeError, ValueError):
        return None


def _calculate_estimated_usd(
    factory_price: float,
    profit_margin: float,
    exchange_rate: float = 6.8,
    purchase_currency: str = 'RMB'
) -> float:
    """
    计算预估美金报价 (Excel列15)

    公式:
        - 人民币采购: 预估美金报价 = 采购价 × (1 + 毛利率) / 汇率
        - 美元采购:   预估美金报价 = 采购价 × (1 + 毛利率)

    Args:
        factory_price: 采购价格
        profit_margin: 基础毛利率 (百分比, 如30表示30%)
        exchange_rate: 人民币兑美元汇率 (默认6.8)
        purchase_currency: 采购币种 (RMB/USD), 默认 RMB

    Returns:
        float: 预估美金报价 (USD), 保留4位小数
    """
    if None in [factory_price, profit_margin]:
        return None

    try:
        margin_factor = 1 + float(profit_margin) / 100.0
        if purchase_currency and purchase_currency.upper() == 'USD':
            usd_price = float(factory_price) * margin_factor
        else:
            usd_price = float(factory_price) * margin_factor / float(exchange_rate)
        return round(usd_price, 4)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _calculate_profit_margin(
    unit_price_usd: float,
    exchange_rate: float,
    total_order_amount: float,
    purchase_currency: str = 'RMB',
    quantity: float = 0
) -> float:
    """
    计算预估毛利率 (Excel列16)

    公式: 毛利率 = (客户总收入 - 采购总成本) / 客户总收入 × 100%
        - 客户总收入 = 客户美金报价 × 数量 (USD)
        - 采购总成本：USD采购直接用；RMB采购需除以汇率

    Args:
        unit_price_usd: 客户美金报价 (USD)
        exchange_rate: 汇率 (如6.8)
        total_order_amount: 采购总金额
        purchase_currency: 采购币种 (RMB/USD), 默认 RMB
        quantity: 客户订单数量

    Returns:
        float: 毛利率 (百分比), 保留2位小数
    """
    if None in [unit_price_usd, exchange_rate, total_order_amount]:
        return None
    if unit_price_usd == 0 or quantity == 0 or total_order_amount == 0:
        return None

    try:
        # 客户总收入 (USD)
        total_revenue_usd = float(unit_price_usd) * float(quantity)

        # 采购总成本 (USD)
        if purchase_currency and purchase_currency.upper() == 'USD':
            cost_usd = float(total_order_amount)
        else:
            cost_usd = float(total_order_amount) / float(exchange_rate)

        # 毛利率 = (收入 - 成本) / 收入 × 100%
        margin = (total_revenue_usd - cost_usd) / total_revenue_usd * 100
        return round(margin, 2)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _calculate_cart_enhanced(
    quantity: float,
    units_per_carton: float,
    packing_spec: str = None
) -> dict:
    """
    增强版箱数/体积/重量计算 (Excel列35-38)

    综合计算以下字段:
    - carton_count: 箱数 (向上取整)
    - estimated_volume: 预估体积 (m³)
    - total_weight: 总重量 (kg)

    数据来源优先级:
    1. PI订单项快照字段 (如果已同步)
    2. 包装规格表 (po_package)
    3. 产品主表 (prd_customer_product)
    4. 实时计算 (基于units_per_carton)

    Args:
        quantity: 订单数量
        units_per_carton: 每箱装入数量 (来自打包规格)
        packing_spec: 打包规格字符串 (可选, 用于解析)

    Returns:
        dict: {
            'carton_count': int or None,
            'estimated_volume': float or None,
            'total_weight': float or None
        }

    示例:
        >>> result = _calculate_cart_enhanced(50, 10)
        >>> print(result)
        {'carton_count': 5, 'estimated_volume': None, 'total_weight': None}
    """
    import math

    result = {
        'carton_count': None,
        'estimated_volume': None,
        'total_weight': None
    }

    if not quantity or not units_per_carton:
        return result

    try:
        qty = float(quantity)
        upc = float(units_per_carton)

        if upc <= 0:
            return result

        # 1. 计算箱数 (向上取整)
        carton_count = math.ceil(qty / upc)
        result['carton_count'] = int(carton_count)

        # 2. 体积和重量需要额外的包装数据
        # 这些值由调用者根据包装规格补充
        # (见 _build_item_detail_v11 中的完整实现)

    except (TypeError, ValueError):
        pass

    return result


def _format_packing_spec_display(units_per_carton: float) -> str:
    """
    格式化打包规格显示 (Excel列34)

    格式: "{units_per_carton} pcs/ctn"

    Args:
        units_per_carton: 每箱装入数量

    Returns:
        str: 格式化的打包规格字符串

    示例:
        >>> _format_packing_spec_display(100)
        '100 pcs/ctn'
    """
    if units_per_carton is None:
        return None

    try:
        return f"{int(float(units_per_carton))} pcs/ctn"
    except (TypeError, ValueError):
        return None


def _derive_pack_spec_from_packaging(packaging: str, carton_count) -> Optional[str]:
    """
    2026-06-23 新增：根据包装方式 + 箱数派生打包规格字符串

    派生规则：
        "1件/箱"   → "1 pcs/ctn"
        "1件多箱" → "1pcs/{N} ctn"（N = carton_count，缺失则回退 "1pcs/ctn"）
        "多件/箱" → 需配合 units_per_carton（_format_packing_spec_display 处理），返回 None
        其他/None → None

    用于 _build_item_detail_v11 详情显示兜底：当 item.pack_spec 字段为空、且
    package_obj 也没有 units_per_carton 时，按 packaging + carton_count 实时计算。
    """
    if not packaging:
        return None
    if packaging == "1件/箱":
        return "1 pcs/ctn"
    if packaging == "1件多箱":
        try:
            n = int(carton_count) if carton_count else None
        except (TypeError, ValueError):
            n = None
        if n and n > 0:
            return f"1pcs/{n} ctn"
        return "1pcs/ctn"
    # 多件/箱的 pack_spec 由 _format_packing_spec_display 处理（需要 units_per_carton）
    return None


def get_pi_invoices_with_customer(db: Session, skip: int = 0, limit: int = 100, status: int = None):
    """获取PI列表，包含客户信息"""
    query = db.query(
        PiProformaInvoice,
        CrmCustomer.customer_code,
        CrmCustomer.customer_name
    ).outerjoin(
        CrmCustomer, PiProformaInvoice.customer_id == CrmCustomer.id
    )
    if status is not None:
        query = query.filter(PiProformaInvoice.status == status)
    query = query.order_by(PiProformaInvoice.created_at.desc())
    results = query.offset(skip).limit(limit).all()
    return [
        {
            "id": pi.id,
            "dept_id": pi.dept_id,
            "pi_no": pi.pi_no,
            "customer_id": pi.customer_id,
            "customer_code": cc,
            "customer_name": cn,
            "total_amount": float(pi.total_amount) if pi.total_amount else 0,
            "currency": pi.currency or "USD",
            "status": pi.status or 1,
            "created_at": pi.created_at.isoformat() if pi.created_at else None,
            "updated_at": pi.updated_at.isoformat() if pi.updated_at else None
        }
        for pi, cc, cn in results
    ]


# ============== 2026-06-10 新增：PI 订单项 CRUD ==============
def get_pi_item(db: Session, item_id: int) -> PiProformaInvoiceItem:
    """获取 PI 订单项"""
    return db.query(PiProformaInvoiceItem).filter(
        PiProformaInvoiceItem.id == item_id
    ).first()


def update_pi_item(db: Session, item_id: int, update_data: dict) -> PiProformaInvoiceItem:
    """更新 PI 订单项（字段回填）
    
    2026-06-22 完整版：支持41列字段中的所有可编辑字段
    
    支持字段分组:
      - A组(基础): product_id, oe_number, customer_code, customer_model, detail_desc,
                   unit_price, quantity, remark
      - B组(财务): customer_prepayment, remaining_payment, factory_deposit, factory_balance
      - D组(包装): packaging, pack_spec, carton_count, carton_gross_weight
      - E组(采购): purchase_option_name
      
    同步逻辑:
      - quantity/unit_price 变化时刷新 total_price 与 PI 主单 total_amount
    """
    db_item = get_pi_item(db, item_id)
    if not db_item:
        return None

    # ---- A组: 基础信息字段 ----
    if 'product_id' in update_data:
        db_item.product_id = update_data['product_id']
    if 'oe_number' in update_data:
        db_item.oe_number = update_data['oe_number']
    if 'customer_code' in update_data:
        db_item.customer_code = update_data['customer_code']
    if 'customer_model' in update_data:
        db_item.customer_model = update_data['customer_model']
    if 'detail_desc' in update_data:
        db_item.detail_desc = update_data['detail_desc']
    if 'unit_price' in update_data:
        db_item.unit_price = update_data['unit_price']
    if 'quantity' in update_data:
        db_item.quantity = update_data['quantity']
    if 'remark' in update_data:
        db_item.remark = update_data['remark']

    # 🔧 2026-06-22 新增：41列设计字段(导入时直接存入主表)
    if 'customer_model' in update_data:
        db_item.customer_model = update_data['customer_model']
    if 'product_feature' in update_data:
        db_item.product_feature = update_data['product_feature']
    if 'product_detail' in update_data:
        db_item.product_detail = update_data['product_detail']
    if 'invoice_status' in update_data:
        db_item.invoice_status = update_data['invoice_status']
    if 'carton_count' in update_data and update_data['carton_count'] is not None:
        db_item.carton_count = int(update_data['carton_count']) if update_data['carton_count'] else None
    if 'carton_length_cm' in update_data and update_data['carton_length_cm'] is not None:
        db_item.carton_length_cm = float(update_data['carton_length_cm'])
    if 'carton_width_cm' in update_data and update_data['carton_width_cm'] is not None:
        db_item.carton_width_cm = float(update_data['carton_width_cm'])
    if 'carton_height_cm' in update_data and update_data['carton_height_cm'] is not None:
        db_item.carton_height_cm = float(update_data['carton_height_cm'])

    # 2026-06-23 派生 carton_size 字符串：三个尺寸都有效时拼出 "LxWxH cm" 写入 pi_item.carton_size
    # 41 列表格 Col 33 读 carton_size 字符串；不派生则 Col 33 永远空
    if (
        db_item.carton_length_cm is not None
        and db_item.carton_width_cm is not None
        and db_item.carton_height_cm is not None
        and float(db_item.carton_length_cm) > 0
        and float(db_item.carton_width_cm) > 0
        and float(db_item.carton_height_cm) > 0
    ):
        db_item.carton_size = (
            f"{float(db_item.carton_length_cm):.0f}x"
            f"{float(db_item.carton_width_cm):.0f}x"
            f"{float(db_item.carton_height_cm):.0f}cm"
        )
        print(
            f"[DEBUG] update_pi_item: 派生 carton_size={db_item.carton_size} "
            f"from (L={db_item.carton_length_cm}, W={db_item.carton_width_cm}, H={db_item.carton_height_cm})"
        )

    # ---- B组: 财务相关字段 (Col 13-14, 25-26) ----
    # ✅ 2026-06-22 新增：客户预付款/尾款/工厂订金/工厂尾款
    if 'customer_prepayment' in update_data and update_data['customer_prepayment'] is not None:
        db_item.customer_prepayment = float(update_data['customer_prepayment'])
        print(f"[DEBUG] update_pi_item: 更新 customer_prepayment={update_data['customer_prepayment']}")

    if 'remaining_payment' in update_data and update_data['remaining_payment'] is not None:
        db_item.remaining_payment = float(update_data['remaining_payment'])
        print(f"[DEBUG] update_pi_item: 更新 remaining_payment={update_data['remaining_payment']}")

    if 'factory_deposit' in update_data and update_data['factory_deposit'] is not None:
        db_item.factory_deposit = float(update_data['factory_deposit'])
        print(f"[DEBUG] update_pi_item: 更新 factory_deposit={update_data['factory_deposit']}")

    if 'factory_balance' in update_data and update_data['factory_balance'] is not None:
        db_item.factory_balance = float(update_data['factory_balance'])
        print(f"[DEBUG] update_pi_item: 更新 factory_balance={update_data['factory_balance']}")

    # ---- D组: 包装规格字段 (Col 29, 34-35, 37) ----
    # ✅ 2026-06-22 新增：包装方式/打包规格/箱数/毛重
    if 'packaging' in update_data and update_data['packaging'] is not None:
        db_item.packaging = update_data['packaging']
        print(f"[DEBUG] update_pi_item: 更新 packaging={update_data['packaging']}")

    # 2026-06-23 新增：接收前端订单产品编辑 Dialog 传的 packing_type/units_per_carton/boxes_count
    # 原代码只处理 'packaging'（来自 Excel 导入），但前端保存用 'packing_type' → 用户在 Dialog 选
    # "1件/箱" / "多件/箱" / "1件多箱" 后 packing_type 永远写不进 DB，订单详情表 41 列 包装相关列永远是空
    if 'packing_type' in update_data and update_data['packing_type'] is not None:
        db_item.packing_type = update_data['packing_type']
        # 同步写入 packaging 字段（Excel 模板 Col 29 也读这个）
        db_item.packaging = update_data['packing_type']
        print(f"[DEBUG] update_pi_item: 更新 packing_type={update_data['packing_type']}（同步到 packaging）")
    # 兼容：前端如果直接发 packaging 字段也支持
    elif 'packaging' in update_data and update_data['packaging'] is not None and not getattr(db_item, 'packaging', None):
        # ⚠️ 注意：不要覆盖已经处理的 packaging（避免覆盖"包装方式"语义）
        # 只有当 packing_type 没传、但 packaging 传了的时候才接管
        db_item.packaging = update_data['packaging']
        print(f"[DEBUG] update_pi_item: 通过 packaging 字段更新 packaging={update_data['packaging']}")
    if 'units_per_carton' in update_data and update_data['units_per_carton'] is not None:
        db_item.units_per_carton = update_data['units_per_carton']
        print(f"[DEBUG] update_pi_item: 更新 units_per_carton={update_data['units_per_carton']}")
    if 'boxes_count' in update_data and update_data['boxes_count'] is not None:
        # ⚠️ 2026-06-23 修复：DB 模型没有 boxes_count 字段，但有 carton_count
        # "1件多箱" 模式下的"箱数"应该写进 carton_count（41 列 Col 35 箱数）
        # 原代码写 db_item.boxes_count 会静默失败（SQLAlchemy 不允许未声明字段）
        try:
            db_item.carton_count = int(update_data['boxes_count'])
            print(f"[DEBUG] update_pi_item: boxes_count={update_data['boxes_count']} 写入 carton_count")
        except (TypeError, ValueError):
            pass

    # 2026-06-23 新增：根据 packaging 派生 pack_spec 字符串写入 DB
    # 用户选 1件/箱 时 units_per_carton=空 → 原来 pack_spec 永远 None → 41 列 Col 34 "打包规格" 列空
    # 注意：DB 模型没有 packing_type 字段，统一用 packaging 字段（VARCHAR(100)）存"1件/箱"等
    #   1件/箱   → "1 pcs/ctn"
    #   多件/箱 → f"{units_per_carton} pcs/ctn"
    #   1件多箱 → f"1pcs/{carton_count} ctn"（1 件拆成 N 箱；用 carton_count 字段）
    packaging_val = db_item.packaging
    if packaging_val == '1件/箱':
        db_item.pack_spec = '1 pcs/ctn'
    elif packaging_val == '多件/箱':
        # 1件多箱的 product.units_per_carton 没有，packaging 模式下单位是 units_per_carton
        # 但 DB 模型也没有 units_per_carton，所以从 dialog 的 pack_spec 旧值保留
        # 优先保留前端已写入的 pack_spec（order_summary_edit_dialog.py L794-801 自己会算）
        pass
    elif packaging_val == '1件多箱':
        # 1件多箱：每箱 1 件，箱数 = carton_count（DB 字段是 carton_count 而非 boxes_count）
        # 2026-06-23：用户要求回填为 "1pcs/{N} ctn"
        try:
            n = int(db_item.carton_count) if db_item.carton_count else None
        except (TypeError, ValueError):
            n = None
        if n and n > 0:
            db_item.pack_spec = f"1pcs/{n} ctn"
        else:
            # 箱数没填时退化为 "1pcs/ctn"（单箱版本）
            db_item.pack_spec = "1pcs/ctn"

    if 'pack_spec' in update_data and update_data['pack_spec'] is not None:
        db_item.pack_spec = update_data['pack_spec']
        print(f"[DEBUG] update_pi_item: 更新 pack_spec={update_data['pack_spec']}")

    if 'carton_count' in update_data and update_data['carton_count'] is not None:
        db_item.carton_count = int(update_data['carton_count']) if update_data['carton_count'] else None
        print(f"[DEBUG] update_pi_item: 更新 carton_count={update_data['carton_count']}")

    if 'carton_gross_weight' in update_data and update_data['carton_gross_weight'] is not None:
        db_item.carton_gross_weight = float(update_data['carton_gross_weight'])
        print(f"[DEBUG] update_pi_item: 更新 carton_gross_weight={update_data['carton_gross_weight']}")

    # ---- E组: 采购选项 (Col 30) ----
    # ✅ 2026-06-22 新增：采购选项名称
    if 'purchase_option_name' in update_data and update_data['purchase_option_name'] is not None:
        db_item.purchase_option_name = update_data['purchase_option_name']
        print(f"[DEBUG] update_pi_item: 更新 purchase_option_name={update_data['purchase_option_name']}")

    # ---- F组: 其他可编辑字段（编辑订单产品 Dialog / 表格内联） ----
    if 'shipping_fee' in update_data and update_data['shipping_fee'] is not None:
        db_item.shipping_fee = float(update_data['shipping_fee'])
        print(f"[DEBUG] update_pi_item: 更新 shipping_fee={update_data['shipping_fee']}")
    if 'misc_fee' in update_data and update_data['misc_fee'] is not None:
        db_item.misc_fee = float(update_data['misc_fee'])
        print(f"[DEBUG] update_pi_item: 更新 misc_fee={update_data['misc_fee']}")
    if 'delivery_date' in update_data:
        from datetime import datetime
        val = update_data['delivery_date']
        if val:
            if isinstance(val, str):
                db_item.delivery_date = datetime.strptime(val[:10], "%Y-%m-%d")
            else:
                db_item.delivery_date = val
        else:
            db_item.delivery_date = None
        print(f"[DEBUG] update_pi_item: 更新 delivery_date={db_item.delivery_date}")
    if 'product_name' in update_data:
        db_item.product_name = update_data['product_name']
        print(f"[DEBUG] update_pi_item: 更新 product_name={update_data['product_name']}")
    if 'image_url' in update_data:
        db_item.image_url = update_data['image_url']
        print(f"[DEBUG] update_pi_item: 更新 image_url={update_data['image_url']}")
    if 'default_image_url' in update_data:
        db_item.image_url = update_data['default_image_url']
        print(f"[DEBUG] update_pi_item: 更新 image_url from default_image_url={update_data['default_image_url']}")
    if 'brand' in update_data:
        db_item.brand = update_data['brand']
        print(f"[DEBUG] update_pi_item: 更新 brand={update_data['brand']}")
    if 'supplier_name' in update_data:
        db_item.supplier_name = update_data['supplier_name']
        print(f"[DEBUG] update_pi_item: 更新 supplier_name={update_data['supplier_name']}")
    if 'factory_short_name' in update_data:
        db_item.supplier_name = update_data['factory_short_name']
        print(f"[DEBUG] update_pi_item: 更新 supplier_name from factory_short_name={update_data['factory_short_name']}")
    if 'shop_url' in update_data:
        db_item.shop_url = update_data['shop_url']
        print(f"[DEBUG] update_pi_item: 更新 shop_url={update_data['shop_url']}")
    if 'line_1688_url' in update_data:
        db_item.shop_url = update_data['line_1688_url']
        print(f"[DEBUG] update_pi_item: 更新 shop_url from line_1688_url={update_data['line_1688_url']}")
    if 'factory_code' in update_data:
        db_item.factory_code = update_data['factory_code']
        print(f"[DEBUG] update_pi_item: 更新 factory_code={update_data['factory_code']}")
    if 'purchase_price' in update_data and update_data['purchase_price'] is not None:
        db_item.purchase_price = float(update_data['purchase_price'])
        print(f"[DEBUG] update_pi_item: 更新 purchase_price={update_data['purchase_price']}")

    # ---- 派生字段:total_price ----
    if db_item.quantity is not None and db_item.unit_price is not None:
        db_item.total_price = float(db_item.quantity) * float(db_item.unit_price)

    # ---- 联动刷新:PI 主单 total_amount ----
    if 'quantity' in update_data or 'unit_price' in update_data:
        pi_items = db.query(PiProformaInvoiceItem).filter(
            PiProformaInvoiceItem.pi_id == db_item.pi_id
        ).all()
        new_total = sum(
            float(it.quantity or 0) * float(it.unit_price or 0) for it in pi_items
        )
        if db_item.pi:
            db_item.pi.total_amount = new_total

    db.commit()
    db.refresh(db_item)
    # 🔧 2026-06-22 关键修复：提交后立即 expire 改对象
    # 防止后续查询返回陈旧数据（Session 一级缓存问题）
    try:
        db.expire(db_item)
    except Exception:
        pass
    return db_item


def change_pi_item_supplier(db: Session, item_id: int, supplier_data: dict) -> dict:
    """更换 PI item 的供应商/采购信息，并重新生成采购单。

    约束：
    - 必须已存在采购单（否则不允许调用）。
    - 若原采购单已收货/已入库，拒绝更换。
    - 删除原采购单及采购项，创建新采购单，并同步更新库存记录中的 po_id/supplier_id。
    """
    from models import PoPurchaseOrder, InvInventory
    from crud.purchase import create_grouped_purchase_orders
    from schemas.purchase import PurchaseOrderCreate, PurchaseOrderItemCreate

    db_item = get_pi_item(db, item_id)
    if not db_item:
        raise ValueError("订单项不存在")

    # 1. 查找当前采购单
    old_po_items = db.query(PoPurchaseOrderItem).filter(
        PoPurchaseOrderItem.pi_item_id == item_id
    ).all()
    if not old_po_items:
        raise ValueError("该订单项尚未生成采购单")

    old_po_item = old_po_items[0]
    old_po = db.query(PoPurchaseOrder).filter(
        PoPurchaseOrder.id == old_po_item.po_id
    ).first()
    if not old_po:
        raise ValueError("关联采购单不存在")

    # 2. 检查是否可更换
    if old_po_item.inbound_status not in (None, 1):
        raise ValueError("采购单已入库或已收货，无法更换供应商")

    # 3. 更新 PI item 字段
    field_map = {
        "supplier_name": "supplier_name",
        "factory_short_name": "supplier_name",
        "shop_url": "shop_url",
        "line_1688_url": "shop_url",
        "factory_code": "factory_code",
        "brand": "brand",
        "purchase_price": "purchase_price",
        "factory_price": "purchase_price",
        "factory_deposit": "factory_deposit",
        "factory_balance": "factory_balance",
        "invoice_status": "invoice_status",
    }
    for src, dst in field_map.items():
        if src in supplier_data and supplier_data[src] is not None:
            if src in ("purchase_price", "factory_price", "factory_deposit", "factory_balance"):
                setattr(db_item, dst, float(supplier_data[src]))
            else:
                setattr(db_item, dst, supplier_data[src])

    # 4. 获取或创建供应商
    supplier_name = supplier_data.get("supplier_name") or supplier_data.get("factory_short_name") or db_item.supplier_name
    if not supplier_name:
        raise ValueError("供应商名称不能为空")

    supplier = db.query(SupSupplier).filter(SupSupplier.supplier_name == supplier_name).first()
    if not supplier:
        # 生成唯一 supplier_code
        base_code = supplier_name[:20] if supplier_name else "NEW"
        supplier_code = base_code
        suffix = 1
        while db.query(SupSupplier).filter(SupSupplier.supplier_code == supplier_code).first():
            supplier_code = f"{base_code}_{suffix}"
            suffix += 1
        supplier = SupSupplier(
            dept_id=old_po.dept_id,
            supplier_code=supplier_code,
            supplier_name=supplier_name,
            status=1,
        )
        db.add(supplier)
        db.flush()
        db.refresh(supplier)

    # 5. 记录旧 PO ID，删除旧采购单（级联删除 items）
    old_po_id = old_po.id
    db.delete(old_po)
    db.flush()

    # 6. 创建新采购单
    purchase = PurchaseOrderCreate(
        pi_id=db_item.pi_id,
        dept_id=old_po.dept_id,
        supplier_id=supplier.id,
        currency=old_po.currency or "USD",
        items=[
            PurchaseOrderItemCreate(
                pi_item_id=db_item.id,
                product_id=db_item.product_id,
                quantity=float(db_item.quantity or 0),
                unit_price=float(db_item.purchase_price or 0),
                link=db_item.shop_url,
                factory_code=db_item.factory_code,
            )
        ],
    )
    new_orders = create_grouped_purchase_orders(db, purchase)
    new_po_id = new_orders[0].id if new_orders else None

    # 7. 库存联动：更新库存记录中的 po_id 和 supplier_id
    if new_po_id:
        inv_records = db.query(InvInventory).filter(
            InvInventory.pi_id == db_item.pi_id,
            InvInventory.product_id == db_item.product_id,
            InvInventory.po_id == old_po_id
        ).all()
        for inv in inv_records:
            inv.po_id = new_po_id
            inv.supplier_id = supplier.id
            inv.purchase_price = db_item.purchase_price
        if inv_records:
            db.flush()

    return {"success": True, "new_po_id": new_po_id, "old_po_id": old_po_id}


# 2026-06-12 需求#40：软删除 / 入库 CRUD
def delete_pi_item(db: Session, item_id: int) -> PiProformaInvoiceItem | None:
    """软删除 PI 单品（设置 is_deleted=True）"""
    item = db.query(PiProformaInvoiceItem).filter(
        PiProformaInvoiceItem.id == item_id
    ).first()
    if not item:
        return None
    item.is_deleted = True
    db.commit()
    db.refresh(item)
    return item


def inbound_pi_item(db: Session, item_id: int, quantity: float, inspector: str = None, remark: str = None):
    """
    单品入库：
    1. 通过 pi_item 找到关联的 PO item（pi_item_id + product_id）
    2. 创建 PoInboundBatch 记录（status=2 已验收），供 _sync_pi_item_from_inbound 聚合
    3. 更新 PO item inbound_status=2
    4. 同步回写 PI item 的 storage_status / stocked_qty
    5. 2026-06-23 计划 A：upsert inv_inventory，让库存管理 Tab 也能看到新入库数据

    历史修复：
    - 原代码用 PoPurchaseOrderItem.pi_id 查询，但模型字段是 pi_item_id → 查询失败
    - 原 inbound_inventory 仅翻转 stock_type=1 行，不支持按 po_id+product_id 新增
    - 改用 upsert_inventory_on_inbound，按 (po_id, product_id) upsert total_quantity
    """
    item = db.query(PiProformaInvoiceItem).filter(
        PiProformaInvoiceItem.id == item_id,
        PiProformaInvoiceItem.is_deleted == False
    ).first()
    if not item:
        raise ValueError(f"PI item {item_id} not found or deleted")

    # 找对应 PO item（用 pi_item_id，不是 pi_id —— 字段名错会导致 SQLAlchemy 报错）
    po_item = db.query(PoPurchaseOrderItem).filter(
        PoPurchaseOrderItem.pi_item_id == item.id,
        PoPurchaseOrderItem.product_id == item.product_id
    ).order_by(PoPurchaseOrderItem.id.desc()).first()
    if not po_item:
        raise ValueError(f"PI item {item_id} has no linked purchase order item (pi_item_id={item.id}, product_id={item.product_id})")

    # 创建 PoInboundBatch 记录（status=2 已验收，_sync_pi_item_from_inbound 聚合此表）
    from datetime import datetime
    from models.purchase import PoInboundBatch, PoPurchaseOrder
    batch = PoInboundBatch(
        po_id=po_item.po_id,
        dept_id=po_item.po.dept_id if po_item.po and po_item.po.dept_id else "",
        product_id=item.product_id,
        quantity=quantity,
        inspector=inspector or "",
        remark=remark or f"入库验收 by {inspector or 'N/A'}",
        status=2,  # 直接置为已验收
        inbound_date=datetime.now(),
        batch_no=f"INB-{datetime.now().strftime('%Y%m%d%H%M%S')}-{item_id}",
    )
    db.add(batch)

    # 更新 PO item 状态
    po_item.inbound_status = 2
    db.commit()
    db.refresh(batch)

    # 同步回写 PI item 的 storage_status / stocked_qty
    try:
        _sync_pi_item_from_inbound(db, item)
        db.refresh(item)  # 重新加载同步后的字段
    except Exception as sync_err_inbound:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[pi] _sync_pi_item_from_inbound failed (non-blocking): {sync_err_inbound}")

    # 2026-06-23 计划 A：upsert inv_inventory，让库存管理 Tab 实时看到新入库数据
    # 失败不影响主流程（po_inbound_batch 已写入），仅记日志
    import logging
    logger = logging.getLogger(__name__)
    try:
        from crud.inventory import upsert_inventory_on_inbound
        pi = item.pi
        po = po_item.po
        _dept_id = (po.dept_id if po and po.dept_id else (pi.dept_id if pi and getattr(pi, 'dept_id', None) else ""))
        _customer_id = (pi.customer_id if pi and pi.customer_id else 0)
        _supplier_id = (po.supplier_id if po and po.supplier_id else None)
        logger.info(f"[📦➡inv] inbound_pi_item → upsert_inventory: dept={_dept_id}, po_id={po_item.po_id}, pi_id={item.pi_id}, "
                    f"product_id={item.product_id}, customer_id={_customer_id}, supplier_id={_supplier_id}, "
                    f"qty={quantity}, inspector={inspector}, po_item.unit_price={po_item.unit_price}, customer_code={item.customer_code}")
        inv = upsert_inventory_on_inbound(
            db,
            dept_id=_dept_id,
            po_id=po_item.po_id,
            pi_id=item.pi_id,
            product_id=item.product_id,
            customer_id=_customer_id,
            supplier_id=_supplier_id,
            quantity=quantity,
            inspector=inspector,
            remark=remark,
            purchase_price=float(po_item.unit_price) if po_item.unit_price is not None else None,
            customer_product_code=item.customer_code,
        )
        logger.info(f"[📦✅inv] upsert_inventory_on_inbound DONE: inv_id={inv.id if inv else None}, "
                    f"total_quantity={inv.total_quantity if inv else None}, stock_type={inv.stock_type if inv else None}")
    except Exception as inv_err:
        import traceback
        logger.error(f"[📦❌inv] upsert_inventory_on_inbound FAILED: {inv_err}\n{traceback.format_exc()}")

    return batch


def inbound_pi_items_batch(db: Session, pi_id: int, items: list[dict], inspector: str = None):
    """
    批量入库：items = [{"pi_item_id": int, "quantity": float, "remark": str}, ...]
    返回 {"processed": N, "failed": M, "errors": [...]}
    """
    results = {"processed": 0, "failed": 0, "errors": []}
    for entry in items:
        try:
            inbound_pi_item(db, entry["pi_item_id"], entry["quantity"], inspector, entry.get("remark"))
            results["processed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({"pi_item_id": entry["pi_item_id"], "error": str(e)})
    return results


# ============== 2026-06-12 需求#42：历史记录 + 正式纪录 CRUD ==============
def get_pi_versions(db: Session, pi_id: int) -> list:
    """获取 PI 所有历史版本"""
    return db.query(PiProformaInvoiceVersion).filter(
        PiProformaInvoiceVersion.pi_id == pi_id
    ).order_by(PiProformaInvoiceVersion.version_no.desc()).all()


def save_pi_snapshot(db: Session, pi_id: int, change_desc: str, expected_version_no: int) -> PiProformaInvoiceVersion:
    """
    保存新快照（乐观锁）
    - expected_version_no: 前端传入的当前版本号
    - 比对 MAX(version_no)，不一致则拒绝（HTTP 409）
    """
    latest = db.query(PiProformaInvoiceVersion).filter(
        PiProformaInvoiceVersion.pi_id == pi_id
    ).order_by(PiProformaInvoiceVersion.version_no.desc()).first()
    latest_no = latest.version_no if latest else 0

    if expected_version_no != latest_no:
        raise ValueError(f"版本冲突：当前版本 {latest_no}，你传入 {expected_version_no}")

    pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == pi_id).first()
    if not pi:
        raise ValueError(f"PI {pi_id} 不存在")

    snapshot = {
        "pi": {
            "id": pi.id, "pi_no": pi.pi_no, "customer_id": pi.customer_id,
            "total_amount": float(pi.total_amount) if pi.total_amount else 0,
            "currency": pi.currency, "status": pi.status,
            "created_at": pi.created_at.isoformat() if pi.created_at else None,
        },
        "items": [
            {
                "id": item.id, "product_id": item.product_id,
                "oe_number": item.oe_number, "customer_code": item.customer_code,
                "detail_desc": item.detail_desc,
                "quantity": float(item.quantity) if item.quantity else 0,
                "unit_price": float(item.unit_price) if item.unit_price else 0,
                "total_price": float(item.total_price) if item.total_price else 0,
                "remark": item.remark,
            } for item in pi.items if not getattr(item, 'is_deleted', False)
        ],
        "payment_stages": [
            {
                "id": s.id, "stage_type": s.stage_type, "stage_no": s.stage_no,
                "amount": float(s.amount) if s.amount else 0,
                "due_date": s.due_date.isoformat() if s.due_date else None,
                "paid_date": s.paid_date.isoformat() if s.paid_date else None,
                "status": s.status,
            } for s in pi.payment_stages
        ],
    }

    new_version = PiProformaInvoiceVersion(
        pi_id=pi_id,
        version_no=latest_no + 1,
        snapshot_data=snapshot,
        change_desc=change_desc,
        created_by=None,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version


def _get_formal_records_dir() -> Path:
    """获取正式纪录存储目录"""
    base = Path(__file__).parent.parent.parent / "data"
    records_dir = base / "formal_records"
    records_dir.mkdir(parents=True, exist_ok=True)
    return records_dir


def save_formal_record(db: Session, pi_id: int) -> str:
    """将 PI 当前状态保存为 JSON 文件（正式纪录），返回文件路径"""
    pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == pi_id).first()
    if not pi:
        raise ValueError(f"PI {pi_id} 不存在")

    data = {
        "pi": {
            "id": pi.id, "pi_no": pi.pi_no, "customer_id": pi.customer_id,
            "customer_name": pi.customer.customer_name if pi.customer else "",
            "total_amount": float(pi.total_amount) if pi.total_amount else 0,
            "currency": pi.currency, "status": pi.status,
            "created_at": pi.created_at.isoformat() if pi.created_at else None,
            "updated_at": pi.updated_at.isoformat() if pi.updated_at else None,
        },
        "items": [
            {
                "id": item.id, "product_id": item.product_id,
                "oe_number": item.oe_number, "customer_code": item.customer_code,
                "detail_desc": item.detail_desc,
                "quantity": float(item.quantity) if item.quantity else 0,
                "unit_price": float(item.unit_price) if item.unit_price else 0,
                "total_price": float(item.total_price) if item.total_price else 0,
                "remark": item.remark,
            } for item in pi.items if not getattr(item, 'is_deleted', False)
        ],
        "payment_stages": [
            {
                "id": s.id, "stage_type": s.stage_type, "stage_no": s.stage_no,
                "amount": float(s.amount) if s.amount else 0,
                "due_date": s.due_date.isoformat() if s.due_date else None,
                "paid_date": s.paid_date.isoformat() if s.paid_date else None,
                "status": s.status,
            } for s in pi.payment_stages
        ],
    }

    records_dir = _get_formal_records_dir()
    file_path = records_dir / f"{pi.pi_no}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(file_path)


def load_formal_record(pi_no: str) -> dict | None:
    """读取正式纪录 JSON"""
    records_dir = _get_formal_records_dir()
    file_path = records_dir / f"{pi_no}.json"
    if not file_path.exists():
        return None
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def formal_record_exists(pi_no: str) -> bool:
    """检查正式纪录是否存在"""
    records_dir = _get_formal_records_dir()
    return (records_dir / f"{pi_no}.json").exists()

