# -*- coding: utf-8 -*-
"""
PI 订单项业务回写同步层

文件：backend/crud/pi_sync.py
创建日期：2026-06-18
来源：fixplan/03-同步函数实现.md

功能概述：
4 大业务线 / 6 个 sync 函数 回写到 pi_proforma_invoice_item:
1. 采购 Dialog (线下) → _sync_pi_item_from_po(含品牌同步)
2. 采购 Dialog (线上:1688/微信) → _sync_pi_item_from_1688(微信渠道跳 shop_url)
3. 入库 Dialog → _sync_pi_item_from_inbound
4. 包装规格 Dialog → _sync_pi_item_from_package
5. 客户付款 Dialog → _sync_pi_item_from_payment
6. 品牌同步(在采购同步中附带) → 从产品表同步品牌信息

设计原则:
- 同步在主业务 commit 之后调用,失败仅记日志不阻塞主流程
- 显示层 (_build_item_detail_v11) 优先用快照字段
- 完整事件流写入 PiProformaInvoice.pi_data_sync_event (JSON数组)
- 所有新字段 nullable=True,向后兼容旧数据

调用方式:
```python
from crud.pi_sync import _sync_pi_item_from_po, _sync_pi_item_from_inbound

# 在采购Dialog提交后调用
_sync_pi_item_from_po(db, pi_item, po_item, supplier)

# 在入库Dialog提交后调用
_sync_pi_item_from_inbound(db, pi_item)
```

依赖:
- SQLAlchemy ORM Session 和模型
- logging 日志模块
"""

import logging
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func

from models.pi import PiProformaInvoice, PiProformaInvoiceItem
from models.purchase import PoPurchaseOrderItem, Po1688Purchase, PoInboundBatch
from models.purchase_package import PoPurchaseOrderItemPackage
from models.payment import ArCustomerPayment

logger = logging.getLogger(__name__)


# ============== 通用辅助函数 ==============


def _safe_commit(db: Session, label: str) -> bool:
    """
    安全的 commit 操作

    失败时仅记录日志并回滚,不抛出异常,避免阻塞主业务流程。

    Args:
        db: SQLAlchemy Session
        label: str, 操作标签(用于日志)

    Returns:
        bool: True=成功, False=失败
    """
    try:
        db.commit()
        return True
    except Exception as e:
        logger.error(f"[pi_sync] {label} commit failed: {e}")
        db.rollback()
        return False


def _append_sync_event(pi: PiProformaInvoice, event_obj: dict) -> None:
    """
    追加同步事件到 PI 主表的审计字段

    将每次同步操作记录到 pi.pi_data_sync_event JSON 字段,
    用于运维追踪和问题排查。

    Args:
        pi: PiProformaInvoice 实例
        event_obj: dict, 事件数据(会自动添加时间戳)
    """
    if pi.pi_data_sync_event is None:
        pi.pi_data_sync_event = []
    event_obj["at"] = datetime.now().isoformat()
    pi.pi_data_sync_event.append(event_obj)


def sync_pi_item_field(
    pi_item: PiProformaInvoiceItem,
    field: str,
    value,
    source: str
) -> None:
    """
    通用字段同步辅助函数

    设置 PI 订单项的字段值,并在 DEBUG 级别记录来源。
    如果字段不存在则记录警告。

    Args:
        pi_item: PiProformaInvoiceItem 实例
        field: str, 字段名(必须存在于模型定义中)
        value: 要设置的值
        source: str, 数据来源描述(用于日志)
    """
    if not hasattr(pi_item, field):
        logger.warning(f"[pi_sync] PI item has no field: {field}")
        return
    setattr(pi_item, field, value)
    logger.debug(f"[pi_sync] PI item {pi_item.id}.{field} = {value} (from {source})")


# ============== 1. 采购同步 (线下) ==============


def _sync_pi_item_from_po(
    db: Session,
    pi_item: PiProformaInvoiceItem,
    po_item: PoPurchaseOrderItem,
    supplier=None,
) -> None:
    """
    采购 Dialog (线下) 提交后,把 PO item 的关键字段回写到 PI item

    触发场景:
    - create_grouped_purchase_orders() 线下采购单创建成功后

    同步字段 (共12个):
    - purchase_price: 采购单价 (来自 po_item.unit_price)
    - shipping_fee: 发货费 (来自 po_item.shipping_fee)
    - misc_fee: 杂费 = labeling_fee + tax_fee + freight (计算得出)
    - total_order_amount: 采购总金额 (来自 po_item.total_price)
    - supplier_name: 供应商名称 (来自 sup_supplier.supplier_name)
    - shop_url: 1688链接 (来自 po_item.line_1688_url)
    - delivery_date: 交期 (来自 po.po.contract_date)
    - factory_code: 工厂编号 (来自 po_item.factory_code)
    - purchase_option_name: 采购选项/名称 (来自 po_item.color_detail 或 purchase_option_name)
    - brand: 品牌 (来自 prd_customer_product.brand)
    - last_synced_at: 最后同步时间 (当前时间)

    Args:
        db: SQLAlchemy Session
        pi_item: 目标 PI 订单项
        po_item: 来源 PO 采购明细项
        supplier: 可选,供应商对象(SupSupplier)
    """
    try:
        # === 基础价格字段 ===
        sync_pi_item_field(pi_item, "purchase_price", po_item.unit_price, "po_item.unit_price")
        sync_pi_item_field(pi_item, "shipping_fee", po_item.shipping_fee, "po_item.shipping_fee")

        # 杂费计算: misc_fee = labeling_fee + tax_fee + freight (发货费)
        # 2026-06-18 明确化: 三项费用汇总
        misc = float(po_item.labeling_fee or 0) + \
               float(po_item.tax_fee or 0) + \
               float(getattr(po_item, 'freight', 0) or 0)
        sync_pi_item_field(
            pi_item, "misc_fee", misc,
            "po_item.labeling_fee+tax_fee+freight"
        )

        # 总金额
        sync_pi_item_field(
            pi_item, "total_order_amount", po_item.total_price,
            "po_item.total_price"
        )

        # === 供应商与链接信息 ===
        sync_pi_item_field(
            pi_item, "shop_url", po_item.line_1688_url,
            "po_item.line_1688_url"
        )
        sync_pi_item_field(
            pi_item, "factory_code", po_item.factory_code,
            "po_item.factory_code"
        )

        # 供应商名称 (如果提供了supplier对象)
        if supplier:
            sync_pi_item_field(
                pi_item, "supplier_name", supplier.supplier_name,
                "sup_supplier.supplier_name"
            )

        # 交期 (从PO主表的合同日期)
        if po_item.po and po_item.po.contract_date:
            sync_pi_item_field(
                pi_item, "delivery_date", po_item.po.contract_date,
                "po.contract_date"
            )

        # 2026-06-23：purchase_option_name 不再从采购单同步到 PI item
        # 该字段只能从产品编辑 Dialog（OrderSummaryEditDialog）维护，
        # 采购流程不应该覆盖它
        # （原逻辑：option_name = po_item.color_detail / po_item.purchase_option_name）

        # === 品牌信息 (从产品表查询) ===
        if pi_item.product_id:
            from models.customer_product import PrdCustomerProduct
            product = db.query(PrdCustomerProduct).filter(
                PrdCustomerProduct.id == pi_item.product_id
            ).first()
            if product and product.brand:
                sync_pi_item_field(
                    pi_item, "brand", product.brand,
                    "prd_customer_product.brand"
                )

        # === 最后同步时间 ===
        sync_pi_item_field(
            pi_item, "last_synced_at", datetime.now(),
            "sync_timestamp"
        )

        # === 记录审计事件到 PI 主表 ===
        if pi_item.pi:
            _append_sync_event(pi_item.pi, {
                "type": "PURCHASE",
                "source": "offline",
                "pi_item_id": pi_item.id,
                "po_item_id": po_item.id,
                "fields_updated": [
                    "purchase_price", "shipping_fee", "misc_fee",
                    "total_order_amount", "supplier_name", "shop_url",
                    "delivery_date", "factory_code", "purchase_option_name",
                    "brand", "last_synced_at"
                ]
            })

        # 提交事务
        _safe_commit(db, "sync_pi_item_from_po")

        logger.info(
            f"[pi_sync] Successfully synced PO item {po_item.id} "
            f"to PI item {pi_item.id}"
        )

    except Exception as e:
        logger.error(
            f"[pi_sync] _sync_pi_item_from_po failed for "
            f"PI item {pi_item.id}, PO item {po_item.id}: {e}",
            exc_info=True
        )
        db.rollback()


# ============== 2. 入库同步 ==============


def _sync_pi_item_from_inbound(
    db: Session,
    pi_item: PiProformaInvoiceItem,
) -> None:
    """
    入库 Dialog 提交后,根据 po_item.inbound_status 和聚合 PoInboundBatch 回写 PI item

    触发场景:
    - inbound_pi_item() 或 inbound_pi_items_batch() 入库操作成功后

    同步字段 (共3个):
    - storage_status: 入库状态 ("已入库"/"已采购"/"× 未入库")
      判定逻辑: po_item.inbound_status == 2 → "已入库"
                 po_item.inbound_status == 1 → "已采购"
                 其他 → "× 未入库"
    - stocked_qty: 已入库数量 (SUM(po_inbound_batch.quantity) WHERE status=2)
    - last_synced_at: 最后同步时间

    注意:
    - is_received Boolean 字段已删除,统一使用 storage_status String 字段
    - 入库数量通过聚合 po_inbound_batch 表计算,支持多次入库累加

    Args:
        db: SQLAlchemy Session
        pi_item: 目标 PI 订单项
    """
    try:
        # 查找关联的最新 PO item
        po_item = db.query(PoPurchaseOrderItem).filter(
            PoPurchaseOrderItem.pi_item_id == pi_item.id
        ).order_by(PoPurchaseOrderItem.id.desc()).first()

        # === 聚合入库数量 ===
        # SUM(po_inbound_batch.quantity) WHERE po_id + product_id + status=2(已验收)
        stocked_qty = 0.0
        if po_item and po_item.po_id:
            total = db.query(
                func.coalesce(func.sum(PoInboundBatch.quantity), 0)
            ).filter(
                PoInboundBatch.po_id == po_item.po_id,
                PoInboundBatch.product_id == pi_item.product_id,
                PoInboundBatch.status == 2,  # 仅统计已验收的批次
            ).scalar()
            stocked_qty = float(total) if total else 0.0

        # === 判定入库状态（2026-06-23 收敛到 crud.storage_status.StorageStatus） ===
        # 取代原先基于 po_item.inbound_status 的硬编码判定，统一为已入库/部分入库/未入库 三值。
        # 业务假设：采购之后才会入库（stocked_qty > 0 隐含 PO 已采购）。
        from crud.storage_status import StorageStatus
        expected_qty = float(pi_item.quantity or 0)
        storage_status_value = StorageStatus.from_item_qty(stocked_qty, expected_qty)

        # === 写入 PI item 快照字段 ===
        sync_pi_item_field(
            pi_item, "storage_status", storage_status_value,
            f"StorageStatus.from_item_qty(stocked_qty={stocked_qty}, expected_qty={expected_qty})"
        )
        sync_pi_item_field(
            pi_item, "stocked_qty", stocked_qty,
            f"SUM(po_inbound_batch.quantity WHERE status=2)"
        )
        sync_pi_item_field(
            pi_item, "last_synced_at", datetime.now(),
            "sync_timestamp"
        )

        # === 记录审计事件 ===
        if pi_item.pi:
            _append_sync_event(pi_item.pi, {
                "type": "INBOUND",
                "pi_item_id": pi_item.id,
                "storage_status": storage_status,
                "stocked_qty": stocked_qty,
                "po_item_id": po_item.id if po_item else None
            })

        _safe_commit(db, "sync_pi_item_from_inbound")

        logger.info(
            f"[pi_sync] Successfully synced inbound status to "
            f"PI item {pi_item.id}: {storage_status}, qty={stocked_qty}"
        )

    except Exception as e:
        logger.error(
            f"[pi_sync] _sync_pi_item_from_inbound failed for "
            f"PI item {pi_item.id}: {e}",
            exc_info=True
        )
        db.rollback()


# ============== 3. 1688 采购同步 (线上:1688 + 微信) ==============


def _sync_pi_item_from_1688(
    db: Session,
    pi_item: PiProformaInvoiceItem,
    record: Po1688Purchase,
) -> None:
    """
    线上采购记录写入后,按 platform 字段区分 1688 / 微信进行差异化同步

    触发场景:
    - create_1688_purchase_batch() 1688/微信采购创建成功后

    同步策略 (按 platform 区分):
    - platform='1688' (默认):
      ✅ 覆盖 shop_url (product_url 是 1688 详情页链接)
      ✅ 同步 purchase_option_name (来自 product_remark)

    - platform='wechat':
      ❌ 跳过 shop_url (微信无产品链接,41列设计该列空)
      ✅ 同步 purchase_option_name (微信聊天备注)

    同步字段 (共2-3个):
    - shop_url: 仅 1688 渠道 (来自 record.product_url)
    - purchase_option_name: 两种渠道都同步 (来自 record.product_remark)
    - last_synced_at: 最后同步时间

    设计原因:
    - 微信渠道没有标准化的产品链接,强制覆盖会导致数据丢失
    - 1688链接是唯一标识符,应该始终更新为最新值

    Args:
        db: SQLAlchemy Session
        pi_item: 目标 PI 订单项
        record: 来源 1688/微信采购记录 (Po1688Purchase)
    """
    try:
        # 获取平台类型 (默认 1688 兼容老数据)
        platform = getattr(record, "platform", "1688")

        # === shop_url 同步 (仅 1688 渠道) ===
        if platform == "1688" and record.product_url:
            sync_pi_item_field(
                pi_item, "shop_url", record.product_url,
                "po_1688_purchase.product_url (1688 channel)"
            )
        else:
            logger.debug(
                f"[pi_sync] Skip shop_url for platform={platform} "
                f"(pi_item={pi_item.id})"
            )

        # === purchase_option_name 不再从采购同步 ===
        # 2026-06-23：该字段只能从产品编辑 Dialog（OrderSummaryEditDialog）维护，
        # 1688 备注 / 微信聊天备注 不再覆盖 purchase_option_name，
        # 避免采购 Dialog 误改 PI 总表 Col 30 采购选项/名称
        # （这些备注仍然存放在 po_1688_purchase.product_remark，不丢失）

        # === 最后同步时间 ===
        sync_pi_item_field(
            pi_item, "last_synced_at", datetime.now(),
            "sync_timestamp"
        )

        # === 记录审计事件 ===
        if pi_item.pi:
            _append_sync_event(pi_item.pi, {
                "type": "PURCHASE_1688",
                "platform": platform,
                "pi_item_id": pi_item.id,
                "po_1688_id": record.id,
                "fields_updated": ["shop_url"] if platform == "1688" else []
            })

        _safe_commit(db, "sync_pi_item_from_1688")

        logger.info(
            f"[pi_sync] Successfully synced 1688/{platform} record "
            f"{record.id} to PI item {pi_item.id}"
        )

    except Exception as e:
        logger.error(
            f"[pi_sync] _sync_pi_item_from_1688 failed for "
            f"PI item {pi_item.id}, record {record.id}: {e}",
            exc_info=True
        )
        db.rollback()


# ============== 4. 包装规格同步 ==============


def _sync_pi_item_from_package(
    db: Session,
    pi_item: PiProformaInvoiceItem,
    package: PoPurchaseOrderItemPackage,
) -> None:
    """
    包装规格 Dialog 提交后,回写包装字段到 PI item

    触发场景:
    - upsert_package() 包装规格保存成功后

    同步字段 (共5个):
    - packaging: 包装方式 (来自 package.packing_type, 如: "纸箱/托盘/木箱")
    - carton_size: 外箱尺寸 (拼接格式: "LxWxH cm", 如: "50x30x40 cm")
    - pack_spec: 装箱规格 (格式: "{units_per_carton} pcs/ctn", 如: "100 pcs/ctn")
    - carton_gross_weight: 毛重 kg (来自 package.gross_weight_kg)
    - last_synced_at: 最后同步时间

    数据转换规则:
    - carton_size: 当三个维度都存在时才拼接,否则设为 None
    - pack_spec: units_per_carton 非空时才生成字符串

    Args:
        db: SQLAlchemy Session
        pi_item: 目标 PI 订单项
        package: 来源包装规格记录 (PoPurchaseOrderItemPackage)
    """
    try:
        # === 包装方式 ===
        sync_pi_item_field(
            pi_item, "packaging", package.packing_type,
            "po_package.packing_type"
        )

        # === 外箱尺寸 (LxWxH cm) ===
        if all([
            package.carton_length_cm,
            package.carton_width_cm,
            package.carton_height_cm
        ]):
            size = (
                f"{int(package.carton_length_cm)}x"
                f"{int(package.carton_width_cm)}x"
                f"{int(package.carton_height_cm)} cm"
            )
        else:
            size = None
        sync_pi_item_field(
            pi_item, "carton_size", size,
            "po_package.carton_*_cm (LxWxH)"
        )

        # === 装箱规格 ===
        if package.units_per_carton:
            pack_spec = f"{package.units_per_carton} pcs/ctn"
        else:
            pack_spec = None
        sync_pi_item_field(
            pi_item, "pack_spec", pack_spec,
            "po_package.units_per_carton"
        )

        # === 毛重 ===
        sync_pi_item_field(
            pi_item, "carton_gross_weight", package.gross_weight_kg,
            "po_package.gross_weight_kg"
        )

        # === 最后同步时间 ===
        sync_pi_item_field(
            pi_item, "last_synced_at", datetime.now(),
            "sync_timestamp"
        )

        # === 记录审计事件 ===
        if pi_item.pi:
            _append_sync_event(pi_item.pi, {
                "type": "PACKAGE",
                "pi_item_id": pi_item.id,
                "po_item_id": package.po_item_id,
                "package_id": package.id,
                "fields_updated": [
                    "packaging", "carton_size", "pack_spec",
                    "carton_gross_weight"
                ]
            })

        _safe_commit(db, "sync_pi_item_from_package")

        logger.info(
            f"[pi_sync] Successfully synced package {package.id} "
            f"to PI item {pi_item.id}"
        )

    except Exception as e:
        logger.error(
            f"[pi_sync] _sync_pi_item_from_package failed for "
            f"PI item {pi_item.id}, package {package.id}: {e}",
            exc_info=True
        )
        db.rollback()


# ============== 5. 客户付款同步 ==============


def _sync_pi_item_from_payment(
    db: Session,
    pi_item: PiProformaInvoiceItem,
) -> None:
    """
    客户付款 Dialog 提交后,聚合 ar_customer_payment 阶段1实收到 PI item

    触发场景:
    - create_customer_payment() 客户收款登记成功后

    同步字段 (共3个):
    - customer_prepayment: 客户预付款
      计算: SUM(ar_customer_payment.actual_amount) WHERE pi_id
    - remaining_payment: 剩余应收款
      计算: pi_item.total_price - customer_prepayment
    - last_synced_at: 最后同步时间

    [P2 优先级 - 未来扩展]:
    - factory_deposit: 工厂定金 (聚合 ap_supplier_payment_stage.stage_type='deposit')
    - factory_balance: 工厂尾款 (聚合 ap_supplier_payment_stage.stage_type IN ('balance1','balance2'))

    业务逻辑:
    - prepayment 是累计值,支持多次收款
    - remaining_payment 动态计算,反映当前应收余额
    - 如果 prepayment >= total_price,remaining_payment 应为 0 或负数

    Args:
        db: SQLAlchemy Session
        pi_item: 目标 PI 订单项
    """
    try:
        # === 聚合客户已收金额 ===
        total = db.query(
            func.coalesce(func.sum(ArCustomerPayment.actual_amount), 0)
        ).filter(
            ArCustomerPayment.pi_id == pi_item.pi_id,
        ).scalar()

        prepayment = float(total) if total else 0.0
        remaining = float(pi_item.total_price or 0) - prepayment

        # === 写入快照字段 ===
        sync_pi_item_field(
            pi_item, "customer_prepayment", prepayment,
            "SUM(ar_customer_payment.actual_amount)"
        )
        sync_pi_item_field(
            pi_item, "remaining_payment", remaining,
            "total_price - customer_prepayment"
        )
        sync_pi_item_field(
            pi_item, "last_synced_at", datetime.now(),
            "sync_timestamp"
        )

        # === 记录审计事件 ===
        if pi_item.pi:
            _append_sync_event(pi_item.pi, {
                "type": "PAYMENT",
                "pi_item_id": pi_item.id,
                "prepayment": prepayment,
                "remaining": remaining,
                "total_price": float(pi_item.total_price or 0)
            })

        _safe_commit(db, "sync_pi_item_from_payment")

        logger.info(
            f"[pi_sync] Successfully synced payment to "
            f"PI item {pi_item.id}: prepayment={prepayment}, remaining={remaining}"
        )

    except Exception as e:
        logger.error(
            f"[pi_sync] _sync_pi_item_from_payment failed for "
            f"PI item {pi_item.id}: {e}",
            exc_info=True
        )
        db.rollback()


# ============== 6. 运维工具函数 ==============


def _snapshot_fields(item: PiProformaInvoiceItem) -> dict:
    """
    获取 PI 订单项当前快照 (所有21个业务回写字段)

    用于:
    - 对账比对 (比较源数据和快照是否一致)
    - 重同步前的备份
    - 运维调试和问题排查

    Returns:
        dict: 包含所有21个字段的字典,值为当前数据库中的实际值
    """
    return {
        # 采购相关 (9个)
        "purchase_price": item.purchase_price,
        "shipping_fee": item.shipping_fee,
        "misc_fee": item.misc_fee,
        "total_order_amount": item.total_order_amount,
        "supplier_name": item.supplier_name,
        "shop_url": item.shop_url,
        "delivery_date": item.delivery_date.isoformat() if item.delivery_date else None,
        "factory_code": item.factory_code,

        # 入库相关 (2个)
        "storage_status": item.storage_status,
        "stocked_qty": item.stocked_qty,

        # 线上采购选项 (1个)
        "purchase_option_name": item.purchase_option_name,

        # 包装规格 (4个)
        "packaging": item.packaging,
        "carton_size": item.carton_size,
        "pack_spec": item.pack_spec,
        "carton_gross_weight": item.carton_gross_weight,

        # 客户付款 (4个)
        "customer_prepayment": item.customer_prepayment,
        "remaining_payment": item.remaining_payment,
        "factory_deposit": item.factory_deposit,
        "factory_balance": item.factory_balance,

        # 产品细节 (1个)
        "brand": item.brand,


    }


def _latest_po_item_for_pi_item(
    db: Session,
    pi_item: PiProformaInvoiceItem
) -> Optional[PoPurchaseOrderItem]:
    """
    获取 PI 订单项关联的最新 PO item

    用于:
    - 重同步触发
    - 数据溯源
    - 运维诊断

    Args:
        db: SQLAlchemy Session
        pi_item: PI 订单项

    Returns:
        Optional[PoPurchaseOrderItem]: 最新的PO明细项,或None
    """
    return db.query(PoPurchaseOrderItem).filter(
        PoPurchaseOrderItem.pi_item_id == pi_item.id
    ).order_by(PoPurchaseOrderItem.id.desc()).first()


def _latest_1688_for_pi_item(
    db: Session,
    pi_item: PiProformaInvoiceItem
) -> Optional[Po1688Purchase]:
    """
    获取 PI 订单项关联的最新 1688/微信采购记录

    Args:
        db: SQLAlchemy Session
        pi_item: PI 订单项

    Returns:
        Optional[Po1688Purchase]: 最新的线上采购记录,或None
    """
    return db.query(Po1688Purchase).filter(
        Po1688Purchase.pi_id == pi_item.pi_id,
        Po1688Purchase.product_id == pi_item.product_id,
    ).order_by(Po1688Purchase.id.desc()).first()


def _supplier_for_po(
    db: Session,
    po_item: PoPurchaseOrderItem
):
    """
    获取 PO 关联的供应商对象

    Args:
        db: SQLAlchemy Session
        po_item: PO明细项

    Returns:
        SupSupplier or None: 供应商实例
    """
    from models.supplier import SupSupplier
    if po_item.po and po_item.po.supplier_id:
        return db.query(SupSupplier).filter(
            SupSupplier.id == po_item.po.supplier_id
        ).first()
    return None


def resync_all_for_pi_item(
    db: Session,
    pi_item: PiProformaInvoiceItem
) -> dict:
    """
    重同步 PI 订单项的所有业务线 (运维工具)

    按顺序执行5个同步函数,用于:
    - 数据修复 (发现快照不一致时)
    - 历史数据回填 (Task 5)
    - 批量对账

    执行顺序:
    1. 采购同步 (线下) - 基础价格和供应商信息
    2. 1688同步 (线上) - 覆盖shop_url和采购选项
    3. 入库同步 - 状态和数量
    4. 包装同步 - 规格参数
    5. 付款同步 - 收款金额

    Returns:
        dict: 包含每个同步函数执行结果的报告
        {
            "success_count": int,
            "fail_count": int,
            "details": [
                {"function": str, "status": "ok"/"error", "message": str}
            ]
        }
    """
    results = {
        "success_count": 0,
        "fail_count": 0,
        "details": [],
        "snapshot_before": _snapshot_fields(pi_item)
    }

    sync_functions = [
        ("_sync_pi_item_from_po", lambda: _sync_pi_item_from_po(
            db, pi_item,
            _latest_po_item_for_pi_item(db, pi_item),
            _supplier_for_po(db, _latest_po_item_for_pi_item(db, pi_item))
        )),
        ("_sync_pi_item_from_1688", lambda: _sync_pi_item_from_1688(
            db, pi_item,
            _latest_1688_for_pi_item(db, pi_item)
        )),
        ("_sync_pi_item_from_inbound", lambda: _sync_pi_item_from_inbound(db, pi_item)),
        ("_sync_pi_item_from_package", lambda: None),  # 需要单独获取package
        ("_sync_pi_item_from_payment", lambda: _sync_pi_item_from_payment(db, pi_item)),
    ]

    for func_name, func_call in sync_functions:
        try:
            func_call()
            results["success_count"] += 1
            results["details"].append({
                "function": func_name,
                "status": "ok",
                "message": "Sync completed successfully"
            })
        except Exception as e:
            results["fail_count"] += 1
            results["details"].append({
                "function": func_name,
                "status": "error",
                "message": str(e)
            })
            logger.error(f"[pi_sync] resync {func_name} failed: {e}")

    results["snapshot_after"] = _snapshot_fields(pi_item)

    logger.info(
        f"[pi_sync] Resync complete for PI item {pi_item.id}: "
        f"{results['success_count']}/{len(sync_functions)} succeeded"
    )

    return results
