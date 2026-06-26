# -*- coding: utf-8 -*-
"""
OrderService - 订单数据服务

文件：client/services/order_service.py
用途：封装订单数据的加载、缓存、更新等操作

创建日期：2026-06-04
来源：main.py L3861-3924 (load_order_summary) 迁移

调用方式：
```python
from services.order_service import OrderService

service = OrderService(api_client)

# 模式1：仅加载PI订单列表（列表视图）
service.load_pi_orders_async(callback)

# 模式2：加载完整数据（含采购/出货/付款/库存）
service.load_full_data_async(callback)
```

依赖：
- api.client.ApiClient
- PySide6.QtCore.QObject, Signal, QTimer
- logging
"""

import logging
from PySide6.QtCore import QObject, Signal, QTimer

logger = logging.getLogger(__name__)


class OrderService(QObject):
    """
    订单数据服务
    
    职责：
    - 异步加载 PI 订单列表
    - 异步加载完整关联数据（采购/出货/付款/库存）
    - 数据缓存管理
    
    信号：
    - data_loaded(orders): PI订单列表加载完成
    - full_data_ready(data): 完整数据加载完成 {pi_list, purchase_list, ...}
    - items_loaded(items): 产品列表加载完成
    - error(msg): 加载错误
    """
    
    # 信号定义
    data_loaded = Signal(list)
    full_data_ready = Signal(object)
    items_loaded = Signal(list)
    error = Signal(str)
    # 2026-06-14：单品删除事件 (order_id, item_id) - 解耦 UI 状态协调
    item_removed = Signal(int, int)
    # 回调信号 - 确保在主线程执行回调
    _data_callback_signal = Signal(object, object)
    
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self._order_cache = {}
        self._orders_cache = []
        self._orders = []            # [兼容性别名] test_phase8_order_service
        self._pi_orders = []         # [兼容性别名] test_phase8_order_service
        self._data = None            # [兼容性别名] test_phase8_order_service
        self.orders = []             # [兼容性别名] test_phase8_order_service
        self._items_cache = {}
        self._full_data_cache = None  # 完整数据缓存
        self._thread_pool = None  # 保持线程池引用，防止被垃圾回收
        
        # 连接回调信号到槽函数
        self._data_callback_signal.connect(self._on_data_callback)
    
    def _on_data_callback(self, data, callback):
        """回调信号的槽函数 - 确保在主线程执行"""
        logger.info(f"[OrderService._on_data_callback] 执行回调, data={type(data)}")
        try:
            if callback:
                callback(data)
                logger.info(f"[OrderService._on_data_callback] 回调执行完成")
        except Exception as e:
            logger.error(f"[OrderService._on_data_callback] 回调异常: {e}", exc_info=True)
    
    def load_full_data_async(self, callback=None):
        """
        异步加载完整订单数据（从 main.py.load_order_summary 迁移）
        
        加载内容：
        - PI 订单列表（强制刷新）
        - 采购订单列表
        - 出货记录
        - 客户付款记录
        - 供应商付款记录
        - 库存汇总 [6.2]
        
        Args:
            callback: 回调函数 callback(data_dict)
        """
        def fetch():
            import time
            import threading
            _t0 = time.time()
            _phase = {}
            logger.info(
                f"[OrderService.load_full_data_async] ===== fetch 开始 ===== "
                f"thread={threading.current_thread().name}"
            )
            try:
                data = {}
                
                # 阶段1: PI 订单
                _t = time.time()
                data['pi_list'] = self.api_client.get_pi_orders() or []
                _phase['pi_list'] = time.time() - _t
                logger.info(
                    f"[OrderService][FETCH-P1] pi_list 数量={len(data['pi_list'])} "
                    f"耗时={_phase['pi_list']:.3f}s"
                )
                # 关键字段回填诊断
                if data['pi_list']:
                    _PI_KEY = [('id', 'n'), ('pi_no', 's'), ('customer_name', 's'),
                               ('order_date', 's'), ('total_amount', 'n'),
                               ('paid_amount', 'n'), ('product_count', 'n'),
                               ('has_inventory', 'b'), ('inventory_quantity', 'n'),
                               ('storage_status', 's')]
                    
                    def _is_missing(val, kind):
                        if val is None:
                            return True
                        if kind == 'b':
                            return not isinstance(val, bool)
                        if kind == 'n':
                            return isinstance(val, str) and val.strip() == ''
                        return False
                    
                    miss = {k: 0 for k, _ in _PI_KEY}
                    for o in data['pi_list']:
                        for k, kind in _PI_KEY:
                            if _is_missing(o.get(k), kind):
                                miss[k] += 1
                    miss_report = {k: v for k, v in miss.items() if v > 0}
                    if miss_report:
                        logger.warning(
                            f"[OrderService][FETCH-P1] /api/pi/ 返回字段缺失: "
                            f"{miss_report} (total={len(data['pi_list'])})"
                        )
                    else:
                        logger.info(
                            f"[OrderService][FETCH-P1] /api/pi/ 关键字段全部回填 "
                            f"(共 {len(_PI_KEY)} 个字段)"
                        )
                
                # 阶段2: 采购订单
                _t = time.time()
                data['purchase_list'] = self.api_client.get_purchase_orders() or []
                _phase['purchase'] = time.time() - _t
                
                # 阶段3: 出货
                _t = time.time()
                data['shipment_list'] = self.api_client.get_shipments() or []
                _phase['shipment'] = time.time() - _t
                
                # 阶段4: 客户付款
                _t = time.time()
                data['customer_payment_list'] = self.api_client.get_customer_payments() or []
                _phase['cust_pay'] = time.time() - _t
                
                # 阶段5: 供应商付款
                _t = time.time()
                data['supplier_payment_list'] = self.api_client.get_supplier_payments() or []
                _phase['sup_pay'] = time.time() - _t
                
                # 阶段6: 库存汇总
                _t = time.time()
                data['inventory_summary'] = {}
                try:
                    data['inventory_summary'] = self.api_client.get_all_inventory_summary() or {}
                    logger.info(
                        f"[OrderService][FETCH-P6] inventory_summary 产品数="
                        f"{len(data['inventory_summary'])}"
                    )
                except Exception as e:
                    logger.warning(f"[OrderService] 获取库存汇总失败: {e}")
                _phase['inventory'] = time.time() - _t
                
                logger.info(
                    f"[OrderService][FETCH-SUMMARY] 阶段耗时: "
                    f"pi={_phase['pi_list']:.3f}s purchase={_phase['purchase']:.3f}s "
                    f"shipment={_phase['shipment']:.3f}s cust_pay={_phase['cust_pay']:.3f}s "
                    f"sup_pay={_phase['sup_pay']:.3f}s inventory={_phase['inventory']:.3f}s "
                    f"total_sequential={sum(_phase.values()):.3f}s"
                )
                
                # 更新缓存
                self._full_data_cache = data
                self._orders_cache = data['pi_list']
                
                # 并行加载每个订单的详细信息（包含 items）
                from concurrent.futures import ThreadPoolExecutor, as_completed
                
                _items_loaded = 0
                _items_failed = 0
                _items_total = 0
                
                def load_order_detail(order):
                    order_id = order.get('id')
                    if not order_id:
                        return order_id, [], 'no_id'
                    try:
                        detail = self.api_client.get_pi_detail(order_id)
                        if detail and 'items' in detail:
                            items = detail.get('items', []) or []
                            for item in items:
                                if not item.get('product_id') or item.get('product_id') == 0:
                                    item['is_temporary'] = True
                                elif 'is_temporary' not in item:
                                    item['is_temporary'] = False
                            return order_id, items, 'ok'
                    except Exception as e:
                        return order_id, [], f'error:{e}'
                    # 降级：使用订单内嵌 items
                    items = order.get('items', []) or []
                    for item in items:
                        if not item.get('product_id') or item.get('product_id') == 0:
                            item['is_temporary'] = True
                        elif 'is_temporary' not in item:
                            item['is_temporary'] = False
                    return order_id, items, 'fallback'
                
                _t_par = time.time()
                logger.info(
                    f"[OrderService][FETCH-PARALLEL] 开始并行加载 "
                    f"{len(data['pi_list'])} 个订单详情..."
                )
                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = {executor.submit(load_order_detail, order): order for order in data['pi_list']}
                    for future in as_completed(futures):
                        order_id, items, status = future.result()
                        _items_total += 1
                        if order_id:
                            self._items_cache[order_id] = items
                            if status == 'ok':
                                _items_loaded += 1
                            elif status.startswith('error'):
                                _items_failed += 1
                            elif status == 'fallback':
                                _items_loaded += 1  # 视为成功
                _phase['parallel_detail'] = time.time() - _t_par
                logger.info(
                    f"[OrderService][FETCH-PARALLEL] 订单详情加载完成: "
                    f"loaded={_items_loaded}/{_items_total} failed={_items_failed} "
                    f"耗时={_phase['parallel_detail']:.3f}s cache={len(self._items_cache)}"
                )
                
                # 主线程回调 - 使用 Signal 中转确保线程安全
                logger.info(f"[OrderService] 准备调用回调, callback={callback is not None}")
                try:
                    if callback:
                        self._data_callback_signal.emit(data, callback)
                        logger.info(f"[OrderService] 回调信号已发射")
                    else:
                        logger.warning("[OrderService] callback 为 None，跳过")
                    
                    self.full_data_ready.emit(data)
                    self.data_loaded.emit(data.get('pi_list', []) if data else [])
                    logger.info(f"[OrderService] 数据信号已发射")
                except Exception as sig_err:
                    logger.error(f"[OrderService] 信号发射异常: {sig_err}", exc_info=True)
                
                _phase['total'] = time.time() - _t0
                logger.info(
                    f"[OrderService][FETCH-TOTAL] ===== fetch 完成 ===== "
                    f"total={_phase['total']:.3f}s"
                )
            except Exception as e:
                logger.error(f"[OrderService] 加载完整数据失败: {e}", exc_info=True)
                QTimer.singleShot(0, lambda: self.error.emit(str(e)))
        
        from concurrent.futures import ThreadPoolExecutor
        self._thread_pool = ThreadPoolExecutor(max_workers=4)
        self._thread_pool.submit(fetch)
    
    def _on_full_data_ready(self, data, callback):
        """完整数据加载完成回调"""
        logger.info(f"[OrderService._on_full_data_ready] ===== 回调开始执行 =====")
        logger.info(f"[OrderService._on_full_data_ready] data 类型: {type(data)}")
        if data:
            logger.info(f"[OrderService._on_full_data_ready] data keys: {list(data.keys())}")
            pi_list = data.get('pi_list', [])
            logger.info(f"[OrderService._on_full_data_ready] pi_list 长度: {len(pi_list)}")
        else:
            logger.warning(f"[OrderService._on_full_data_ready] data is None!")
        
        try:
            self.full_data_ready.emit(data)
            logger.info(f"[OrderService._on_full_data_ready] full_data_ready 信号已发射")
            
            # 同时发射 data_loaded 以兼容旧接口
            pi_list = data.get('pi_list', []) if data else []
            self.data_loaded.emit(pi_list)
            logger.info(f"[OrderService._on_full_data_ready] data_loaded 信号已发射, 数量={len(pi_list)}")
            
            if callback:
                logger.info(f"[OrderService._on_full_data_ready] 准备执行 callback...")
                callback(data)
                logger.info(f"[OrderService._on_full_data_ready] callback 执行完成")
            else:
                logger.warning(f"[OrderService._on_full_data_ready] callback 为 None，跳过执行")
                
        except Exception as cb_err:
            logger.error(f"[OrderService._on_full_data_ready] 回调执行异常: {cb_err}", exc_info=True)
        
        logger.info(f"[OrderService._on_full_data_ready] ===== 回调执行结束 =====")
    
    def load_pi_orders_async(self, callback=None):
        """
        异步加载 PI 订单列表（轻量模式，仅获取订单列表）
        
        Args:
            callback: callback(orders: list)
        """
        def fetch():
            try:
                pi_orders = self.api_client.get_pi_orders() or []
                
                dept_id = getattr(self.api_client, 'dept_id', 'S')
                filtered = [
                    o for o in pi_orders
                    if str(o.get('dept_id', '')) == str(dept_id)
                ]
                
                self._orders_cache = filtered
                for order in filtered:
                    self._order_cache[order.get('id')] = order
                
                QTimer.singleShot(0, lambda: self._on_data_loaded(filtered, callback))
                
            except Exception as e:
                logger.error(f"[OrderService] 加载PI订单失败: {e}")
                QTimer.singleShot(0, lambda: self.error.emit(str(e)))
        
        from concurrent.futures import ThreadPoolExecutor
        if not self._thread_pool or self._thread_pool._shutdown:
            self._thread_pool = ThreadPoolExecutor(max_workers=4)
        self._thread_pool.submit(fetch)
    
    def _on_data_loaded(self, orders, callback):
        """PI订单列表加载完成回调"""
        self.data_loaded.emit(orders)
        if callback:
            callback(orders)
    
    def load_order_items_async(self, order_id: int, callback=None):
        """异步加载订单产品列表"""
        if order_id in self._items_cache:
            if callback:
                callback(self._items_cache[order_id])
            self.items_loaded.emit(self._items_cache[order_id])
            return
        
        def fetch():
            try:
                items = self.api_client.get_pi_items(order_id)
                self._items_cache[order_id] = items
                QTimer.singleShot(0, lambda: self._on_items_loaded(order_id, items, callback))
            except Exception as e:
                logger.error(f"[OrderService] 加载产品列表失败: {e}")
                QTimer.singleShot(0, lambda: self.error.emit(str(e)))
        
        from concurrent.futures import ThreadPoolExecutor
        if not self._thread_pool or self._thread_pool._shutdown:
            self._thread_pool = ThreadPoolExecutor(max_workers=4)
        self._thread_pool.submit(fetch)
    
    def _on_items_loaded(self, order_id, items, callback):
        self.items_loaded.emit(items)
        if callback:
            callback(items)
    
    # ---- 缓存访问 ----
    
    def get_order_by_id(self, order_id: int):
        return self._order_cache.get(order_id)
    
    def get_orders(self):
        return self._orders_cache
    
    def get_items_by_order_id(self, order_id: int):
        return self._items_cache.get(order_id, [])

    def update_items_cache(self, order_id: int, items: list):
        """
        🔧 2026-06-22 新增：更新items缓存
        问题：保存订单后服务端缓存未更新，导致UI显示旧数据
        解决：保存成功后调用此方法，将最新items写入缓存
        """
        self._items_cache[order_id] = items
        logger.info(f"[OrderService] 缓存已更新: order_id={order_id}, items_count={len(items) if items else 0}")

    def invalidate_items_cache(self, order_id: int = None):
        """
        🔧 2026-06-22 新增：使items缓存失效
        用法：
        - 传order_id: 仅清除指定订单的缓存
        - 不传: 清除所有items缓存
        """
        if order_id is not None:
            if order_id in self._items_cache:
                del self._items_cache[order_id]
                logger.info(f"[OrderService] 缓存已失效: order_id={order_id}")
        else:
            self._items_cache.clear()
            logger.info(f"[OrderService] 全部items缓存已失效")
    
    def get_full_data(self):
        """获取完整数据缓存"""
        return self._full_data_cache
    
    def get_inventory_summary(self):
        """获取库存汇总 [6.2]"""
        if self._full_data_cache:
            return self._full_data_cache.get('inventory_summary', {})
        return {}
    
    def refresh_cache(self):
        self._order_cache.clear()
        self._orders_cache.clear()
        self._items_cache.clear()
        self._full_data_cache = None
    
    def update_item(self, item_id: int, data: dict) -> bool:
        try:
            self.api_client.update_pi_item(item_id, data)
            return True
        except Exception as e:
            logger.error(f"[OrderService] 更新产品失败: {e}")
            return False

    def remove_pi_item(self, order_id: int, item_id: int) -> bool:
        """删除 PI 单品：调 API + 清理本地缓存 + 发射信号

        Returns:
            True 表示 API 端删除成功，False 表示失败（缓存保持原样）
        """
        try:
            self.api_client.delete_pi_item(item_id)
        except Exception as e:
            logger.error(f"[OrderService] 删除单品失败: item_id={item_id}, err={e}")
            return False

        # 清理本地缓存
        items = self._items_cache.get(order_id)
        if items is not None:
            self._items_cache[order_id] = [it for it in items if it.get("id") != item_id]

        # 通知订阅者（OrderDetailPanel 监听此信号同步内部状态）
        self.item_removed.emit(order_id, item_id)
        return True
    
    def get_order_items_sync(self, order_id: int) -> list:
        try:
            return self.api_client.get_pi_items(order_id)
        except Exception as e:
            logger.error(f"[OrderService] 同步获取产品失败: {e}")
            return []
    
    # 向后兼容别名
    load_order_summary_async = load_full_data_async
