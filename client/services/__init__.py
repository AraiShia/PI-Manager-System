# -*- coding: utf-8 -*-
"""
services 包

客户端业务服务层:
- order_service : 订单数据加载/缓存/异步刷新

重导出 OrderService,允许:
    from services import OrderService
"""

from .order_service import OrderService

__all__ = ["OrderService"]
