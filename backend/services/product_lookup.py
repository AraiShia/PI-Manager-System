# -*- coding: utf-8 -*-
"""
统一产品访问服务 - Phase 5 简化版

Phase 5 后已删除 prd_product 表，所有产品统一来自 prd_customer_product。

使用：
    from services.product_lookup import unified_product_lookup
    product = unified_product_lookup(db, item.product_id, customer_id=customer.id)
    if product.is_temporary: ...
"""
import logging
import time
from typing import Optional
from sqlalchemy.orm import Session

from models.customer_product import PrdCustomerProduct

logger = logging.getLogger(__name__)


class UnifiedProduct:
    """统一产品对象（Phase 5 后只代理 PrdCustomerProduct）"""

    def __init__(self, data: PrdCustomerProduct):
        self._data = data
        logger.debug(
            "[UnifiedProduct] 包装产品对象 id=%s, customer_id=%s, model=%s, is_temporary=%s",
            getattr(data, 'id', None),
            getattr(data, 'customer_id', None),
            getattr(data, 'customer_model', None),
            getattr(data, 'is_temporary', None),
        )

    @property
    def id(self) -> int:
        return self._data.id

    @property
    def system_code(self) -> Optional[str]:
        return self._data.system_code

    @property
    def oe_number(self) -> Optional[str]:
        # prd_customer_product 用 customer_model 存客户型号（与原 oe_number 等价）
        return self._data.customer_model

    @property
    def product_name(self) -> Optional[str]:
        return self._data.product_name or self._data.detail_desc

    @property
    def detail_desc(self) -> Optional[str]:
        return self._data.detail_desc or self._data.product_name

    @property
    def brand(self) -> Optional[str]:
        return self._data.brand

    @property
    def category_id(self) -> Optional[str]:
        v = self._data.category_id
        return str(v) if v is not None else None

    @property
    def image_url(self) -> Optional[str]:
        return self._data.image_url

    @property
    def fob_price_incl(self):
        """FOB 含税价（USD）"""
        return self._data.price_usd

    @property
    def fob_price_excl(self):
        """FOB 不含税价（RMB）"""
        return self._data.price_rmb

    @property
    def is_temporary(self) -> bool:
        return bool(self._data.is_temporary)

    @property
    def customer_id(self) -> Optional[int]:
        return self._data.customer_id

    def __getattr__(self, item):
        """未知属性回退到原对象"""
        logger.debug("[UnifiedProduct] 属性回退到原对象: %s", item)
        return getattr(self._data, item, None)


def unified_product_lookup(
    db: Session,
    product_id: Optional[int],
    customer_id: Optional[int] = None,
) -> Optional[UnifiedProduct]:
    """
    统一产品查找（Phase 5 简化版）

    Args:
        db: 数据库会话
        product_id: 产品ID
        customer_id: 客户ID（可选，用于校验 customer_product 是否属于该客户）

    Returns:
        UnifiedProduct 或 None
    """
    logger.info(
        "[unified_product_lookup] 入参 product_id=%s, customer_id=%s",
        product_id, customer_id,
    )
    start = time.perf_counter()

    if product_id is None:
        logger.warning("[unified_product_lookup] product_id 为空，直接返回 None")
        return None

    try:
        cp = db.query(PrdCustomerProduct).filter(PrdCustomerProduct.id == product_id).first()
    except Exception as e:
        logger.exception(
            "[unified_product_lookup] 查询 PrdCustomerProduct 异常 product_id=%s, err=%s",
            product_id, e,
        )
        return None

    if not cp:
        logger.warning(
            "[unified_product_lookup] 未找到产品 product_id=%s（可能已被删除或为脏数据）",
            product_id,
        )
        return None

    # 归属校验（仅当显式传入 customer_id 时执行）
    if customer_id is not None and cp.customer_id != customer_id:
        logger.warning(
            "[unified_product_lookup] 归属校验失败 product_id=%s, 期望 customer_id=%s, 实际=%s",
            product_id, customer_id, cp.customer_id,
        )
        return None

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "[unified_product_lookup] 命中 product_id=%s, customer_id=%s, model=%s, is_temp=%s, 耗时=%.2fms",
        cp.id, cp.customer_id, cp.customer_model, cp.is_temporary, elapsed_ms,
    )
    if elapsed_ms > 200:
        logger.warning(
            "[unified_product_lookup] 慢查询 product_id=%s, 耗时=%.2fms（建议排查索引）",
            product_id, elapsed_ms,
        )

    return UnifiedProduct(data=cp)


def unified_product_lookup_by_system_code(
    db: Session,
    system_code: str,
) -> Optional[UnifiedProduct]:
    """通过 system_code 查找"""
    logger.info("[unified_product_lookup_by_system_code] 入参 system_code=%s", system_code)
    start = time.perf_counter()

    if not system_code:
        logger.warning("[unified_product_lookup_by_system_code] system_code 为空，返回 None")
        return None

    try:
        cp = db.query(PrdCustomerProduct).filter(
            PrdCustomerProduct.system_code == system_code
        ).first()
    except Exception as e:
        logger.exception(
            "[unified_product_lookup_by_system_code] 查询异常 system_code=%s, err=%s",
            system_code, e,
        )
        return None

    elapsed_ms = (time.perf_counter() - start) * 1000
    if not cp:
        logger.warning(
            "[unified_product_lookup_by_system_code] 未命中 system_code=%s, 耗时=%.2fms",
            system_code, elapsed_ms,
        )
        return None

    logger.info(
        "[unified_product_lookup_by_system_code] 命中 system_code=%s, product_id=%s, 耗时=%.2fms",
        system_code, cp.id, elapsed_ms,
    )
    return UnifiedProduct(data=cp)
