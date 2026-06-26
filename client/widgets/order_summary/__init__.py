# -*- coding: utf-8 -*-
"""
order_summary 包

订单总表(QWidget Tab)相关的所有面板与常量:
- OrderSummaryTab     : 总表容器(对接 ApiClient,协调子面板)
- OrderListPanel      : 左侧订单列表(15 列:选择/订单号/客户/.../添加付款/...)
- OrderDetailPanel    : 右侧订单详情(41 列)
- constants           : 15 列表头/列宽/颜色/状态文本

重导出 OrderSummaryTab,允许:
    from widgets.order_summary import OrderSummaryTab
"""

from .order_summary_tab import OrderSummaryTab
from .order_list_panel import OrderListPanel
from .order_detail_panel import OrderDetailPanel
from . import constants

__all__ = [
    "OrderSummaryTab",
    "OrderListPanel",
    "OrderDetailPanel",
    "constants",
]
