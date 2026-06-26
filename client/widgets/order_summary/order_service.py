# -*- coding: utf-8 -*-
"""
订单数据服务

文件：client/widgets/order_summary/order_service.py
用途：封装订单数据的加载、缓存、更新等操作

创建日期：2026-06-04
来源：main.py 订单数据加载相关方法

调用方式：
```python
from widgets.order_summary import OrderService

service = OrderService(api_client)
service.load_order_summary_async(callback)
```

依赖：
- api.client.ApiClient
- concurrent.futures (全局线程池)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import QObject, Signal, QTimer

# 全局线程池（从 main.py 引用）
_global_thread_pool = None


def get_thread_pool():
    """获取全局线程池（延迟导入避免循环依赖）"""
    global _global_thread_pool
    if _global_thread_pool is None:
        import concurrent.futures
        _global_thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="order_service")
    return _global_thread_pool


class OrderService(QObject):
    """
    订单数据服务
    
    职责：
    - 异步加载订单汇总数据
    - 异步加载订单产品列表
    - 数据缓存管理
    
    信号：
    - data_loaded: 数据加载完成，返回订单列表
    - items_loaded: 产品列表加载完成，返回产品列表
    - error: 加载错误，返回错误信息
    """
    
    data_loaded = Signal(list)    # 订单汇总数据加载完成
    items_loaded = Signal(list)   # 订单产品列表加载完成
    error = Signal(str)          # 错误信息
    
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self._order_cache = {}    # 订单缓存 {order_id: order}
        self._orders_cache = []    # 订单列表缓存
        self._items_cache = {}    # 产品列表缓存 {order_id: [items]}
    
    def load_order_summary_async(self, callback=None):
        """
        异步加载订单汇总数据
        
        Args:
            callback: 加载完成后的回调函数，签名为 callback(orders: list)
        """
        def fetch():
            try:
                # 获取所有 PI 订单
                pi_orders = self.api_client.get_pi_orders()
                
                # 过滤当前部门的订单
                dept_id = getattr(self.api_client, 'dept_id', 'S')
                filtered_orders = [
                    o for o in pi_orders 
                    if str(o.get('dept_id', '')) == str(dept_id)
                ]
                
                # 更新缓存
                self._orders_cache = filtered_orders
                for order in filtered_orders:
                    self._order_cache[order.get('id')] = order
                
                # 在主线程回调
                QTimer.singleShot(0, lambda: self._on_data_loaded(filtered_orders, callback))
                
            except Exception as e:
                print(f"[ERROR] OrderService.load_order_summary_async: {e}")
                QTimer.singleShot(0, lambda: self.error.emit(str(e)))
        
        # 使用线程池异步加载
        get_thread_pool().submit(fetch)
    
    def _on_data_loaded(self, orders, callback):
        """数据加载完成回调"""
        self.data_loaded.emit(orders)
        if callback:
            callback(orders)
    
    def load_order_items_async(self, order_id: int, callback=None):
        """
        异步加载订单产品列表
        
        Args:
            order_id: 订单ID
            callback: 加载完成后的回调函数
        """
        # 检查缓存
        if order_id in self._items_cache:
            if callback:
                callback(self._items_cache[order_id])
            self.items_loaded.emit(self._items_cache[order_id])
            return
        
        def fetch():
            try:
                # 获取订单产品详情
                items = self.api_client.get_pi_items(order_id)
                
                # 更新缓存
                self._items_cache[order_id] = items
                
                # 在主线程回调
                QTimer.singleShot(0, lambda: self._on_items_loaded(order_id, items, callback))
                
            except Exception as e:
                print(f"[ERROR] OrderService.load_order_items_async: {e}")
                QTimer.singleShot(0, lambda: self.error.emit(str(e)))
        
        get_thread_pool().submit(fetch)
    
    def _on_items_loaded(self, order_id, items, callback):
        """产品列表加载完成回调"""
        self.items_loaded.emit(items)
        if callback:
            callback(items)
    
    def get_order_by_id(self, order_id: int) -> dict:
        """根据ID获取订单"""
        return self._order_cache.get(order_id)
    
    def get_orders(self) -> list:
        """获取所有订单"""
        return self._orders_cache
    
    def get_items_by_order_id(self, order_id: int) -> list:
        """根据订单ID获取产品列表"""
        return self._items_cache.get(order_id, [])
    
    def update_item(self, item_id: int, data: dict) -> bool:
        """
        更新订单产品
        
        Args:
            item_id: 产品ID
            data: 更新数据
            
        Returns:
            bool: 是否更新成功
        """
        try:
            self.api_client.update_pi_item(item_id, data)
            return True
        except Exception as e:
            print(f"[ERROR] OrderService.update_item: {e}")
            return False
    
    def refresh_cache(self):
        """清空缓存，下次加载会重新获取"""
        self._order_cache.clear()
        self._orders_cache.clear()
        self._items_cache.clear()
    
    def get_order_items_sync(self, order_id: int) -> list:
        """
        同步获取订单产品列表（会阻塞）
        
        Args:
            order_id: 订单ID
            
        Returns:
            list: 产品列表
        """
        try:
            return self.api_client.get_pi_items(order_id)
        except Exception as e:
            print(f"[ERROR] OrderService.get_order_items_sync: {e}")
            return []