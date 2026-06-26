"""storage_status 全局工具模块

单一来源：所有 storage_status 字段的取值与判定都从此处走。
支持向后兼容读取 DB 旧值（normalize）。
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func


class StorageStatus:
    """storage_status 枚举 + 判定逻辑"""

    STORED     = "已入库"
    PARTIAL    = "部分入库"
    NOT_STORED = "未入库"
    ALL = (STORED, PARTIAL, NOT_STORED)

    # DB 历史值 → 新值映射（读路径兼容）
    _LEGACY_MAP = {
        "已采购":     PARTIAL,
        "× 未入库":   NOT_STORED,
        "有库":       STORED,
        "partial":    PARTIAL,
        "已部分入库": PARTIAL,
    }

    @classmethod
    def normalize(cls, raw: Optional[str]) -> Optional[str]:
        """读 DB 时规范化旧值。已经是新值则原样返回。"""
        if raw is None:
            return None
        return cls._LEGACY_MAP.get(raw, raw)

    @classmethod
    def from_item_qty(
        cls, stocked_qty: Optional[float], expected_qty: float
    ) -> str:
        """单品级：基于 stocked_qty 与 expected_qty 比较判定"""
        if not stocked_qty or stocked_qty <= 0:
            return cls.NOT_STORED
        if stocked_qty >= expected_qty:
            return cls.STORED
        return cls.PARTIAL

    @classmethod
    def from_order_inventory(
        cls, db: Session, *, pi_id: int, expected_total: float
    ) -> str:
        """订单级：基于 inv_inventory.total_quantity 聚合判定"""
        from models import InvInventory
        total = db.query(
            func.coalesce(func.sum(InvInventory.total_quantity), 0)
        ).filter(InvInventory.pi_id == pi_id).scalar() or 0.0
        return cls.from_item_qty(float(total), expected_total)
