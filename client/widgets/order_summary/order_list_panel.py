# -*- coding: utf-8 -*-
"""
订单列表面板

文件：client/widgets/order_summary/order_list_panel.py
用途：订单列表表格组件，显示订单概要信息

创建日期：2026-06-04
来源：main.py L3604-3650

主要功能：
- 创建订单列表表格（10列 - 4.1 迭代后）
- 显示订单概要（订单号、客户、日期、金额、状态）
- 处理点击/双击事件
- 搜索过滤
- 状态筛选
- 多选（列0复选框）
- PI操作列（生成PI/重新生成）
- 编辑列

调用方式：
```python
from widgets.order_summary import OrderListPanel

panel = OrderListPanel(api_client)
table = panel.create_table()

# 更新数据
panel.update_table(orders)

# 连接信号
panel.cellClicked.connect(main_window._on_order_list_click)
```

依赖：
- PySide6.QtWidgets
- PySide6.QtCore
- PySide6.QtGui
- .constants
"""

from PySide6.QtWidgets import (
    QWidget, QTableWidget, QTableWidgetItem, QLabel, QPushButton,
    QHeaderView, QAbstractItemView, QGroupBox, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLineEdit, QComboBox
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QColor

import logging
logger = logging.getLogger(__name__)

from .constants import (
    ORDER_LIST_HEADERS,
    ORDER_LIST_COLUMN_COUNT,
    ORDER_LIST_COLUMN_WIDTHS,
    ORDER_LIST_ROW_HEIGHT,
    HIDDEN_PI_ID_COLUMN,
    PAYMENT_STATUS_COLORS,
)


class OrderListPanel(QWidget):
    """
    订单列表面板

    功能：
    - 显示订单概要列表（14列）
    - 列0: 选择（复选框）
    - 列1: ORDER NO.
    - 列2: 客户
    - 列3: 订单日期
    - 列4: 产品数
    - 列5: 总金额
    - 列6: 状态
    - 列7: 已付款       [2026-06-11 需求 38]
    - 列8: 未付款       [2026-06-11 需求 38]
    - 列9: 付款进度     [2026-06-11 需求 38]
    - 列10: 库存剩余 [6.2]
    - 列11: 添加付款(按钮) [2026-06-11 需求 38]
    - 列12: PI操作（多形态按钮）
    - 列13: 编辑

    信号：
    - cellClicked: 单元格点击（转发）
    - cellDoubleClicked: 单元格双击（转发）
    - piActionRequested: PI操作按钮点击 (order, mode)
    - paymentAddRequested: 添加付款按钮点击 (order)
    """

    # 转发信号（保持与 main.py 相同的签名）
    cellClicked = Signal(int, int)
    cellDoubleClicked = Signal(int, int)
    piActionRequested = Signal(object, str)  # (order_dict, mode: 'draft'|'order'|'ship')
    paymentAddRequested = Signal(object)     # (order_dict) [2026-06-11 需求 38]
    piDeleted = Signal(int)                  # 订单删除成功 (pi_id) [2026-06-15 需求 删除订单]
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self._orders = []
        self._table = None
        # 防抖定时器 - 搜索/筛选变化后延迟200ms再执行过滤
        from PySide6.QtCore import QTimer
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(200)
        self._filter_timer.timeout.connect(self._do_filter)
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        from PySide6.QtWidgets import QSizePolicy
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        # 设置 size policy 让 panel 占据所有可用空间
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # 搜索栏
        search_layout = QHBoxLayout()
        
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍 搜索订单号/OE号/客户/产品...")
        self._search_input.setFixedHeight(35)
        self._search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self._search_input)
        
        # 状态筛选
        self._status_filter = QComboBox()
        self._status_filter.addItems(["全部状态", "进行中", "已完成", "已取消"])
        self._status_filter.setFixedHeight(35)
        self._status_filter.currentTextChanged.connect(self._on_filter_changed)
        search_layout.addWidget(self._status_filter)

        # 客户筛选
        self._customer_filter = QComboBox()
        self._customer_filter.addItem("全部客户", None)
        self._customer_filter.setFixedHeight(35)
        self._customer_filter.setMinimumWidth(120)
        self._customer_filter.currentIndexChanged.connect(self._on_filter_changed)
        search_layout.addWidget(self._customer_filter)
        
        # 清除筛选
        clear_btn = QPushButton("🗑 清除")
        clear_btn.setFixedWidth(70)
        clear_btn.setFixedHeight(35)
        clear_btn.clicked.connect(self._on_clear_filter)
        search_layout.addWidget(clear_btn)
        
        layout.addLayout(search_layout)
        
        # 表格
        self._table = self._create_table()
        layout.addWidget(self._table)
        
        # 状态栏
        self._status_label = QLabel("准备就绪")
        self._status_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(self._status_label)
    
    def _create_table(self) -> QTableWidget:
        """创建订单列表表格"""
        table = QTableWidget()
        table.setColumnCount(ORDER_LIST_COLUMN_COUNT)
        table.setHorizontalHeaderLabels(ORDER_LIST_HEADERS)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # 设置列宽
        for col, width in ORDER_LIST_COLUMN_WIDTHS.items():
            table.setColumnWidth(col, width)

        # 隐藏 PI_ID 列（仅用于内部数据存储）
        table.setColumnHidden(HIDDEN_PI_ID_COLUMN, True)

        # 表格属性
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setDefaultSectionSize(36)  # 固定行高
        table.verticalHeader().setVisible(False)  # 隐藏行号
        table.setMinimumHeight(200)  # 确保表格有最小高度可见
        table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e5e7eb;
                border-radius: 4px;
            }
        """)
        
        # 连接信号
        table.cellClicked.connect(self._on_cell_clicked)
        table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        # 2026-06-12 需求#42：右键菜单
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self._on_context_menu)

        return table
    
    @Slot(int, int)
    def _on_cell_clicked(self, row, column):
        """单元格点击事件（转发）"""
        self.cellClicked.emit(row, column)
    
    @Slot(int, int)
    def _on_cell_double_clicked(self, row, column):
        """单元格双击事件（转发）"""
        self.cellDoubleClicked.emit(row, column)

    # 2026-06-12 需求#42：右键菜单
    @Slot("QPoint")
    def _on_context_menu(self, pos: "QPoint"):
        """右键菜单"""
        import logging
        logger2 = logging.getLogger(__name__)
        
        row = self._table.rowAt(pos.y())
        if row < 0:
            return
        order = self.get_order_at_row(row)
        if not order:
            logger2.warning("[右键菜单] order 为空")
            return
        pi_id = order.get("id")
        pi_no = order.get("pi_no") or ""
        if pi_id is None or not pi_no:
            logger2.warning(f"[右键菜单] pi_id 或 pi_no 为空: pi_id={pi_id}, pi_no={pi_no}")
            return

        logger2.info(f"[右键菜单] 显示菜单, pi_id={pi_id}, pi_no={pi_no}")
        
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        save_snapshot = menu.addAction("💾 保存快照")
        save_snapshot.triggered.connect(lambda: self._on_save_snapshot(pi_id, row))
        
        # 2026-06-15 新增：查看历史记录
        view_history = menu.addAction("📜 历史记录")
        view_history.triggered.connect(lambda: self._on_view_history(pi_id, pi_no))
        
        # 2026-06-15 需求：删除订单（仅删点中行，与多选无关）
        # 2026-07-02：临时产品功能已去除，所有 PI 均可删除
        delete_action = menu.addAction("删除订单")
        delete_action.triggered.connect(lambda: self._on_delete_order(pi_id, row, pi_no))

        # 缺货标记切换
        current_storage = order.get('storage_status', '')
        if current_storage == '缺货':
            shortage_action = menu.addAction("🔓 取消缺货标记")
            shortage_action.triggered.connect(lambda: self._toggle_shortage(pi_id, row, False))
        else:
            shortage_action = menu.addAction("🔒 标记缺货")
            shortage_action.triggered.connect(lambda: self._toggle_shortage(pi_id, row, True))

        # 用 popup() 而非 exec()：非阻塞，事件循环可继续运行
        menu.popup(self._table.viewport().mapToGlobal(pos))

    def _on_save_snapshot(self, pi_id: int, row: int):
        """保存快照"""
        import logging
        logger2 = logging.getLogger(__name__)
        
        logger2.info(f"[保存快照] _on_save_snapshot 被调用, pi_id={pi_id}")
        
        from widgets.pi_management.snapshot_dialog import SnapshotDialog
        dialog = SnapshotDialog(self)
        logger2.info(f"[保存快照] 显示对话框...")
        
        result = dialog.exec()
        logger2.info(f"[保存快照] 对话框结果: {result}")
        
        # PySide6: dialog.exec() 返回 1 表示 Accepted，0 表示 Rejected
        if result == 1:
            desc = dialog.get_change_desc()
            try:
                logger2.info(f"[保存快照] pi_id={pi_id}, desc={desc}")
                
                versions = self.api_client.get_pi_versions(pi_id)
                logger2.info(f"[保存快照] 当前版本列表: {versions}")
                
                latest_no = versions[0]["version_no"] if versions else 0
                logger2.info(f"[保存快照] 最新版本号: {latest_no}")
                
                result = self.api_client.save_pi_snapshot(pi_id, desc, latest_no)
                logger2.info(f"[保存快照] 保存结果: {result}")
                
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "成功", f"快照已保存（v{result['version_no']}）")
            except Exception as e:
                logger2.error(f"[保存快照] 失败: {e}")
                from PySide6.QtWidgets import QMessageBox
                if "409" in str(e) or "冲突" in str(e):
                    QMessageBox.warning(self, "冲突", "已被其他人修改，请刷新后重试")
                else:
                    QMessageBox.warning(self, "错误", f"保存失败: {e}")

    def _on_view_history(self, pi_id: int, pi_no: str):
        """查看历史记录"""
        from widgets.order_history_dialog import OrderHistoryDialog
        from widgets.order_version_detail_dialog import OrderVersionDetailDialog
        
        dialog = OrderHistoryDialog(self.api_client, pi_id, pi_no, self)
        dialog.view_version.connect(lambda version: self._on_view_version_detail(pi_id, version))
        dialog.exec()

    def _on_view_version_detail(self, pi_id: int, version: dict):
        """查看版本详情"""
        from widgets.order_version_detail_dialog import OrderVersionDetailDialog
        
        detail_dialog = OrderVersionDetailDialog(self.api_client, pi_id, version, self)
        detail_dialog.exec()

    def _on_delete_order(self, pi_id: int, row: int, pi_no: str):
        """
        删除订单（右键菜单触发）。

        2026-07-02：临时产品功能已去除，所有 PI 均可删除。

        Args:
            pi_id: PI 数据库主键
            row: 表格行号（用于成功后移除）
            pi_no: 订单号（仅用于确认对话框展示）
        """
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确认删除订单 {pi_no}？该操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            result = self.api_client.batch_delete_pi([pi_id])
        except Exception as e:
            # 网络/HTTP 异常
            QMessageBox.warning(self, "删除失败", str(e))
            return

        # 业务异常：后端不抛异常，错误进 result["errors"]
        errors = (result or {}).get("errors") or []
        if errors or (result or {}).get("deleted", 0) == 0:
            msg = "; ".join(errors) if errors else "删除失败（未知原因）"
            QMessageBox.warning(self, "删除失败", msg)
            return

        # 成功：本地移除行 + 同步 _orders + 状态标签 + emit
        if row < self._table.rowCount():
            self._table.removeRow(row)
        self._orders = [o for o in self._orders if o.get("id") != pi_id]
        self._update_status_label()
        self.piDeleted.emit(pi_id)

    def _toggle_shortage(self, pi_id: int, row: int, mark_as_shortage: bool):
        """切换缺货标记"""
        try:
            new_status = "缺货" if mark_as_shortage else None
            result = self.api_client.update_pi_storage_status(pi_id, new_status)

            # 更新本地数据
            order = self.get_order_at_row(row)
            if order:
                order['storage_status'] = result.get('storage_status')
                # 刷新当前行显示（背景色 + 库存列）
                self._refresh_row_style(row, order)
                logger.info(f"[缺货标记] PI={pi_id} → {new_status or '取消'}")
        except Exception as e:
            logger.error(f"[缺货标记] 失败: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "操作失败", f"更新缺货状态失败：{e}")

    def _refresh_row_style(self, row: int, order: dict):
        """刷新单行样式（背景色 + 库存列文字）"""
        from PySide6.QtGui import QColor as _QC

        is_shortage = order.get('storage_status') == '缺货'
        bg_color = _QC('#FEF3C7') if is_shortage else None  # 浅黄

        for col in range(self._table.columnCount()):
            item = self._table.item(row, col)
            if not item:
                continue
            if bg_color:
                item.setBackground(bg_color)
            else:
                item.setBackground(_QC('#FFFFFF'))

        # 更新库存列显示（列10）
        inv_item = self._table.item(row, 10)
        if inv_item and is_shortage:
            inv_item.setText("🔒 缺货")
            inv_item.setForeground(_QC('#D97706'))

    # 2026-06-12 需求#42：从订单列表保存正式纪录
    def _on_save_formal_from_list(self, order: dict):
        """PI操作列"保存正式纪录"按钮点击"""
        pi_id = order.get("id")
        pi_no = order.get("pi_no") or ""
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "确认保存",
            f"确定将当前状态固化为正式纪录？\nPI 编号：{pi_no}\n之前保存的正式纪录将被覆盖。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            result = self.api_client.save_formal_record(pi_id)
            QMessageBox.information(self, "成功", f"正式纪录已保存\n{result.get('file_path', '')}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {e}")
    
    def get_table(self) -> QTableWidget:
        """获取表格组件"""
        return self._table
    
    @property
    def table(self) -> QTableWidget:
        """获取表格组件（兼容属性）"""
        return self._table
    
    def clear_table(self):
        """清空表格"""
        self._table.setRowCount(0)
    
    def update_table(self, orders: list):
        """
        更新表格数据（完整加载，含诊断日志）

        Args:
            orders: 订单列表
        """
        self._orders = orders or []
        self.clear_table()

        for order in self._orders:
            try:
                self._add_order_row(order)
            except Exception as e:
                logger.warning(f"[OrderListPanel] 添加行异常 pi_no={order.get('pi_no', 'N/A')}: {e}")

        self._update_status_label()
    
    def _add_order_row(self, order: dict):
        """添加一行订单数据"""
        row = self._table.rowCount()
        self._table.insertRow(row)
        
        # 列0: 选择（复选框）
        chkbox = QCheckBox()
        chkbox_widget = QWidget()
        chkbox_layout = QHBoxLayout(chkbox_widget)
        chkbox_layout.setContentsMargins(0, 0, 0, 0)
        chkbox_layout.setAlignment(Qt.AlignCenter)
        chkbox_layout.addWidget(chkbox)
        self._table.setCellWidget(row, 0, chkbox_widget)
        
        # 列1: ORDER NO.
        self._table.setItem(row, 1, QTableWidgetItem(order.get('pi_no', '')))
        
        # 列2: 客户
        self._table.setItem(row, 2, QTableWidgetItem(order.get('customer_name', '')))
        
        # 列3: 订单日期
        order_date = order.get('order_date') or order.get('created_at', '')
        if order_date:
            order_date = str(order_date)[:10]
        self._table.setItem(row, 3, QTableWidgetItem(order_date))
        
        # 列4: 产品数（兼容多种字段名：item_count / product_count / items 长度）
        item_count = (
            order.get('item_count')
            or order.get('product_count', 0)
            or len(order.get('items', []) or [])
        )
        self._table.setItem(row, 4, QTableWidgetItem(str(item_count)))
        
        # 列5: 总金额
        total_amount = order.get('total_amount', 0) or 0
        currency = order.get('currency', 'USD')
        self._table.setItem(row, 5, QTableWidgetItem(f"{total_amount:.2f} {currency}"))
        
        # 列6: 状态
        status_val = order.get('status', '')
        status_text = self._get_status_text(status_val)
        status_item = QTableWidgetItem(status_text)
        self._table.setItem(row, 6, status_item)
        
        # 列7: 已付款 [2026-06-11 需求 38]
        paid_amount = float(order.get('paid_amount', 0) or 0)
        currency = order.get('currency', 'USD')
        paid_item = QTableWidgetItem(f"{paid_amount:.2f} {currency}")
        paid_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._table.setItem(row, 7, paid_item)

        # 列8: 未付款 [2026-06-11 需求 38]
        unpaid_amount = float(order.get('unpaid_amount', 0) or 0)
        unpaid_item = QTableWidgetItem(f"{unpaid_amount:.2f} {currency}")
        unpaid_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        # 未付款 = 0 时标绿
        if unpaid_amount == 0 and paid_amount > 0:
            unpaid_item.setForeground(Qt.darkGreen)
        self._table.setItem(row, 8, unpaid_item)

        # 列9: 付款进度 [2026-06-11 需求 38]
        progress = float(order.get('payment_progress', 0) or 0)
        status_text = order.get('payment_status', '未付款')
        progress_item = QTableWidgetItem(f"{progress:.0f}%")
        progress_item.setTextAlignment(Qt.AlignCenter)
        color_hex = PAYMENT_STATUS_COLORS.get(status_text, "#9ca3af")
        from PySide6.QtGui import QColor
        progress_item.setForeground(QColor(color_hex))
        self._table.setItem(row, 9, progress_item)

        # 列10: 库存剩余 [6.2] (原列 8)
        inventory_item = self._get_inventory_item(order)
        self._table.setItem(row, 10, inventory_item)

        # 列11: 添加付款按钮 [2026-06-11 需求 38]
        payment_btn = QPushButton("💰 付款")
        payment_btn.setFixedWidth(70)
        # 始终可点：即使 unpaid=0 也允许录入首笔收款
        if unpaid_amount > 0:
            payment_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton:hover { background-color: #2563eb; }
            """)
        else:
            # 未付款时用紫色提示"待收款"
            payment_btn.setStyleSheet("""
                QPushButton {
                    background-color: #8b5cf6;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton:hover { background-color: #7c3aed; }
            """)
        payment_btn.clicked.connect(lambda checked, o=order: self._on_payment_add(o))
        self._table.setCellWidget(row, 11, payment_btn)

        # 列12: PI操作(原列 9)
        action_state = self._get_order_action_state(order)
        pi_btn = QPushButton(action_state['text'])
        pi_btn.setFixedWidth(100)
        pi_btn.setEnabled(action_state['enabled'])
        mode = action_state.get('mode', 'draft')
        color_map = {
            'draft':  ('#f59e0b', '#d97706'),    # 橙色（保留兼容）
            'order':  ('#f59e0b', '#d97706'),    # 橙色
            'ship':   ('#10b981', '#059669'),    # 绿色
            'done':   ('#9ca3af', '#9ca3af'),    # 灰色
            'formal': ('#7c3aed', '#6d28d9'),   # 紫色 [2026-06-12 需求#42]
        }
        bg, hover = color_map.get(mode, color_map['draft'])
        pi_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:disabled {{ background-color: #9ca3af; color: white; }}
        """)
        # 2026-06-12 需求#42：formal 模式直接保存正式纪录
        if mode == 'formal':
            pi_btn.clicked.connect(lambda checked, o=order: self._on_save_formal_from_list(o))
        else:
            pi_btn.clicked.connect(lambda checked, o=order, m=mode: self._on_pi_action(o, m))
        self._table.setCellWidget(row, 12, pi_btn)

        # 列13: 编辑按钮(原列 10)
        edit_btn = QPushButton("编辑")
        edit_btn.setFixedWidth(60)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        self._table.setCellWidget(row, 13, edit_btn)

        # 列14: PI_ID(隐藏列,内部使用)
        # [2026-06-16 需求 46] Excel 41 字段在模式二(详情)显示, 模式一只保留订单级汇总列
        pi_id = order.get('id')
        pi_id_item = QTableWidgetItem(str(pi_id) if pi_id is not None else '')
        pi_id_item.setFlags(pi_id_item.flags() & ~Qt.ItemIsEditable)  # 不可编辑
        self._table.setItem(row, HIDDEN_PI_ID_COLUMN, pi_id_item)

        # 缺货标记：整行背景色
        if order.get('storage_status') == '缺货':
            from PySide6.QtGui import QColor as _QC2
            for col in range(self._table.columnCount()):
                item = self._table.item(row, col)
                if item:
                    item.setBackground(_QC2('#FEF3C7'))  # 浅黄

    def _get_status_text(self, status) -> str:
        """获取状态文本"""
        status_map = {
            'draft': '草稿',
            'pending': '待确认',
            'confirmed': '已确认',
            'in_progress': '进行中',
            'completed': '已完成',
            'cancelled': '已取消',
            0: '草稿',
            1: '进行中',
            2: '待确认',
            3: '已确认',
            4: '已完成',
            5: '已取消'
        }
        return status_map.get(status, str(status) if status else '未知')
    
    def _get_payment_text(self, order: dict) -> str:
        """
        获取客户款项显示文本
        
        规则（4.1 迭代）：
        - 已结清（≥99.9%）：✅ 已结清（绿色）
        - 部分付款（30%-99%）：🟡 已收 X%（黄色）
        - 已收（<30%）：🔴 已收 X%（红色）
        - 部分付款（无总额）：🟡 部分付款（黄色）
        - 未付款：⚪ 未付款（灰色）
        """
        total = order.get('total_amount', 0) or 0
        paid = order.get('paid_amount', 0) or 0
        
        if total <= 0:
            return "⚪ 未付款"
        
        percent = (paid / total) * 100
        
        if percent >= 99.9:
            return "✅ 已结清"
        elif percent >= 30:
            return f"🟡 已收 {percent:.0f}%"
        elif percent > 0:
            return f"🔴 已收 {percent:.0f}%"
        else:
            return "⚪ 未付款"
    
    def _get_inventory_item(self, order: dict) -> QTableWidgetItem:
        """
        获取库存剩余显示项 [6.2]

        规则（2026-06-23 收敛：3 分支对应 storage_status 三值）：
        - 已入库 / has_inventory / inventory_qty > 0：✅ 有库存（绿色）
        - 部分入库：◐ 部分入库（深黄）
        - 其他：✕ 无库存（红色）
        """
        has_inventory = order.get('has_inventory', False)
        inventory_qty = order.get('inventory_quantity', 0) or 0
        storage_status = order.get('storage_status', '')

        if storage_status == '缺货':
            text, color = "🔒 缺货", QColor('#D97706')  # 橙色
        elif storage_status == '已入库' or has_inventory or inventory_qty > 0:
            text, color = "✅ 有库存", Qt.green
        elif storage_status == '部分入库':
            text, color = "◐ 部分入库", Qt.darkYellow
        else:
            text, color = "✕ 无库存", Qt.red

        item = QTableWidgetItem(text)
        item.setForeground(color)
        item.setTextAlignment(Qt.AlignCenter)
        return item
    
    def _get_order_action_state(self, order: dict) -> dict:
        """
        根据订单状态确定 PI 操作按钮的多形态配置 [6.0.1]
        
        Returns: dict {
            'text': str,       # 按钮文本
            'color': str,      # 背景色 (CSS hex)
            'hover': str,      # hover 背景色
            'enabled': bool,   # 是否可点击
            'mode': str        # 'draft' | 'order' | 'ship' | 'done'
        }
        """
        status_str = str(order.get('status', '进行中'))
        pi_no = order.get('pi_no') or order.get('order_no') or ''
        is_temp_pi = pi_no.endswith('?')
        
        # 已完成 / 已取消 → 灰色按钮（不可点击）
        if '完成' in status_str or '取消' in status_str:
            return {'text': '已完成', 'color': '#9ca3af', 'hover': '#9ca3af',
                    'enabled': False, 'mode': 'done'}
        
        # 进行中 + 临时PI → 完成下单（橙色）
        if is_temp_pi:
            return {'text': '完成下单', 'color': '#f59e0b', 'hover': '#d97706',
                    'enabled': True, 'mode': 'order'}
        
        # 进行中 + 已有正式PI号 → 完成出货（绿色）
        if pi_no and '进行中' in status_str:
            return {'text': '完成出货', 'color': '#10b981', 'hover': '#059669',
                    'enabled': True, 'mode': 'ship'}
        
        # 默认 fallback：保存正式纪录（紫色）[2026-06-12 需求#42]
        # 2026-07-02：临时产品功能已去除，所有订单均可保存正式纪录
        return {'text': '保存正式纪录', 'color': '#7c3aed', 'hover': '#6d28d9',
                'enabled': True, 'mode': 'formal'}
    
    def _on_pi_action(self, order: dict, mode: str):
        """PI操作按钮点击回调 - 发射信号由 main_window 处理"""
        self.piActionRequested.emit(order, mode)

    def _on_payment_add(self, order: dict):
        """添加付款按钮点击 - 发射信号由 main_window 处理 [2026-06-11 需求 38]"""
        self.paymentAddRequested.emit(order)
    
    def _on_search_changed(self, text: str):
        """搜索框变化 - 防抖触发过滤"""
        self._filter_timer.start()

    def _on_filter_changed(self, text: str):
        """状态/客户筛选变化 - 防抖触发过滤"""
        self._filter_timer.start()

    def _do_filter(self):
        """执行即时前端过滤（不请求API）"""
        search_text = self._search_input.text().strip()
        status = self._status_filter.currentText()
        customer_id = self._customer_filter.currentData()

        filtered = self.filter_orders(
            search_text=search_text,
            status=status,
            customer_id=customer_id
        )
        # 直接更新表格显示（不清空原始数据）
        self._update_filtered_table(filtered)
    
    def _on_clear_filter(self):
        """清除筛选"""
        self._search_input.clear()
        self._status_filter.setCurrentIndex(0)
        self._customer_filter.setCurrentIndex(0)

    def _update_filtered_table(self, filtered_orders: list):
        """轻量级更新表格（仅用于前端筛选，无诊断日志）"""
        self.clear_table()
        for order in filtered_orders:
            self._add_order_row(order)
        self._status_label.setText(f"共 {len(filtered_orders)} / {len(self._orders)} 条")
    
    def _update_status_label(self):
        """更新状态栏"""
        self._status_label.setText(f"共 {len(self._orders)} 条订单")
    
    def get_selected_row(self) -> int:
        """获取选中的行号"""
        return self._table.currentRow()
    
    def get_selected_order(self) -> dict:
        """获取选中的订单"""
        row = self.get_selected_row()
        if row < 0 or row >= len(self._orders):
            return {}
        return self._orders[row]
    
    def get_order_at_row(self, row: int) -> dict:
        """获取指定行的订单"""
        if row < 0 or row >= len(self._orders):
            return {}
        return self._orders[row]
    
    def select_row(self, row: int):
        """选中指定行"""
        if row >= 0 and row < self._table.rowCount():
            self._table.selectRow(row)
    
    def get_orders(self) -> list:
        """获取所有订单"""
        return self._orders
    
    def set_orders(self, orders: list):
        """设置订单列表"""
        self._orders = orders or []
        self.update_table(self._orders)

    def load_customers(self):
        """加载客户列表到筛选下拉框"""
        try:
            customers = self.api_client.get_customers() or []
            # 保留"全部客户"选项，追加客户
            current = self._customer_filter.currentData()
            self._customer_filter.clear()
            self._customer_filter.addItem("全部客户", None)
            for c in customers:
                name = c.get('company_name_en') or c.get('company_name_cn') or f"客户{c.get('id', '')}"
                self._customer_filter.addItem(name, c.get('id'))
            # 恢复之前选中项
            if current is not None:
                for i in range(self._customer_filter.count()):
                    if self._customer_filter.itemData(i) == current:
                        self._customer_filter.setCurrentIndex(i)
                        break
        except Exception as e:
            logger.warning(f"[OrderListPanel] 加载客户列表失败: {e}")

    def get_current_customer_id(self):
        """获取当前选中的客户ID"""
        return self._customer_filter.currentData()
    
    def get_selected_pis(self) -> list[int]:
        """获取当前勾选的PI ID列表（模式一）"""
        selected = []
        for row in range(self._table.rowCount()):
            # 修复：列0的 cellWidget 是 QWidget 包装器，需要从中找出真正的 QCheckBox
            widget = self._table.cellWidget(row, 0)
            if not widget:
                continue
            chkbox = widget.findChild(QCheckBox)
            if not chkbox or not chkbox.isChecked():
                continue

            # 修复：从隐藏列（PI_ID）读取 PI 数据库主键 ID
            pi_id_item = self._table.item(row, HIDDEN_PI_ID_COLUMN)
            if not pi_id_item:
                continue
            pi_id_text = pi_id_item.text().strip()
            if not pi_id_text:
                continue
            try:
                selected.append(int(pi_id_text))
            except ValueError:
                logger.warning(
                    f"[OrderListPanel.get_selected_pis] 第 {row} 行 PI_ID 解析失败: {pi_id_text!r}"
                )
        return selected
    
    def filter_orders(self, search_text: str = "", status: str = "全部状态", customer_id=None) -> list:
        """
        过滤订单列表

        Args:
            search_text: 搜索关键词
            status: 状态筛选
            customer_id: 客户ID筛选

        Returns:
            list: 过滤后的订单列表
        """
        filtered = self._orders.copy()

        # 客户过滤
        if customer_id is not None:
            filtered = [o for o in filtered if o.get('customer_id') == customer_id]

        # 状态过滤
        if status and status != "全部状态":
            status_map = {
                "进行中": ["进行中", "in_progress", 1],
                "已完成": ["已完成", "completed", 4],
                "已取消": ["已取消", "cancelled", 5]
            }
            target_statuses = status_map.get(status, [status])
            filtered = [o for o in filtered if o.get('status') in target_statuses]
        
        # 搜索过滤
        if search_text:
            text = search_text.lower()
            filtered = [
                o for o in filtered
                if (text in str(o.get('pi_no', '')).lower()
                    or text in str(o.get('customer_name', '')).lower()
                    or text in str(o.get('order_no', '')).lower())
            ]
        
        return filtered