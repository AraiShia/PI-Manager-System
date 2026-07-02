# -*- coding: utf-8 -*-
"""
订单总表主 Tab 容器 - 两页式切换布局

文件：client/widgets/order_summary/order_summary_tab.py
用途：订单总表 Tab 容器，整合列表和详情面板，支持视图切换

创建日期：2026-06-04
来源：main.py L3339-3400（重构）

主要功能：
- 模式1：订单列表视图（默认）
- 模式2：订单详情视图（双击列表行触发）
- 视图切换：列表 ↔ 详情
- 工具栏（新增/刷新/导出按钮）
- 状态管理

调用方式：
```python
from widgets.order_summary import OrderSummaryTab

tab = OrderSummaryTab(api_client, main_window)
widget = tab.create()

# 保持原有信号连接
tab.order_list_clicked.connect(main_window._on_order_list_click)
tab.order_list_double_clicked.connect(main_window._on_order_list_double_click)
tab.order_detail_double_clicked.connect(main_window._on_order_detail_double_click)
```

依赖：
- PySide6.QtWidgets
- PySide6.QtCore
- PySide6.QtGui
- .order_list_panel
- .order_detail_panel
- services.order_service
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFrame, QDialog
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QFont

import logging
logger = logging.getLogger(__name__)

from .order_list_panel import OrderListPanel
from .order_detail_panel import OrderDetailPanel
from services import OrderService


def get_font(size=12, weight=QFont.Weight.Normal):
    """获取字体"""
    return QFont("Microsoft YaHei", size, weight)


class OrderSummaryTab(QWidget):
    """
    订单总表主 Tab 容器 - 两页式切换布局
    
    功能：
    - 模式1（列表）：显示订单列表
    - 模式2（详情）：显示订单详情（41列）
    - 视图切换
    - 工具栏
    
    信号（转发原有信号）：
    - order_list_clicked: 列表单元格点击
    - order_list_double_clicked: 列表单元格双击
    - order_detail_double_clicked: 详情单元格双击
    - piActionRequested: PI操作按钮点击 (order, mode)
    """
    
    # 转发信号（保持与 main.py 相同的签名）
    order_list_clicked = Signal(int, int)
    order_list_double_clicked = Signal(int, int)
    order_detail_double_clicked = Signal(int, int)
    piActionRequested = Signal(object, str)  # (order_dict, mode)
    # 详情面板操作信号
    purchaseRequested = Signal()       # 采购按钮（已废弃：顶部『采购全部』点击后由 tab 内部处理；保留信号以免破坏遗留连接）
    purchaseCompleted = Signal(dict)   # 2026-06-11 任务 5：采购完成回调（main.py 用于刷新）
    supplementRequested = Signal()     # 补充商品按钮
    shipmentRequested = Signal()       # 出货按钮
    replyExportRequested = Signal(list) # 导出回复记录按钮，传 items 列表
    backToOrderListRequested = Signal() # 返回订单总表
    paymentAddRequested = Signal(object)  # 添加付款按钮点击 (order_dict) [需求#41]
    itemUpdated = Signal()  # 2026-06-23：入库/删除明细后通知外部刷新
    
    def __init__(self, api_client, main_window=None):
        super().__init__(main_window)
        self.api_client = api_client
        self.main_window = main_window
        
        # 子组件
        self._list_panel = OrderListPanel(api_client)
        self._detail_panel = OrderDetailPanel(api_client)
        self._service = OrderService(api_client)
        # 2026-06-14：让详情面板订阅服务的事件（item_removed 等）
        self._detail_panel.attach_service(self._service)

        # 视图状态
        self._view_mode = "list"  # "list" | "detail"
        self._current_order = None
        
        # 初始化UI
        self._init_ui()
        
        # 建立内部信号连接
        self._setup_signal_connections()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 工具栏
        toolbar = self._create_toolbar()
        layout.addLayout(toolbar)
        
        # 详情面板（默认隐藏）
        self._detail_group = QGroupBox("📋 订单详情（点击下方列表查看）")
        detail_layout = QVBoxLayout()
        detail_layout.setContentsMargins(10, 10, 10, 10)
        detail_layout.addWidget(self._detail_panel)
        self._detail_group.setLayout(detail_layout)
        layout.addWidget(self._detail_group, stretch=2)
        
        # 列表面板（默认显示）
        self._list_group = QGroupBox("📋 订单列表")
        self._list_group.setMinimumHeight(400)  # 确保 list_group 有足够空间
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(10, 10, 10, 10)
        list_layout.addWidget(self._list_panel)
        self._list_group.setLayout(list_layout)
        layout.addWidget(self._list_group, stretch=1)
        
        # 应用初始视图（默认显示列表）
        self._update_view()
    
    def _create_toolbar(self) -> QHBoxLayout:
        """创建工具栏"""
        toolbar = QHBoxLayout()
        
        # 标题
        title = QLabel("📊 订单管理总表")
        title.setFont(get_font(14, QFont.Weight.Bold))
        toolbar.addWidget(title)
        toolbar.addStretch()
        
        # 新增按钮
        import_btn = QPushButton("📥 新增")
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #4f46e5; }
        """)
        import_btn.clicked.connect(self._on_import_clicked)
        toolbar.addWidget(import_btn)
        
        # 刷新按钮
        self._refresh_btn = QPushButton("🔄 刷新")
        self._refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        self._refresh_btn.clicked.connect(self.load_data)
        toolbar.addWidget(self._refresh_btn)

        # 导出按钮
        self._export_btn = QPushButton("📤 导出")
        self._export_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        self._export_btn.clicked.connect(self._on_export_clicked)
        toolbar.addWidget(self._export_btn)
        
        # 出货按钮（模式一）
        self._shipment_btn = QPushButton("🚚 出货")
        self._shipment_btn.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #d97706; }
        """)
        self._shipment_btn.clicked.connect(self._on_shipment_clicked)
        toolbar.addWidget(self._shipment_btn)

        # 导出回复记录按钮（模式一）
        self._reply_export_btn = QPushButton("📋 导出回复记录")
        self._reply_export_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        self._reply_export_btn.clicked.connect(self._on_reply_export_clicked)
        toolbar.addWidget(self._reply_export_btn)

        # 2026-06-12 需求#40：全部入库按钮（模式二）
        self._batch_inbound_btn = QPushButton("📥 全部入库")
        self._batch_inbound_btn.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #047857; }
        """)
        self._batch_inbound_btn.clicked.connect(self._on_batch_inbound_clicked)
        # 2026-06-23：默认禁用，等 order_detail_panel 异步检查完正式PI后再启用
        self._batch_inbound_btn.setEnabled(False)
        self._batch_inbound_btn.setToolTip("请先点击『保存正式记录』锁定PI后再入库")
        toolbar.addWidget(self._batch_inbound_btn)

        return toolbar
    
    def _setup_signal_connections(self):
        """建立内部信号到转发信号的连接"""
        # 列表面板信号转发
        self._list_panel.cellClicked.connect(
            lambda r, c: self.order_list_clicked.emit(r, c)
        )
        self._list_panel.cellDoubleClicked.connect(
            lambda r, c: self.order_list_double_clicked.emit(r, c)
        )
        # PI操作按钮信号转发
        self._list_panel.piActionRequested.connect(
            lambda o, m: self.piActionRequested.emit(o, m)
        )
        # 添加付款按钮信号转发 [需求#41]
        self._list_panel.paymentAddRequested.connect(
            lambda o: self.paymentAddRequested.emit(o)
        )
        
        # 详情面板信号转发
        self._detail_panel.cellDoubleClicked.connect(
            lambda r, c: self.order_detail_double_clicked.emit(r, c)
        )
        # 操作按钮信号转发
        # 2026-06-11 任务 5：顶部『采购全部』点击由 tab 内部处理（main.py 薄包装）
        self._detail_panel.purchaseRequested.connect(self._on_purchase_all_clicked)
        # 2026-06-11 任务 8：右键菜单信号由 tab 内部处理
        self._detail_panel.purchaseSingleRequested.connect(self._on_purchase_single_clicked)
        self._detail_panel.purchaseRepurchaseRequested.connect(self._on_purchase_repurchase_clicked)
        self._detail_panel.supplementRequested.connect(self.supplementRequested.emit)
        # 2026-06-12 需求#40：入库 / 删除信号
        self._detail_panel.deleteItemRequested.connect(self._on_delete_item_requested)
        self._detail_panel.stockInSingleRequested.connect(self._on_stock_in_single_requested)
        self._detail_panel.backRequested.connect(self._on_back_to_list)
        # 2026-06-23：正式PI检查完成 → 启用/禁用『全部入库』按钮
        self._detail_panel.formalRecordChecked.connect(self._on_formal_record_checked)
        # 2026-06-23：保存正式纪录成功后刷新订单详情
        self._detail_panel.formalRecordSaved.connect(self._on_formal_record_saved)

    def _on_formal_record_saved(self):
        """保存正式纪录成功后刷新当前订单详情"""
        if self._current_order:
            self.show_order_detail(self._current_order)

    @Slot(int, int)
    def _on_list_clicked(self, row, column):
        """列表点击事件（内部处理）- 选中行"""
        order = self._list_panel.get_order_at_row(row)
        if order:
            self._list_panel.select_row(row)
    
    @Slot(int, int)
    def _on_list_double_clicked(self, row, column):
        """列表双击事件（内部处理）- 切换到详情视图"""
        if column == 0:  # 复选框列不处理
            return
        
        order = self._list_panel.get_order_at_row(row)
        if order:
            self.show_order_detail(order)
    
    def show_order_detail(self, order: dict):
        """
        显示订单详情（切换到详情视图）

        Args:
            order: 订单数据
        """
        self._current_order = order
        order_id = order.get('id')

        # 🔧 2026-06-22 修复：优先使用传入order中的items（已包含最新保存的数据）
        # 原问题：保存后立即调用show_order_detail，但_tab从_service缓存中取items
        # 缓存是旧的，导致显示已保存字段为空
        items_from_order = order.get('items', [])

        if items_from_order:
            # ✅ 传入order对象中已有items（刚保存后已更新），直接使用
            self._detail_panel.show_order_detail(order, items_from_order)

            order_no = order.get('pi_no', order.get('order_no', ''))
            customer_name = order.get('customer_name', '')
            total_amount = order.get('total_amount', 0) or 0
            currency = order.get('currency', 'USD')
            item_count = len(items_from_order) or 1
            title = f"📋 订单: {order_no} | 客户: {customer_name} | 共 {item_count} 个产品 | 总金额: {total_amount} {currency}"
            self._detail_group.setTitle(title)

            # 切换到详情视图
            self._view_mode = "detail"
            self._update_view()
            return

        # 获取 items（优先使用服务缓存） - 兼容未传items的情况
        items = self._service.get_items_by_order_id(order_id) if order_id else []

        # 如果缓存中没有 items，说明并行加载还在进行中，需要等待
        if not items and order_id:
            # 显示加载中状态
            self._detail_panel.show_order_detail(order, [])
            self._detail_group.setTitle(f"📋 订单: {order.get('pi_no', '')} | 加载中...")
            self._update_view()
            
            # 设置刷新回调，加载完成后自动刷新详情
            def on_items_loaded(loaded_items):
                # 重新获取订单详情（确保包含最新的 items，包括临时+正式产品）
                try:
                    detail = self.api_client.get_pi_detail(order_id)
                    final_items = detail.get('items', []) if detail else []

                    self._detail_panel.show_order_detail(order, final_items)
                    item_count = len(final_items)
                    customer_name = order.get('customer_name', '')
                    total_amount = order.get('total_amount', 0) or 0
                    currency = order.get('currency', 'USD')
                    pi_no = order.get('pi_no', order.get('order_no', ''))
                    title = f"📋 订单: {pi_no} | 客户: {customer_name} | 共 {item_count} 个产品 | 总金额: {total_amount} {currency}"
                    self._detail_group.setTitle(title)
                except Exception as e:
                    logger.error(f"[OrderSummaryTab] 刷新订单详情失败: {e}")
            
            # 异步加载该订单的 items
            self._service.load_order_items_async(order_id, on_items_loaded)
            return
        
        # 如果有 items，直接显示
        self._detail_panel.show_order_detail(order, items)
        
        # 更新 GroupBox Title
        order_no = order.get('pi_no', order.get('order_no', ''))
        customer_name = order.get('customer_name', '')
        total_amount = order.get('total_amount', 0) or 0
        currency = order.get('currency', 'USD')
        item_count = len(items) or 1
        title = f"📋 订单: {order_no} | 客户: {customer_name} | 共 {item_count} 个产品 | 总金额: {total_amount} {currency}"
        self._detail_group.setTitle(title)
        
        # 切换到详情视图
        self._view_mode = "detail"
        self._update_view()
    
    def show_order_list(self):
        """显示订单列表（切换到列表视图）"""
        self._current_order = None
        self._detail_group.setTitle("📋 订单详情（点击下方列表查看）")
        
        # 切换到列表视图
        self._view_mode = "list"
        self._update_view()
    
    @Slot()
    def _on_back_to_list(self):
        """返回按钮点击 - 切换到列表视图并通知外部"""
        self.show_order_list()
        self.backToOrderListRequested.emit()

    def _on_formal_record_checked(self, has_formal: bool):
        """2026-06-23：order_detail_panel 异步检查完正式PI后，同步更新『全部入库』按钮"""
        if hasattr(self, '_batch_inbound_btn'):
            self._batch_inbound_btn.setEnabled(bool(has_formal))
            if has_formal:
                self._batch_inbound_btn.setToolTip("")
            else:
                self._batch_inbound_btn.setToolTip("请先点击『保存正式记录』锁定PI后再入库")
    
    def _update_view(self):
        """更新视图显示 - 双模式切换"""
        # 模式一（列表）：显示刷新/导出；模式二（详情）：隐藏
        is_list = self._view_mode == "list"
        self._refresh_btn.setVisible(is_list)
        self._export_btn.setVisible(is_list)
        self._shipment_btn.setVisible(is_list)
        self._reply_export_btn.setVisible(is_list)
        self._batch_inbound_btn.setVisible(is_list)

        if self._view_mode == "detail":
            self._detail_group.show()
            self._list_group.hide()
        else:
            # 默认/列表模式：仅显示列表
            self._detail_group.hide()
            self._list_group.show()
    
    def set_view_mode(self, mode: str):
        """
        设置视图模式
        
        Args:
            mode: "list" | "detail"
        """
        if mode in ("list", "detail"):
            self._view_mode = mode
            self._update_view()
    
    @Slot()
    def _on_import_clicked(self):
        """新增按钮点击"""
        # 转发给 main_window
        if self.main_window and hasattr(self.main_window, '_import_order_summary'):
            self.main_window._import_order_summary()
    
    @Slot()
    def _on_export_clicked(self):
        """导出按钮点击"""
        # 转发给 main_window
        if self.main_window and hasattr(self.main_window, 'export_order_summary'):
            self.main_window.export_order_summary()
    
    @Slot()
    def _on_shipment_clicked(self):
        """出货按钮点击（模式一）- 弹出出货单创建对话框"""
        from PySide6.QtWidgets import QMessageBox
        from widgets.shipment_create_dialog import ShipmentCreateDialog
        
        # 获取当前勾选的PI IDs
        pi_ids = self._list_panel.get_selected_pis()
        if not pi_ids:
            QMessageBox.warning(self, "提示", "请先勾选要出货的PI")
            return
        
        # 弹出出货单创建对话框
        dialog = ShipmentCreateDialog(self.api_client, pi_ids, self)
        dialog.shipment_created.connect(self._on_shipment_created)
        dialog.exec()
    
    def _on_shipment_created(self, result: dict):
        """出货单创建成功回调"""
        from PySide6.QtWidgets import QMessageBox
        
        shipment_no = result.get('shipment_no', '')
        QMessageBox.information(self, "成功", f"出货单已创建: {shipment_no}")
        
        # 刷新数据
        self.load_data()
        
        # 通知主窗口跳转到出货Tab
        self.shipmentRequested.emit()

    @Slot()
    def _on_reply_export_clicked(self):
        """导出回复记录按钮点击（模式一）"""
        from PySide6.QtWidgets import QMessageBox

        selected_indices = self.get_selected_item_indices() or []

        if not selected_indices:
            QMessageBox.warning(self, "提示", "请先勾选要导出回复记录的商品")
            return

        items = []
        current_items = self.get_current_items() or []

        for idx in selected_indices:
            if 0 <= idx < len(current_items):
                item = current_items[idx]
                items.append({
                    "pi_id": item.get('pi_id'),
                    "pi_item_id": item.get('id'),
                    "product_name": item.get('product_name') or item.get('name_cn') or '',
                    "pi_no": item.get('pi_no') or '',
                })

        if items:
            self.replyExportRequested.emit(items)

    def create(self) -> QWidget:
        """
        创建 Tab 组件
        
        Returns:
            QWidget: Tab 组件
        """
        # 加载数据
        self.load_data()
        
        # 连接列表点击事件（内部处理）
        self.order_list_clicked.connect(self._on_list_clicked)
        self.order_list_double_clicked.connect(self._on_list_double_clicked)
        
        return self
    
    def load_data(self):
        """加载订单数据（完整模式，含库存等关联数据）"""
        import time
        _t0 = time.time()
        logger.info(f"[OrderSummaryTab.load_data] ===== 开始加载数据 ===== thread={__import__('threading').current_thread().name}")
        
        # 清除 HTTP 缓存，确保获取最新数据
        from cache_manager import invalidate_cache
        invalidate_cache("pi_orders")
        
        def on_full_data_ready(data):
            import time
            _t_callback_start = time.time()
            logger.info(f"[OrderSummaryTab.load_data] on_full_data_ready 被调用, data={type(data)}")
            try:
                if data is None:
                    logger.warning("[OrderSummaryTab.load_data] on_full_data_ready: data is None")
                    return
                
                # ===== 阶段1: 解析 data 顶层结构 =====
                data_keys = list(data.keys()) if isinstance(data, dict) else []
                logger.info(f"[OrderSummaryTab.load_data][STAGE1] data 顶层 keys={data_keys}")
                
                pi_list = data.get('pi_list', [])
                logger.info(f"[OrderSummaryTab.load_data][STAGE1] pi_list={len(pi_list)} (空列表={pi_list == []})")
                
                # 顶层资源计数
                purchase_count = len(data.get('purchase_list', []) or [])
                shipment_count = len(data.get('shipment_list', []) or [])
                cust_pay_count = len(data.get('customer_payment_list', []) or [])
                sup_pay_count = len(data.get('supplier_payment_list', []) or [])
                inventory_summary = data.get('inventory_summary', {}) or {}
                logger.info(
                    f"[OrderSummaryTab.load_data][STAGE1] purchase={purchase_count} "
                    f"shipment={shipment_count} cust_pay={cust_pay_count} sup_pay={sup_pay_count} "
                    f"inventory_summary_keys={len(inventory_summary)}"
                )
                
                if not pi_list:
                    logger.warning("[OrderSummaryTab.load_data][STAGE1] pi_list 为空，无需处理 - 检查后端 /api/pi/ 接口")
                    return
                
                # ===== 阶段2: 字段回填诊断 =====
                # 关键字段清单 - 任何一个缺失都会导致前端表格为空
                # 字段按"类型"分类：b=布尔, n=数字（0 有效）, s=字符串（空串有效）, l=列表（[] 有效）
                _DIAG_FIELDS = [
                    ('id', 'n'), ('pi_no', 's'), ('customer_name', 's'),
                    ('order_date', 's'), ('created_at', 's'),
                    ('total_amount', 'n'), ('currency', 's'), ('status', 's'),
                    ('product_count', 'n'), ('item_count', 'n'),
                    ('paid_amount', 'n'), ('storage_status', 's'),
                    ('has_inventory', 'b'), ('inventory_quantity', 'n'),
                    ('has_temporary_items', 'b'), ('temporary_item_count', 'n'),
                    ('items', 'l'),
                ]
                
                def _is_missing(val, kind: str) -> bool:
                    """判断值是否真正缺失（避免把 False/0/'' 误判为缺失）"""
                    if val is None:
                        return True
                    if kind == 'b':
                        return not isinstance(val, bool)  # bool 类型任意值都算有效
                    if kind == 'n':
                        return isinstance(val, str) and val.strip() == ''
                    if kind == 's':
                        return False  # 任意字符串都算有效（含空串）
                    if kind == 'l':
                        return not isinstance(val, (list, tuple))
                    return False
                
                def _diag_order(o: dict) -> dict:
                    """诊断单个订单的字段回填情况"""
                    return {f: not _is_missing(o.get(f), k) for f, k in _DIAG_FIELDS}
                
                # 大数据量下，仅采样前 3 + 后 1 + 失败订单
                sample_orders = []
                missing_summary = {f: 0 for f, _ in _DIAG_FIELDS}
                total_orders = len(pi_list)
                
                for idx, order in enumerate(pi_list):
                    diag = _diag_order(order)
                    miss = [f for f, ok in diag.items() if not ok]
                    for f in miss:
                        missing_summary[f] += 1
                    # 采样
                    if idx < 3 or idx == total_orders - 1 or miss:
                        sample_orders.append({
                            'idx': idx,
                            'id': order.get('id'),
                            'pi_no': order.get('pi_no'),
                            'missing': miss,
                        })
                
                # 汇总
                miss_pct = {f: f"{missing_summary[f]}/{total_orders} ({100*missing_summary[f]/max(total_orders,1):.1f}%)"
                            for f, _ in _DIAG_FIELDS if missing_summary[f] > 0}
                if miss_pct:
                    logger.warning(
                        f"[OrderSummaryTab.load_data][STAGE2] 字段回填缺失统计:\n"
                        + "\n".join(f"  {f}: {v}" for f, v in miss_pct.items())
                    )
                else:
                    logger.info(
                        f"[OrderSummaryTab.load_data][STAGE2] 所有 17 个关键字段全部回填，"
                        f"无缺失 (orders={total_orders})"
                    )
                
                # 采样订单详情
                for s in sample_orders:
                    logger.info(
                        f"[OrderSummaryTab.load_data][STAGE2-SAMPLE] idx={s['idx']} "
                        f"id={s['id']} pi_no={s['pi_no']} missing={s['missing']}"
                    )
                
                # ===== 阶段3: 库存回填（按 product_id 累加） =====
                _t_inv = time.time()
                inventory = data.get('inventory_summary', {})
                enriched = 0
                for order in pi_list:
                    order_id = order.get('id')
                    total_qty = 0
                    has_inv = False
                    items = order.get('items') or []
                    if order_id and self._service and not items:
                        items = self._service.get_items_by_order_id(order_id) or []
                    for it in items:
                        pid = it.get('product_id')
                        if pid is not None and pid in inventory:
                            total_qty += float(inventory[pid] or 0)
                            has_inv = True
                    order['has_inventory'] = has_inv
                    order['inventory_quantity'] = total_qty

                    # 用服务缓存的 items 补充订单对象
                    if order_id and items and not order.get('items'):
                        order['items'] = items
                    enriched += 1
                logger.info(
                    f"[OrderSummaryTab.load_data][STAGE3] 库存回填完成, "
                    f"enriched={enriched}/{total_orders} 耗时={time.time()-_t_inv:.3f}s "
                    f"inventory_summary覆盖产品数={len(inventory)}"
                )
                
                # 验证 enrich 后字段
                post_inv_missing = {f: 0 for f in ['has_inventory', 'inventory_quantity', 'items']}
                for order in pi_list:
                    for f in post_inv_missing:
                        if not order.get(f) and order.get(f) != 0:
                            post_inv_missing[f] += 1
                if any(v > 0 for v in post_inv_missing.values()):
                    logger.warning(
                        f"[OrderSummaryTab.load_data][STAGE3] enrich 后仍缺失: "
                        + ", ".join(f"{f}={c}" for f, c in post_inv_missing.items() if c > 0)
                    )
                
                # ===== 阶段4: 更新列表 UI =====
                _t_ui = time.time()
                logger.info(f"[OrderSummaryTab.load_data][STAGE4] 准备调用 _list_panel.update_table, orders={len(pi_list)}")
                self._list_panel.update_table(pi_list)
                # 加载客户筛选列表
                self._list_panel.load_customers()
                logger.info(f"[OrderSummaryTab.load_data][STAGE4] _list_panel.update_table 完成, 耗时={time.time()-_t_ui:.3f}s")
                
                # ===== 阶段5: 视图模式 =====
                if self._view_mode == "list":
                    self._list_group.show()
                    self._detail_group.hide()
                else:
                    self._list_group.hide()
                    self._detail_group.show()
                
                if self._view_mode == "detail" and self._current_order:
                    self.show_order_detail(self._current_order)
                
                _t_total = time.time() - _t0
                _t_callback = time.time() - _t_callback_start
                logger.info(
                    f"[OrderSummaryTab.load_data] ===== 数据加载完成 ===== "
                    f"total={_t_total:.3f}s callback={_t_callback:.3f}s orders={total_orders}"
                )
            except Exception as e:
                logger.error(f"[OrderSummaryTab.load_data] on_full_data_ready 异常: {e}", exc_info=True)
        
        self._service.load_full_data_async(on_full_data_ready)
    
    def get_list_panel(self) -> OrderListPanel:
        """获取列表面板"""
        return self._list_panel
    
    def get_detail_panel(self) -> OrderDetailPanel:
        """获取详情面板"""
        return self._detail_panel
    
    def get_service(self) -> OrderService:
        """获取数据服务"""
        return self._service
    
    def get_current_order(self) -> dict:
        """获取当前订单"""
        return self._current_order

    def get_current_items(self) -> list:
        """获取当前订单的产品列表"""
        if self._detail_panel is not None:
            return self._detail_panel.get_current_items() or []
        return []

    def get_selected_item_indices(self) -> list:
        """获取选中的产品行索引列表（订单详情中用户勾选的项）"""
        if self._detail_panel is not None:
            try:
                return list(self._detail_panel.get_selected_items() or [])
            except Exception:
                return []
        return []
    
    def get_view_mode(self) -> str:
        """获取当前视图模式"""
        return self._view_mode
    
    def refresh_data(self):
        """刷新数据"""
        # 清除 HTTP 缓存，确保获取最新数据
        from cache_manager import invalidate_cache
        invalidate_cache("pi_orders")

        # 2026-06-12 修复：记录当前订单/选中行，刷新数据后恢复
        current_order_id = self._current_order.get('id') if self._current_order else None
        current_row = self._detail_panel._current_row if hasattr(self._detail_panel, '_current_row') else -1
        selected_items = self._detail_panel.get_selected_items() if hasattr(self._detail_panel, 'get_selected_items') else set()

        self._service.refresh_cache()
        self.load_data()

        # 2026-06-12 修复：刷新后恢复详情视图（确保状态灯、表格数据同步更新）
        if current_order_id and self._view_mode == "detail":
            # 等待异步加载完成后重新显示详情
            def _refresh_detail_when_ready():
                # 尝试多次获取 items（处理异步加载延迟）
                import time
                for _ in range(5):  # 最多尝试 5 次
                    items = self._service.get_items_by_order_id(current_order_id) or []
                    if items:
                        break
                    time.sleep(0.1)

                items = self._service.get_items_by_order_id(current_order_id) or []
                if items:
                    # 找到当前订单
                    orders = self._service.get_orders() or []
                    current_order = None
                    for o in orders:
                        if o.get('id') == current_order_id or o.get('pi_id') == current_order_id:
                            current_order = o
                            break

                    if current_order:
                        self.show_order_detail(current_order)
                        # 恢复选中行
                        if current_row >= 0 and hasattr(self._detail_panel, '_on_detail_table_clicked'):
                            self._detail_panel._current_row = current_row
                        # 恢复勾选项（强制更新状态灯）
                        if selected_items and hasattr(self._detail_panel, '_update_status_indicator'):
                            self._detail_panel._update_status_indicator(items)

            QTimer.singleShot(300, _refresh_detail_when_ready)
    
    # 向后兼容属性
    @property
    def order_list_table(self):
        """兼容属性：列表表格"""
        return self._list_panel.get_table()

    @property
    def order_detail_table(self):
        """兼容属性：详情表格"""
        return self._detail_panel.get_table()

    # ============== 2026-06-11 任务 5：采购功能重构 ==============

    def _prefill_1688_urls(self, items: list) -> dict:
        """
        拉取每个产品的最近 1688 URL 列表
        返回: {product_id: [url, ...]}；跳过没有 product_id 的项
        """
        result: dict = {}
        for item in items or []:
            pid = item.get("product_id")
            if not pid:
                continue
            try:
                urls = self.api_client.get_recent_1688_urls(pid, limit=5) or []
            except Exception as e:
                print(f"[OrderSummaryTab] get_recent_1688_urls 失败 product_id={pid}: {e}")
                urls = []
            result[pid] = urls
        return result

    def _open_purchase_dialog(self, items: list, prefill_map: dict, *, is_repurchase: bool = False):
        """打开采购对话框，连接 purchase_completed 信号"""
        from widgets.purchase_dialog import PurchaseDialog

        order = self._current_order or {}
        dialog = PurchaseDialog(
            self.api_client,
            items=items,
            parent=self,
            dept_id=None,  # 由 main_window 在更上层补齐（任务 9 兜底）
            pi_id=order.get("id"),
            prefill_urls=prefill_map,
        )
        dialog.purchase_completed.connect(self.purchaseCompleted.emit)
        dialog.exec()
        return dialog

    def _on_purchase_all_clicked(self):
        """顶部『采购全部』按钮：默认勾选所有产品打开采购对话框"""
        items = self._detail_panel.get_current_items() or []
        if not items:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "提示", "当前订单无产品可采购")
            return
        prefill_map = self._prefill_1688_urls(items)
        self._open_purchase_dialog(items, prefill_map)

    def _on_purchase_single_clicked(self, row: int):
        """右键『采购该产品』：只打开对应行的产品采购对话框"""
        items = self._detail_panel.get_current_items() or []
        if row < 0 or row >= len(items):
            return
        single = [items[row]]
        prefill_map = self._prefill_1688_urls(single)
        self._open_purchase_dialog(single, prefill_map)

    def _on_purchase_repurchase_clicked(self, row: int):
        """右键『重新采购』：弹二次确认，确认后打开对话框"""
        items = self._detail_panel.get_current_items() or []
        if row < 0 or row >= len(items):
            return
        from PySide6.QtWidgets import QMessageBox
        product_name = items[row].get("product_name") or items[row].get("detail_desc") or f"产品 #{row+1}"
        ans = QMessageBox.question(
            self,
            "确认重新采购",
            f"产品『{product_name}』已采购过（供应商：{items[row].get('supplier_name', '-')}）。\n确定要再采购一次？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        single = [items[row]]
        prefill_map = self._prefill_1688_urls(single)
        self._open_purchase_dialog(single, prefill_map)

    # 2026-06-12 需求#40：入库 / 删除处理

    def _on_delete_item_requested(self, row: int):
        """软删除商品 - 走 service.remove_pi_item，自动同步 cache + panel 状态"""
        from PySide6.QtWidgets import QMessageBox
        items = self._detail_panel.get_current_items() or []
        if row < 0 or row >= len(items):
            return
        item = items[row]
        item_id = item.get("id")
        if not item_id:
            return
        product_name = item.get("product_name") or f"产品 #{row + 1}"
        order_id = (self._current_order or {}).get("id")
        if not order_id:
            return
        reply = QMessageBox.question(
            self, "确认删除", f"确定删除商品「{product_name}」？（可恢复）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        # 2026-06-14 重构：走 service 层
        # service 会：调 API + 清理 _items_cache + 发射 item_removed 信号
        # panel 订阅该信号 → 内部状态自动同步
        if not self._service.remove_pi_item(order_id, item_id):
            QMessageBox.warning(self, "错误", "删除失败：服务端未确认")
            return
        try:
            self.itemUpdated.emit()
        except (AttributeError, RuntimeError):
            # 兼容老代码：itemUpdated 信号未定义
            pass

    def _on_stock_in_single_requested(self, row: int):
        """单品入库"""
        import logging
        logger = logging.getLogger(__name__)
        items = self._detail_panel.get_current_items() or []
        if row < 0 or row >= len(items):
            logger.warning(f"[🖥UI] _on_stock_in_single_requested row={row} out of range (items={len(items)})")
            return
        item = items[row]
        from widgets.order_summary.inbound_dialog import InboundDialog
        dialog = InboundDialog(item, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            pi_id = self._current_order.get("id") if self._current_order else None
            logger.info(f"[🖥UI] ➡ inbound_pi_item row={row}, item_id={item.get('id')}, pi_id={pi_id}, data={data}")
            try:
                resp = self.api_client.inbound_pi_item(item.get("id"), data["quantity"], data["inspector"], data["remark"])
                logger.info(f"[🖥UI] ✅ inbound response: {resp}")
                self.itemUpdated.emit()
                # 2026-06-23：入库后服务端数据已变更，拉取最新明细重渲染详情面板
                if pi_id:
                    detail = self.api_client.get_pi_detail(pi_id) or {}
                    self._detail_panel.show_order_detail(detail, detail.get("items") or [])
                    self._current_order = detail
                    logger.info(f"[🖥UI] ↻ detail panel refreshed, items count={len(detail.get('items') or [])}")
            except Exception as e:
                logger.error(f"[🖥UI] ❌ inbound failed: {e}")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "错误", f"入库失败: {e}")

    def _on_batch_inbound_clicked(self):
        """全部入库（模式二按钮）"""
        items = self._detail_panel.get_current_items() or []
        if not items:
            return
        from widgets.order_summary.batch_inbound_dialog import BatchInboundDialog
        dialog = BatchInboundDialog(items, self)
        if dialog.exec() == QDialog.Accepted:
            entries, inspector = dialog.get_data()
            pi_id = self._current_order.get("id")
            try:
                self.api_client.inbound_pi_items_batch(pi_id, entries, inspector)
                self.itemUpdated.emit()
                # 2026-06-23：批量入库后拉取最新明细重渲染
                if pi_id:
                    detail = self.api_client.get_pi_detail(pi_id) or {}
                    self._detail_panel.show_order_detail(detail, detail.get("items") or [])
                    self._current_order = detail
            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "错误", f"批量入库失败: {e}")

    @property
    def order_list_group(self):
        """兼容属性：列表 GroupBox"""
        return self._list_group
    
    @property
    def order_detail_group(self):
        """兼容属性：详情 GroupBox"""
        return self._detail_group