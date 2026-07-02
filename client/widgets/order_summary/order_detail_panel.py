# -*- coding: utf-8 -*-
"""
订单详情面板

文件：client/widgets/order_summary/order_detail_panel.py
用途：订单详情表格组件，显示41列产品信息

创建日期：2026-06-04
来源：main.py L3403-3465, L4065-4447

主要功能：
- 创建订单详情表格（41列）
- 填充各组数据（A-F组）
- 处理双击编辑事件
- 状态灯管理

调用方式：
```python
from widgets.order_summary import OrderDetailPanel

panel = OrderDetailPanel(api_client)
table = panel.create_table()

# 显示订单详情
panel.show_order_detail(order, items)

# 连接信号
panel.cellDoubleClicked.connect(main_window._on_order_detail_double_click)
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
    QMessageBox, QCheckBox, QMenu, QDialog
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor, QBrush, QFont, QPixmap, QImage, QAction
import urllib.request
import concurrent.futures
import threading
from typing import Any, Dict, List

from config import Config

from .constants import (
    ORDER_DETAIL_HEADERS,
    ORDER_DETAIL_COLUMN_COUNT,
    ORDER_DETAIL_COLUMN_WIDTHS,
    ORDER_DETAIL_ROW_HEIGHT,
    COLORS
)


class OrderDetailPanel(QWidget):
    """
    订单详情面板
    
    功能：
    - 显示订单产品详情（41列）
    - A组: 基础信息（列0-8）
    - B组: 价格财务（列9-20）
    - C组: 供应商采购（列21-26）
    - D组: 物流入库（列27-29）
    - E组: 产品细节（列30-38）
    - F组: 其他属性（列39-40）
    - 状态灯管理（4个圆点+文字）
    
    信号：
    - cellDoubleClicked: 单元格双击（转发）
    """
    
    # 转发信号（保持与 main.py 相同的签名）
    cellDoubleClicked = Signal(int, int)
    # 操作按钮信号
    purchaseRequested = Signal()       # 顶部"采购全部"按钮点击
    supplementRequested = Signal()     # 补充商品按钮点击
    backRequested = Signal()           # 返回订单总表按钮点击
    # 2026-06-11 任务 4：右键菜单信号
    purchaseSingleRequested = Signal(int)        # 右键"采购该产品"，参数：行索引
    purchaseRepurchaseRequested = Signal(int)    # 右键"重新采购"，参数：行索引
    # 2026-06-12 需求#40：入库 / 删除信号
    stockInSingleRequested = Signal(int)          # 右键"入库该产品"，参数：行索引
    deleteItemRequested = Signal(int)            # 右键"删除商品"，参数：行索引
    # 2026-06-23：正式PI检查完成信号（参数：True=有正式PI，False=无）
    formalRecordChecked = Signal(bool)
    # 2026-06-23：正式PI保存完成信号（由 detail_panel 内部按钮触发，通知外部）
    formalRecordSaved = Signal()
    # 2026-07-02：编辑产品 / 更换供应商 / 采购快照 / 访问店铺网站
    editProductRequested = Signal(int, int)          # 行索引, 触发列号(-1 表示右键菜单)
    changeSupplierRequested = Signal(int)            # 行索引
    purchaseSnapshotRequested = Signal(int)          # 行索引
    openShopUrlRequested = Signal(int)               # 行索引

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self._current_order = None
        self._current_items = []
        self._table = None
        self._status_dots = []
        self._status_labels = []
        self._selected_items = set()  # 记录选中的行索引
        self._checkboxes = []  # 记录所有复选框
        self._current_row = -1  # 当前点击选中的行
        # 2026-06-14：数据服务订阅
        self._service = None
        # 2026-06-23：当前订单是否有正式PI（"保存正式记录" 后才置为 True）
        # 未保存正式PI 时，采购/入库按钮全部禁用
        self._has_formal_record = False
        # 图片缓存
        self._image_cache = {}
        self._image_cache_lock = threading.Lock()
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="order_detail_img")
        self._init_ui()

    def attach_service(self, service):
        """订阅 OrderService.item_removed 信号，单品删除时同步内部状态

        Args:
            service: OrderService 实例
        """
        if self._service is service:
            return
        # 解绑旧的
        if self._service is not None:
            try:
                self._service.item_removed.disconnect(self._on_item_removed)
            except (TypeError, RuntimeError):
                pass
        self._service = service
        service.item_removed.connect(self._on_item_removed)
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(0)
        
        # 详情顶部标题栏
        header_widget = self._create_header()
        layout.addWidget(header_widget)
        
        # 详情表格
        self._table = self._create_table()
        layout.addWidget(self._table)

        # 2026-06-11 任务 4：启用右键菜单
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)

        # 连接双击信号
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self._table.cellClicked.connect(self._on_detail_table_clicked)

        # 2026-07-02：连接内联编辑保存信号
        self._init_table_connections()

    def _create_header(self) -> QWidget:
        """创建详情头部（返回按钮 + 标题 + 状态灯 + 操作按钮）"""
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 10, 0, 10)
        
        # 返回订单总表按钮
        self._back_btn = QPushButton("← 返回订单总表")
        self._back_btn.setFixedWidth(130)
        self._back_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #d1d5db;
                color: #374151;
                background: transparent;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #f3f4f6; }
        """)
        self._back_btn.clicked.connect(self.backRequested.emit)
        header_layout.addWidget(self._back_btn)
        
        header_layout.addSpacing(12)
        
        # 标题标签
        self._title_label = QLabel("📋 订单详情（点击下方列表查看）")
        self._title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        self._title_label.setStyleSheet("color: #1f2937;")
        header_layout.addWidget(self._title_label)
        
        # 状态灯容器
        self._status_widget = QWidget()
        status_layout = QHBoxLayout(self._status_widget)
        status_layout.setContentsMargins(8, 0, 0, 0)
        status_layout.setSpacing(8)
        
        self._status_dots = []
        self._status_labels = []
        default_texts = ["正式", "未采", "有库", "无票"]
        for text in default_texts:
            dot = QLabel()
            dot.setFixedSize(12, 12)
            dot.setStyleSheet(f"background-color: {COLORS['readonly_fg']}; border-radius: 6px;")
            status_layout.addWidget(dot)
            self._status_dots.append(dot)

            label = QLabel(text)
            label.setStyleSheet("color: #6b7280; font-size: 12px;")
            status_layout.addWidget(label)
            self._status_labels.append(label)

        # 2026-06-26: 正式PI 状态提示（默认隐藏，检查后根据状态显示）
        self._formal_hint_label = QLabel()
        self._formal_hint_label.setStyleSheet("""
            QLabel {
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self._formal_hint_label.setVisible(False)
        status_layout.addWidget(self._formal_hint_label)

        header_layout.addWidget(self._status_widget)
        header_layout.addStretch()
        
        # 2026-06-26: 列筛选按钮
        self._col_filter_btn = QPushButton("☰ 列筛选")
        self._col_filter_btn.setFixedWidth(80)
        self._col_filter_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #d1d5db;
                color: #374151;
                background: transparent;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #f3f4f6; }
        """)
        self._col_filter_btn.clicked.connect(self._show_column_filter_menu)
        header_layout.addWidget(self._col_filter_btn)
        
        # 采购按钮（2026-06-11 任务 4：文案改"采购全部"）
        self._purchase_btn = QPushButton("采购全部")
        self._purchase_btn.setFixedWidth(80)
        self._purchase_btn.setStyleSheet("""
            QPushButton {
                border: 2px solid #3b82f6;
                color: #3b82f6;
                background: transparent;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #eff6ff; }
        """)
        self._purchase_btn.clicked.connect(self.purchaseRequested.emit)
        # 2026-06-23：默认禁用，直到检查完正式PI后再启用
        self._purchase_btn.setEnabled(False)
        self._purchase_btn.setToolTip("请先点击『保存正式记录』锁定PI后再采购")
        header_layout.addWidget(self._purchase_btn)
        
        header_layout.addSpacing(8)
        
        # 补充商品按钮
        self._supplement_btn = QPushButton("补充商品")
        self._supplement_btn.setFixedWidth(100)
        self._supplement_btn.setStyleSheet("""
            QPushButton {
                border: 2px solid #3b82f6;
                color: #3b82f6;
                background: transparent;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #eff6ff; }
        """)
        self._supplement_btn.clicked.connect(self.supplementRequested.emit)
        header_layout.addWidget(self._supplement_btn)
        
        header_layout.addSpacing(8)
        
        # 2026-06-23：保存正式纪录按钮（锁定PI后才能采购/入库）
        self._formal_btn = QPushButton("📌 保存正式纪录")
        self._formal_btn.setFixedWidth(130)
        self._formal_btn.setStyleSheet("""
            QPushButton {
                border: 2px solid #7c3aed;
                color: #7c3aed;
                background: transparent;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #f5f3ff; }
            QPushButton:disabled {
                border-color: #d1d5db;
                color: #9ca3af;
                background: #f9fafb;
            }
        """)
        self._formal_btn.clicked.connect(self._on_save_formal_record)
        # 已保存过正式PI 时禁用（避免重复覆盖）
        self._formal_btn.setEnabled(False)
        self._formal_btn.setToolTip("请先点击此按钮保存正式纪录，锁定PI后再进行采购/入库操作")
        header_layout.addWidget(self._formal_btn)
        
        return header
    
    def _create_table(self) -> QTableWidget:
        """创建订单详情表格（41列）"""
        table = QTableWidget()
        table.setColumnCount(ORDER_DETAIL_COLUMN_COUNT)
        table.setHorizontalHeaderLabels(ORDER_DETAIL_HEADERS)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # 设置列宽
        for col, width in ORDER_DETAIL_COLUMN_WIDTHS.items():
            table.setColumnWidth(col, width)
        
        # 表格属性
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        # 2026-07-02：简单字段（文本/数字）允许内联编辑；复杂字段通过右键/双击打开 Dialog
        table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        table.verticalHeader().setDefaultSectionSize(ORDER_DETAIL_ROW_HEIGHT)
        table.setStyleSheet("""
            QTableWidget {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 4px;
            }
        """)

        return table

    def _init_table_connections(self):
        """连接表格编辑相关信号"""
        self._table.cellChanged.connect(self._on_cell_changed)

    @Slot(int, int)
    def _on_cell_changed(self, row, column):
        """单元格内容变化后失去焦点自动保存"""
        # 只处理允许内联编辑的列
        if column not in (10, 13, 14, 18, 19):
            return
        if row < 0 or row >= len(self._current_items):
            return
        item = self._current_items[row]
        table_item = self._table.item(row, column)
        if not table_item:
            return

        field_map = {
            10: ("unit_price", float),
            13: ("customer_prepayment", float),
            14: ("remaining_payment", float),
            18: ("shipping_fee", float),
            19: ("misc_fee", float),
        }
        field, converter = field_map[column]
        try:
            new_value = converter(table_item.text())
        except (ValueError, TypeError):
            return

        # 与旧值相同则不保存
        old_value = item.get(field)
        try:
            if old_value is not None and float(old_value) == new_value:
                return
        except (ValueError, TypeError):
            pass

        item[field] = new_value
        if self.api_client and item.get("id"):
            try:
                self.api_client.update_pi_item(item["id"], {field: new_value})
            except Exception as e:
                QMessageBox.warning(self, "保存失败", f"{field} 保存失败：{e}")
                # 回滚显示
                self.show_order_detail(self._current_order, self._current_items)

    @Slot(int, int)
    def _on_cell_double_clicked(self, row, column):
        """双击事件：可编辑列进入内联编辑；2-9/23/包装规格列打开编辑订单产品 Dialog"""
        if column in (10, 13, 14, 18, 19):
            # 让表格默认行为处理内联编辑
            return
        if column in (
            2, 3, 4, 5, 6, 7, 8, 9,      # 基础信息
            23,                           # 交货日期
            29, 30, 31, 33, 34, 37,       # 包装规格
        ):
            self.editProductRequested.emit(row, column)

    def open_edit_dialog(self, row: int, focus_column: int = -1):
        """外部调用：打开编辑订单产品 Dialog"""
        item = self.get_item_at_row(row)
        if not item:
            return
        from widgets.product_item_edit_dialog import ProductItemEditDialog
        dlg = ProductItemEditDialog(
            item=item,
            api_client=self.api_client,
            focus_column=focus_column,
            has_formal=self._has_formal_record,
            is_purchased=self._is_item_purchased(item),
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # Dialog 已内部调用 api_client.update_pi_item，刷新表格即可
            self.show_order_detail(self._current_order, self._current_items)
    
    def get_table(self) -> QTableWidget:
        """获取表格组件"""
        return self._table
    
    def clear_table(self):
        """清空表格"""
        self._table.setRowCount(0)
        self._table.setSortingEnabled(False)
    
    def show_order_detail(self, order: dict, items: list):
        """
        显示订单详情

        [2026-06-16 需求 46] 模式二(详情)显示 Excel 41 字段, 完全对齐 订单管理总表(1).xlsx

        Args:
            order: 订单数据
            items: 产品列表
        """
        self._current_order = order
        self._current_items = items or []

        # 2026-06-23：进入订单时异步检查是否有正式PI（"保存正式记录" 后才允许采购/入库）
        # 先 reset 成 False，避免上一个订单状态串扰
        self._has_formal_record = False
        self._check_formal_record_async(order.get('id'))

        # 清空选中状态
        self._selected_items.clear()
        self._checkboxes.clear()
        self._current_row = -1

        # 更新标题
        order_no = order.get('pi_no', order.get('order_no', ''))
        self._title_label.setText(f"ORDER NO.: {order_no}")

        # 清空并重新填充
        self.clear_table()

        currency = order.get('currency', 'USD')

        for idx, item in enumerate(self._current_items):
            row = self._table.rowCount()
            self._table.insertRow(row)

            # [2026-06-16 需求 46] 完全按 Excel 41 字段填充
            self._fill_excel_41_columns(row, idx, item, order, currency)

            # 需求#43: 采购数量 vs 订单数量不匹配 → 整行淡红背景
            order_qty = item.get('quantity', 0) or 0
            purchase_qty = item.get('purchase_quantity') or 0
            if purchase_qty and float(purchase_qty) != float(order_qty):
                bg = QBrush(QColor('#FFF0F0'))
                for col in range(ORDER_DETAIL_COLUMN_COUNT):
                    cell = self._table.item(row, col)
                    if cell:
                        cell.setBackground(bg)

        # 新增：高亮重复行
        self._apply_duplicate_highlight()

        self._table.setSortingEnabled(False)

        # 添加合计行
        self._add_summary_row()

        # 更新状态灯
        self._update_status_indicator(items)

    def _add_summary_row(self):
        """添加合计行（总箱数、总体积、总重量、总产品数）"""
        import math
        from PySide6.QtGui import QFont, QColor, QBrush

        items = self._current_items
        if not items:
            return

        # 统计
        total_cartons = 0
        total_volume = 0.0
        total_weight = 0.0
        total_quantity = 0
        total_amount = 0.0
        total_products = len(items)

        def num(obj, key, default=0):
            v = obj.get(key) if obj else default
            try:
                return float(v) if v not in (None, '') else default
            except (TypeError, ValueError):
                return default

        def g(obj, key, default=''):
            v = obj.get(key, default) if obj else default
            return v if v is not None else default

        def _local_carton_count(it):
            qty = num(it, 'quantity', 0)
            upc = num(it, 'units_per_carton', 0)
            if not upc:
                pack_spec = g(it, 'pack_spec') or g(it, 'packing_spec') or g(it, 'pcs_per_carton') or ''
                import re
                m = re.match(r'\s*(\d+(?:\.\d+)?)', str(pack_spec))
                if m:
                    upc = float(m.group(1))
            if qty > 0 and upc > 0:
                return int(math.ceil(qty / upc))
            return 0

        def _local_estimated_volume(it, cc):
            if not cc:
                return 0.0
            vol = num(it, 'carton_volume_m3', 0)
            if vol > 0:
                return round(vol * cc, 4)
            cs = g(it, 'carton_size') or g(it, 'box_size')
            if cs:
                import re
                m = re.search(r'(\d+(?:\.\d+)?)\s*[xX*×]\s*(\d+(?:\.\d+)?)\s*[xX*×]\s*(\d+(?:\.\d+)?)', str(cs))
                if m:
                    l, w, h = float(m.group(1)), float(m.group(2)), float(m.group(3))
                    return round((l * w * h / 1_000_000) * cc, 4)
            return 0.0

        def _local_total_weight(it, cc):
            if not cc:
                return 0.0
            gw = num(it, 'carton_gross_weight', 0) or num(it, 'gross_weight_kg', 0)
            if gw > 0:
                return round(gw * cc, 2)
            return 0.0

        for item in items:
            # 直接使用后端已经回填好的显示字段（避免重新解析 pack_spec 导致误差）
            total_cartons += num(item, 'carton_count', 0) or num(item, 'box_count', 0)
            total_volume += num(item, 'estimated_volume', 0)
            total_weight += num(item, 'total_weight', 0)
            total_quantity += num(item, 'quantity', 0)
            total_amount += num(item, 'total_price', 0) or (num(item, 'unit_price', 0) * num(item, 'quantity', 0))

        # 添加合计行
        row = self._table.rowCount()
        self._table.insertRow(row)

        # 样式设置
        bold_font = QFont("Microsoft YaHei", 9, QFont.Weight.Bold)
        summary_bg = QBrush(QColor('#E8F4FD'))  # 浅蓝色背景
        summary_color = QColor('#1E40AF')  # 深蓝色文字

        # 设置合并单元格（第一列显示"合计"）
        self._table.setItem(row, 0, QTableWidgetItem("📊 合计"))
        self._table.item(row, 0).setFont(bold_font)
        self._table.item(row, 0).setBackground(summary_bg)
        self._table.item(row, 0).setForeground(summary_color)

        # 总产品数（col 4 或其他合适位置）
        self._table.setItem(row, 4, QTableWidgetItem(f"共 {total_products} 种产品"))
        self._table.item(row, 4).setFont(bold_font)
        self._table.item(row, 4).setBackground(summary_bg)
        self._table.item(row, 4).setForeground(summary_color)

        # 总数量（col 9）
        self._table.setItem(row, 9, QTableWidgetItem(str(int(total_quantity))))
        self._table.item(row, 9).setFont(bold_font)
        self._table.item(row, 9).setBackground(summary_bg)
        self._table.item(row, 9).setForeground(summary_color)
        self._table.item(row, 9).setTextAlignment(0x0082 | 0x0004)

        # 总金额（col 11）- 使用订单币种
        currency = self._current_order.get('currency', 'USD') if self._current_order else 'USD'
        amount_text = f"{total_amount:.2f} {currency}"
        self._table.setItem(row, 11, QTableWidgetItem(amount_text))
        self._table.item(row, 11).setFont(bold_font)
        self._table.item(row, 11).setBackground(summary_bg)
        self._table.item(row, 11).setForeground(summary_color)
        self._table.item(row, 11).setTextAlignment(0x0082 | 0x0004)

        # 箱数（col 35）
        self._table.setItem(row, 35, QTableWidgetItem(str(total_cartons)))
        self._table.item(row, 35).setFont(bold_font)
        self._table.item(row, 35).setBackground(summary_bg)
        self._table.item(row, 35).setForeground(summary_color)
        self._table.item(row, 35).setTextAlignment(0x0082 | 0x0004)  # 右对齐

        # 总体积（col 36）
        vol_text = f"{total_volume:.4f} m³" if total_volume > 0 else "-"
        self._table.setItem(row, 36, QTableWidgetItem(vol_text))
        self._table.item(row, 36).setFont(bold_font)
        self._table.item(row, 36).setBackground(summary_bg)
        self._table.item(row, 36).setForeground(summary_color)
        self._table.item(row, 36).setTextAlignment(0x0082 | 0x0004)

        # 总重量（col 38）
        weight_text = f"{total_weight:.2f} kg" if total_weight > 0 else "-"
        self._table.setItem(row, 38, QTableWidgetItem(weight_text))
        self._table.item(row, 38).setFont(bold_font)
        self._table.item(row, 38).setBackground(summary_bg)
        self._table.item(row, 38).setForeground(summary_color)
        self._table.item(row, 38).setTextAlignment(0x0082 | 0x0004)

        # 使合计行不可选
        from PySide6.QtCore import Qt
        for col in range(self._table.columnCount()):
            cell = self._table.item(row, col)
            if cell:
                cell.setFlags(cell.flags() & ~Qt.ItemIsSelectable)

    def _apply_duplicate_highlight(self):
        """高亮订单详情中重复出现的行（按 product_id，缺失时回退 customer_code+oe_number）。"""
        if not self._current_items:
            return

        pid_groups: Dict[Any, List[dict]] = {}
        fallback_groups: Dict[str, List[dict]] = {}

        for item in self._current_items:
            product_id = item.get('product_id')
            if product_id:
                pid_groups.setdefault(product_id, []).append(item)
            else:
                code = item.get('customer_code') or ''
                oe = item.get('oe_number') or ''
                if code or oe:
                    key = f"{code}|{oe}"
                    fallback_groups.setdefault(key, []).append(item)

        duplicate_pids = {pid for pid, items in pid_groups.items() if len(items) > 1}
        duplicate_fallbacks = {
            key for key, items in fallback_groups.items() if len(items) > 1
        }

        yellow = QBrush(QColor("#fef3c7"))
        red_name = QColor("#fff0f0").name().lower()

        for row in range(self._table.rowCount()):
            item0 = self._table.item(row, 0)
            # 跳过合计行
            if item0 and item0.text() == "📊 合计":
                continue

            if row >= len(self._current_items):
                continue

            item = self._current_items[row]
            product_id = item.get('product_id')
            fallback_key = f"{item.get('customer_code', '')}|{item.get('oe_number', '')}"
            is_duplicate = (
                product_id in duplicate_pids or fallback_key in duplicate_fallbacks
            )

            if not is_duplicate:
                continue

            for col in range(ORDER_DETAIL_COLUMN_COUNT):
                cell = self._table.item(row, col)
                if not cell:
                    continue
                # 不覆盖已存在的红色背景（采购数量不匹配）
                bg_color = cell.background().color().name().lower()
                if bg_color == red_name:
                    continue
                cell.setBackground(yellow)

            if item0:
                item0.setToolTip("该产品在订单中重复出现")

    def _fill_excel_41_columns(self, row, idx, item, order, currency):
        """
        [2026-06-16 需求 46] 按 Excel 41 字段顺序填充表格列

        Excel 列号 → 表格列号:
        0 订单日期          → col 0
        1 ORDER NO.        → col 1
        2 客户产品编号      → col 2
        3 OE号             → col 3
        4 客户需求/产品备注 → col 4
        5 产品名称          → col 5
        6 图片              → col 6
        7 客户型号          → col 7
        8 产品特性          → col 8
        9 数量              → col 9
        10 报价(USD/RMB)    → col 10
        11 合计金额         → col 11
        12 最新客户回复     → col 12
        13 客户预付款       → col 13
        14 待收尾款         → col 14
        15 预估美金报价     → col 15
        16 预估毛利率       → col 16
        17 采购价格         → col 17
        18 运费             → col 18
        19 杂费             → col 19
        20 总金额           → col 20
        21 工厂简称         → col 21
        22 店铺链接         → col 22
        23 交货日期         → col 23
        24 是否已收货       → col 24
        25 工厂订金         → col 25
        26 工厂尾款         → col 26
        27 入库操作         → col 27
        28 入库数量         → col 28
        29 包装方式         → col 29
        30 采购选项/名称    → col 30
        31 产品细节         → col 31
        32 工厂编号         → col 32
        33 纸箱尺寸         → col 33
        34 打包规格         → col 34
        35 箱数             → col 35
        36 预估体积         → col 36
        37 整箱毛重         → col 37
        38 总重量           → col 38
        39 品牌             → col 39
        40 开票情况         → col 40
        """
        from PySide6.QtCore import Qt

        def g(obj, key, default=''):
            v = obj.get(key, default) if obj else default
            return v if v is not None else default

        def num(obj, key, default=0):
            v = obj.get(key, default) if obj else default
            try:
                return float(v) if v not in (None, '') else default
            except (TypeError, ValueError):
                return default

        # ===== 自动计算列本地补算（后端回填优先，缺值时本地算） =====
        # 2026-06-23：补齐 5 个自动计算列（16/20/35/36/38）回填逻辑。
        # 后端 _build_item_detail_v11 已用 snapshot_or_fallback 计算过，但快照可能为
        # None（例如新导入未走 PO 流程的产品），此时前端用同一公式补算。
        import math
        import re

        def _local_carton_count(it):
            """本地补算箱数
            普通模式：ceil(quantity / units_per_carton)
            1件多箱模式：quantity * 每件箱数
            """
            qty = num(it, 'quantity', 0)
            packaging = g(it, 'packaging') or g(it, 'packing_type')

            # 2026-06-26 修复：1件多箱模式，总箱数 = 数量 × 每件箱数
            if packaging == '1件多箱':
                boxes_per_piece = num(it, 'carton_count', 0) or num(it, 'box_count', 0)
                if not boxes_per_piece:
                    pack_spec = (
                        g(it, 'pack_spec')
                        or g(it, 'packing_spec')
                        or g(it, 'pcs_per_carton')
                        or ''
                    )
                    # 解析 "1pcs/48 ctn" -> 48
                    m = re.search(r'(\d+(?:\.\d+)?)\s*ctn', str(pack_spec), re.IGNORECASE)
                    if m:
                        boxes_per_piece = float(m.group(1))
                if qty > 0 and boxes_per_piece > 0:
                    return int(qty * boxes_per_piece)
                return None

            # 普通模式：解析 pack_spec "20 pcs/ctn" -> 每箱 20 件
            upc = num(it, 'units_per_carton', 0)
            if not upc:
                pack_spec = (
                    g(it, 'pack_spec')
                    or g(it, 'packing_spec')
                    or g(it, 'pcs_per_carton')
                    or ''
                )
                m = re.match(r'\s*(\d+(?:\.\d+)?)', str(pack_spec))
                if m:
                    upc = float(m.group(1))
            if qty > 0 and upc > 0:
                return int(math.ceil(qty / upc))
            return None

        def _local_estimated_volume(it, carton_count=None):
            """本地补算预估体积（m³）：carton_count × carton_volume_m3（解析 carton_size 兜底）"""
            if carton_count is None:
                carton_count = _local_carton_count(it)
            if not carton_count:
                return None
            # 优先用现成的体积字段
            vol = num(it, 'carton_volume_m3', 0)
            if vol > 0:
                return round(vol * carton_count, 4)
            # 否则解析 carton_size（"L x W x H cm"）
            cs = g(it, 'carton_size') or g(it, 'box_size')
            if cs:
                m = re.search(
                    r'(\d+(?:\.\d+)?)\s*[xX*×]\s*(\d+(?:\.\d+)?)\s*[xX*×]\s*(\d+(?:\.\d+)?)',
                    str(cs),
                )
                if m:
                    l, w, h = float(m.group(1)), float(m.group(2)), float(m.group(3))
                    return round((l * w * h / 1_000_000) * carton_count, 4)
            return None

        def _local_total_weight(it, carton_count=None):
            """本地补算总重量（kg）：carton_count × carton_gross_weight_kg"""
            if carton_count is None:
                carton_count = _local_carton_count(it)
            if not carton_count:
                return None
            gw = num(it, 'carton_gross_weight', 0) or num(it, 'gross_weight_kg', 0)
            if gw > 0:
                return round(gw * carton_count, 2)
            return None

        def _local_total_order_amount(it):
            """本地补算采购总金额（RMB）：purchase_price × quantity + shipping_fee + misc_fee"""
            pp = num(it, 'purchase_price', 0) or num(it, 'factory_price', 0)
            qty = num(it, 'quantity', 0)
            if pp <= 0 or qty <= 0:
                return None
            ship = num(it, 'shipping_fee', 0)
            misc = num(it, 'misc_fee', 0)
            return round(pp * qty + ship + misc, 2)

        def _local_profit_margin(it, total_order_amount):
            """本地补算预估毛利率（百分比 0-100）：unit_price_usd × exchange_rate / total_order_amount × 100"""
            if not total_order_amount or total_order_amount <= 0:
                return None
            usd = num(it, 'unit_price', 0) or num(it, 'customer_unit_price', 0)
            if usd <= 0:
                return None
            rate = num(it, 'exchange_rate', 6.8) or 6.8
            return round((usd * rate / total_order_amount) * 100, 2)

        def setc(col, value, align=None, color=None, readonly=False):
            it = QTableWidgetItem(str(value) if value is not None else '')
            if align is not None:
                it.setTextAlignment(align)
            if color is not None:
                it.setForeground(QBrush(QColor(color)))
            if readonly:
                it.setForeground(QBrush(QColor(COLORS['readonly_fg'])))
                it.setData(Qt.ItemDataRole.UserRole, 'readonly')
            self._table.setItem(row, col, it)

        # ===== Col 0: 订单日期 =====
        order_date = item.get('order_date') or order.get('order_date', '')
        if order_date:
            order_date = str(order_date)[:10]
        setc(0, order_date, align=Qt.AlignCenter)

        # ===== Col 1: ORDER NO. =====
        setc(1, order.get('pi_no', order.get('order_no', '')))

        # ===== Col 2: 客户产品编号 =====
        product_code = (
            item.get('customer_model')
            or item.get('customer_code')
            or item.get('product_code')
            or item.get('customer_product_code')
            or item.get('customer_product_no')
        )
        if not product_code:
            product_code = '-'
        setc(2, product_code)

        # ===== Col 3: OE号 =====
        setc(3, g(item, 'oe_number') or g(item, 'oe_no'))

        # ===== Col 4: 客户需求/产品备注 =====
        setc(4, g(item, 'customer_remark') or g(item, 'remark'))

        # ===== Col 5: 产品名称 =====
        # 2026-06-23 修复：优先使用 product_name，与产品管理列表保持一致；其次使用 detail_desc
        setc(5, g(item, 'product_name') or g(item, 'detail_desc'))

        # ===== Col 6: 图片(异步加载) =====
        from PySide6.QtWidgets import QLabel
        # 2026-06-23 修复：显示框统一 100×100，与 _load_image_async 内一致，
        # 避免初始 76×76 导致行高先被压到 32 再被撑开（图片挤占其他行的根源）。
        image_label = QLabel()
        image_label.setFixedSize(100, 100)
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setStyleSheet("border: 1px solid #e5e7eb; background-color: #f9fafb;")
        image_url = (item.get('default_image_url') or item.get('image_url') or item.get('image')
                     or item.get('product_image') or item.get('pic_url'))
        if image_url:
            self._load_image_async(image_label, str(image_url), row=row)
        else:
            image_label.setText("暂无图片")
        self._table.setCellWidget(row, 6, image_label)
        # 2026-06-23 修复：行高与图片列列宽统一立刻设置，不等图片异步加载完成。
        # 原因：图片加载是异步的，渲染瞬间 row 高度若不固定，行高会被压回 32，
        #       多张图同时加载时不同步导致行高错乱、图片挤占其他行。
        self._fit_row_height_to_image(row, max_h=100)

        # ===== Col 7: 客户型号 =====
        setc(7, g(item, 'customer_model') or g(item, 'cust_model') or g(item, 'oe_number'))

        # ===== Col 8: 产品特性 =====
        setc(8, g(item, 'product_features') or g(item, 'product_feature'))

        # ===== Col 9: 数量 =====
        setc(9, int(num(item, 'quantity', 0)), align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 10: 报价(USD/RMB) =====
        # 2026-06-23：保留币种后缀显示（采购时通过顶部币种选择切换 USD/RMB）
        # 2026-06-23 修复：PI item 未填报价时，回退到产品默认报价（price_rmb/price_usd）
        quote = num(item, 'unit_price', 0) or num(item, 'customer_unit_price', 0)
        if not quote:
            # Fallback：产品表默认报价
            quote = num(item, 'price_rmb', 0) or num(item, 'price_usd', 0)
        setc(10, self.format_currency_display(quote, currency), align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 11: 合计金额 =====
        # 2026-06-23：与 col 10 一致保留币种后缀
        line_total = num(item, 'total_price', 0) or (num(item, 'unit_price', 0) * num(item, 'quantity', 0))
        setc(11, self.format_currency_display(line_total, currency), align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 12: 最新客户回复 =====
        setc(12, g(order, 'latest_customer_reply') or g(item, 'latest_reply'))

        # ===== Col 13: 客户预付款 =====
        setc(13, f"{num(order, 'prepayment', 0):.2f}", align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 14: 待收尾款 =====
        setc(14, f"{num(order, 'final_payment', 0):.2f}", align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 15: 预估美金报价 =====
        # 2026-06-23：后端字段名 estimated_usd（不是 estimated_usd_price），新增 estimated_usd_price 别名兜底
        est_usd = num(item, 'estimated_usd', 0) or num(item, 'estimated_usd_price', 0)
        setc(15, f"{est_usd:.2f}" if est_usd else '-', align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 16: 预估毛利率 =====
        # 2026-06-23：后端字段名 profit_margin (0-100 百分比)，原代码读 estimated_margin (0-1) 单位错配导致显示成 2500% 之类。
        # 回填策略：后端预计算值 → 缺值时本地用 Col20 金额补算
        profit_margin = num(item, 'profit_margin', 0)  # 后端预计算 (百分比)
        if not profit_margin:
            total_order_for_margin = num(item, 'total_order_amount', 0) or _local_total_order_amount(item)
            profit_margin = _local_profit_margin(item, total_order_for_margin) or 0
        if profit_margin:
            # 颜色阈值 20%：≥20% 绿色，<20% 不上色（与 Excel 模板一致）
            margin_color = '#059669' if profit_margin >= 20 else None
            setc(16, f"{profit_margin:.1f}%", align=Qt.AlignRight | Qt.AlignVCenter, color=margin_color)
        else:
            setc(16, '-', align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 17: 采购价格 =====
        purchase_price = num(item, 'purchase_price', 0) or num(item, 'factory_price', 0)
        setc(17, f"{purchase_price:.2f}" if purchase_price else '-', align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 18: 运费 =====
        shipping = num(item, 'shipping_fee', 0) or num(order, 'shipping_fee', 0)
        setc(18, f"{shipping:.2f}" if shipping else '-', align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 19: 杂费 =====
        misc = num(item, 'misc_fee', 0) or num(order, 'misc_fee', 0)
        setc(19, f"{misc:.2f}" if misc else '-', align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 20: 总金额 =====
        # 2026-06-23：原代码用 purchase_qty 字段（item 中不存在）回退到 quantity，忽略后端预计算 total_order_amount。
        # 回填策略：后端 total_order_amount → 缺值时本地用 purchase_price × quantity + shipping + misc 计算
        cost_total = num(item, 'total_order_amount', 0) or _local_total_order_amount(item) or 0
        setc(20, f"{cost_total:.2f}" if cost_total else '-', align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 21: 工厂简称 =====
        setc(21, g(item, 'factory_short_name') or g(item, 'supplier_short_name') or g(item, 'supplier_name'))

        # ===== Col 22: 店铺链接 =====
        setc(22, g(item, 'supplier_url') or g(item, 'shop_url') or g(item, 'url'))

        # ===== Col 23: 交货日期 =====
        delivery_date = g(item, 'delivery_date') or g(order, 'delivery_date')
        if delivery_date:
            delivery_date = str(delivery_date)[:10]
        setc(23, delivery_date, align=Qt.AlignCenter)

        # ===== Col 24: 是否已收货 =====
        received = item.get('is_received') or order.get('is_received')
        if received in (True, 'true', '是', '已收货', 1, '1'):
            setc(24, '√ 已收货', align=Qt.AlignCenter, color='#059669')
        else:
            setc(24, '× 未收货', align=Qt.AlignCenter, color='#9ca3af')

        # ===== Col 25: 工厂订金 =====
        setc(25, f"{num(item, 'factory_deposit', 0):.2f}", align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 26: 工厂尾款 =====
        setc(26, f"{num(item, 'factory_balance', 0):.2f}", align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 27: 入库操作 =====
        # 2026-06-23 收敛：3 分支对应 storage_status 三值（已入库/部分入库/未入库）。
        # 后端已统一为单一字段 storage_status（见 crud.storage_status.StorageStatus），
        # 不要再回退读 warehouse_action（已删除）。
        # 2026-06-23 新增：支持订单级「缺货」标记显示（黄色锁）
        storage = g(item, 'storage_status') or g(order, 'storage_status')
        if storage == '缺货':
            setc(27, '🔒 缺货', align=Qt.AlignCenter, color='#D97706')
        elif storage == '已入库':
            setc(27, '√ 已入库', align=Qt.AlignCenter, color='#059669')
        elif storage == '部分入库':
            setc(27, '◐ 部分入库', align=Qt.AlignCenter, color='#d97706')
        else:
            setc(27, '× 未入库', align=Qt.AlignCenter, color='#9ca3af')

        # ===== Col 28: 入库数量 =====
        # 2026-06-23 收敛：后端只暴露 stocked_qty（DB 字段），删除 warehouse_qty 别名。
        in_qty = num(item, 'stocked_qty', 0) or num(item, 'inbound_qty', 0)
        setc(28, int(in_qty) if in_qty else '', align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 29: 包装方式 =====
        # 🔍 2026-06-22 诊断埋点：追踪item实际包含的字段
        packaging_value = g(item, 'packaging') or g(item, 'packing_method') or g(item, 'package_method')
        if not hasattr(self, '_diag_printed'):
            self._diag_printed = set()
        if row not in self._diag_printed:
            self._diag_printed.add(row)
            print(f"[DIAG-DetailPanel] row={row} Col29包装方式 渲染值: {packaging_value!r}")
            print(f"[DIAG-DetailPanel]   item所有key: {list(item.keys()) if isinstance(item, dict) else 'NOT_DICT'}")
            # 关键字段
            for k in ['packaging', 'packing_method', 'package_method', 'purchase_option_name', '1688_title', 'purchase_name', 'pack_spec']:
                v = item.get(k) if isinstance(item, dict) else None
                print(f"[DIAG-DetailPanel]   item.get({k!r}) = {v!r}")
        setc(29, packaging_value)

        # ===== Col 30: 采购选项/名称 =====
        purchase_value = g(item, 'purchase_option_name') or g(item, '1688_title') or g(item, 'purchase_name')
        if row not in self._diag_printed or True:  # 每次都打印
            print(f"[DIAG-DetailPanel] row={row} Col30采购选项 渲染值: {purchase_value!r}")
        setc(30, purchase_value)

        # ===== Col 31: 产品细节 =====
        setc(31, g(item, 'product_details') or g(item, 'product_spec'))

        # ===== Col 32: 工厂编号 =====
        setc(32, g(item, 'factory_code') or g(item, 'factory_sku') or g(item, 'factory_model'))

        # ===== Col 33: 纸箱尺寸 =====
        setc(33, g(item, 'carton_size') or g(item, 'box_size'))

        # ===== Col 34: 打包规格 =====
        # 2026-06-23 修复：后端 _build_item_detail_v11 返回字段名是 packing_spec，
        # 不是 pack_spec；兼容两种 key
        setc(34, g(item, 'pack_spec') or g(item, 'packing_spec') or g(item, 'pcs_per_carton'))

        # ===== Col 35: 箱数 =====
        # 2026-06-23：补齐本地补算（quantity + units_per_carton），保证新导入未走 PO 流程的产品也能算出来
        carton_count = num(item, 'carton_count', 0) or num(item, 'box_count', 0) or _local_carton_count(item) or 0
        setc(35, int(carton_count) if carton_count else '', align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 36: 预估体积 =====
        # 2026-06-23：补齐本地补算（carton_count × carton_volume_m3；或解析 carton_size）
        est_vol = num(item, 'estimated_volume', 0) or _local_estimated_volume(item, carton_count) or 0
        setc(36, f"{est_vol:.4f} m3" if est_vol else '-', align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 37: 整箱毛重 =====
        carton_gw = num(item, 'carton_gross_weight', 0) or num(item, 'box_gw', 0) or num(item, 'gross_weight_kg', 0)
        setc(37, f"{carton_gw:.2f} kg" if carton_gw else '-', align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 38: 总重量 =====
        # 2026-06-23：补齐本地补算（carton_count × carton_gross_weight_kg）
        total_w = num(item, 'total_weight', 0) or _local_total_weight(item, carton_count) or num(order, 'total_weight', 0)
        setc(38, f"{total_w:.2f} kg" if total_w else '-', align=Qt.AlignRight | Qt.AlignVCenter)

        # ===== Col 39: 品牌 =====
        setc(39, g(item, 'brand') or g(item, 'product_brand'))

        # ===== Col 40: 开票情况 =====
        invoice = g(item, 'invoice_type') or g(item, 'invoice_status') or g(order, 'invoice_type')
        if invoice in ('已上传', '已开', '已开票', '增票', '普票'):
            setc(40, invoice, color=COLORS['invoice_paid'])
        elif invoice and invoice != '-':
            setc(40, invoice, color=COLORS['invoice_unpaid'])
        else:
            setc(40, invoice or '未上传', color=COLORS['muted'])

    def _on_checkbox_changed(self, row, state):
        """复选框状态改变"""
        from PySide6.QtCore import Qt
        if state == Qt.CheckState.Checked:
            self._selected_items.add(row)
            self._current_row = row
        else:
            self._selected_items.discard(row)
            # 取消勾选后，若无任何选中项 → 灯全灭
            if not self._selected_items:
                self._set_status_dots_gray()
                return

        # 更新状态灯（根据选中状态）
        self._update_status_indicator(self._current_items)
    
    def _update_status_indicator(self, items):
        """更新状态灯 - 基于当前选中行的单品状态（与 main.py 逻辑一致）"""
        if not items:
            self._set_status_dots_gray()
            return

        # 优先使用复选框选中的行，否则用当前点击行
        # 2026-06-12：未点击/未勾选任何行时，所有指示灯应熄灭，不再 fallback 到第 0 行
        if self._selected_items:
            row = next(iter(self._selected_items))
        elif self._current_row >= 0:
            row = self._current_row
        else:
            self._set_status_dots_gray()
            return

        if row < 0 or row >= len(items):
            self._set_status_dots_gray()
            return

        item = items[row]

        # 灯1: 产品类型（均为正式产品）
        color1 = '#22c55e'
        text1 = '正式'

        # 灯2: 采购状态（已采=蓝色，未采=灰色）
        # 判断依据：有采购价格 或 有采购单项ID 或 有供应商名称
        purchase_price = item.get('purchase_price')
        po_item_id = item.get('po_item_id')
        supplier_name = item.get('supplier_name')
        is_purchased = (
            (purchase_price is not None and float(purchase_price) > 0)
            or (po_item_id is not None and po_item_id != '')
            or (supplier_name is not None and supplier_name != '')
        )
        color2 = '#3b82f6' if is_purchased else '#6b7280'
        text2 = '已采' if is_purchased else '未采'

        # 灯3: 入库状态（缺货=橙色，已入库=绿色，部分入库=黄色，未入库=灰色）
        order_storage = (self._current_order or {}).get('storage_status', '')
        item_storage = item.get('storage_status', '')
        stocked_qty = item.get('stocked_qty', 0) or 0
        quantity = item.get('quantity', 0) or 0
        try:
            stocked_qty_f = float(stocked_qty)
        except (TypeError, ValueError):
            stocked_qty_f = 0
        try:
            quantity_f = float(quantity)
        except (TypeError, ValueError):
            quantity_f = 0

        if order_storage == '缺货':
            color3, text3 = '#D97706', '缺货'
        elif item_storage == '已入库' or (quantity_f > 0 and stocked_qty_f >= quantity_f):
            color3, text3 = '#22c55e', '已入库'
        elif item_storage == '部分入库' or (stocked_qty_f > 0 and stocked_qty_f < quantity_f):
            color3, text3 = '#f59e0b', '部分入库'
        else:
            color3, text3 = '#6b7280', '未入库'

        # 灯4: 发票状态（有票=绿色，无票=灰色）
        invoice_status = item.get('invoice_status', '')
        has_invoice = invoice_status in ['已上传', '已开']
        color4 = '#22c55e' if has_invoice else '#6b7280'
        text4 = '有票' if has_invoice else '无票'

        colors = [color1, color2, color3, color4]
        texts = [text1, text2, text3, text4]

        for i, (color, text) in enumerate(zip(colors, texts)):
            self._status_dots[i].setStyleSheet(f"background-color: {color}; border-radius: 6px;")
            self._status_labels[i].setText(text)
            self._status_labels[i].setStyleSheet(f"color: {color}; font-size: 12px;")

    def _set_status_dots_gray(self):
        gray = COLORS['readonly_fg']
        default_texts = ["正式", "未采", "未入库", "无票"]
        for i, dot in enumerate(self._status_dots):
            dot.setStyleSheet(f"background-color: {gray}; border-radius: 6px;")
        for i, label in enumerate(self._status_labels):
            label.setText(default_texts[i] if i < len(default_texts) else "")
            label.setStyleSheet(f"color: {gray}; font-size: 12px;")

    # ============== 2026-06-14：单品删除状态协调 ==============

    def remove_item(self, item_id: int) -> bool:
        """删除指定 item_id 的行，同步 _current_items / _checkboxes / _selected_items / _current_row / 状态灯

        Returns:
            True 表示删除成功，False 表示未找到
        """
        if self._table is None or not self._current_items:
            return False

        # 1. 定位行号
        row = next(
            (i for i, it in enumerate(self._current_items) if it.get("id") == item_id),
            -1,
        )
        if row < 0:
            return False

        # 2. 移除数据
        self._current_items.pop(row)

        # 3. 释放被删行的复选框 widget，然后删 _checkboxes[row]
        if 0 <= row < len(self._checkboxes):
            old_chk = self._checkboxes[row]
            old_chk.setParent(None)
            old_chk.deleteLater()
            del self._checkboxes[row]

        # 4. 删除表格行
        self._table.removeRow(row)

        # 5. 修正选中集合：行号 > row 的 -1
        # 仅当 row 原本在选中集合中时，才把"原 row"项从新集合里清掉
        # 否则会误伤"原 row+1 -1 = 新 row"这个合理的新选中
        had_row = row in self._selected_items
        self._selected_items = {s - 1 if s > row else s for s in self._selected_items}
        if had_row:
            self._selected_items.discard(row)

        # 6. 修正当前行
        if self._current_row == row:
            self._current_row = -1
        elif self._current_row > row:
            self._current_row -= 1

        # 7. 状态灯
        if self._current_row >= 0 and self._current_items:
            self._update_status_indicator(self._current_items)
        else:
            self._set_status_dots_gray()

        return True

    def _on_item_removed(self, order_id: int, item_id: int):
        """服务信号回调 - 仅处理当前显示订单的删除事件"""
        if not self._current_order:
            return
        if self._current_order.get("id") != order_id:
            return
        self.remove_item(item_id)

    def _on_detail_table_clicked(self, row, col):
        """详情表点击事件 - 更新当前行和状态灯"""
        if row < 0 or (self._current_items and row >= len(self._current_items)):
            self._current_row = -1
            self._set_status_dots_gray()
            return
        self._current_row = row
        self._update_status_indicator(self._current_items)
    
    @staticmethod
    def format_currency_display(amount, currency='USD'):
        """格式化金额显示 - 统一格式 {X.XX} {CUR}"""
        if amount is None:
            return f"0.00 {currency}"
        try:
            return f"{float(amount):.2f} {currency}"
        except (ValueError, TypeError):
            return f"0.00 {currency}"
    
    def get_current_order(self) -> dict:
        """获取当前订单"""
        return self._current_order
    
    def get_current_items(self) -> list:
        """获取当前产品列表"""
        return self._current_items
    
    def get_selected_items(self) -> set:
        """获取用户勾选的产品行索引集合（直接读取复选框实际状态）"""
        from PySide6.QtCore import Qt
        selected = set()
        for i, chkbox in enumerate(getattr(self, '_checkboxes', [])):
            if chkbox and chkbox.checkState() == Qt.CheckState.Checked:
                selected.add(i)
        # 如果通过复选框读到了选中项，优先使用；否则 fallback 到 _selected_items
        return selected if selected else getattr(self, '_selected_items', set())
    
    def get_item_at_row(self, row: int) -> dict:
        """获取指定行的产品数据"""
        if row < 0 or row >= len(self._current_items):
            return {}
        return self._current_items[row]
    
    def _normalize_image_url(self, image_url: str) -> str:
        """把后端返回的相对路径（/images/xxx）补全为绝对 URL"""
        if not image_url:
            return image_url
        if image_url.startswith(("http://", "https://")):
            return image_url
        base = (Config.API_BASE_URL or "").rstrip("/")
        result = f"{base}{image_url}" if image_url.startswith("/") else f"{base}/{image_url}"
        return result

    def _load_image_async(self, label, image_url, row=None):
        """异步加载图片，加载完成后根据原图宽高比自适应行高和图片列列宽

        参数：
            label: 图片显示的 QLabel
            image_url: 图片 URL
            row: 行号（用于调整该行的行高）
        """
        # 规范化 URL：相对路径 → 绝对 URL
        image_url = self._normalize_image_url(image_url)
        if not image_url:
            label.setText("暂无图片")
            return

        # 先检查内存缓存
        with self._image_cache_lock:
            if image_url in self._image_cache:
                pixmap = self._image_cache[image_url]
                label.setPixmap(pixmap)
                # 2026-06-23 修复：之前传 pixmap 对象导致 "QPixmap + int" TypeError
                # 这里 max_h 取 QPixmap 的实际高度，匹配 on_done 分支传入 100 的语义
                self._fit_row_height_to_image(row, pixmap.height() if not pixmap.isNull() else 100)
                return

        # 显示加载中占位符
        label.setText("...")

        def fetch_image():
            try:
                image_data = urllib.request.urlopen(image_url, timeout=3).read()
                return image_data
            except Exception as e:
                print(f"图片加载失败: {e}")
                return None

        def on_done(future):
            try:
                from shiboken6 import isValid
                if not label or not isValid(label):
                    return
            except ImportError:
                pass

            image_data = future.result()
            if image_data:
                try:
                    image = QImage.fromData(image_data)
                    if image.isNull():
                        raise ValueError("图片解码失败")

                    # 行高匹配图片高度：
                    # - 显示框固定 max_w × max_h
                    # - 图片等比缩放填入显示框
                    # - 行高 = max(ORDER_DETAIL_ROW_HEIGHT, 实际显示高度 + 上下内边距)
                    orig_w = image.width()
                    orig_h = image.height()

                    # 显示框尺寸：固定上限，避免列宽无限扩张
                    max_w = 100   # 显示框最大宽
                    max_h = 100   # 显示框最大高
                    min_h = ORDER_DETAIL_ROW_HEIGHT  # 32

                    if orig_w <= 0 or orig_h <= 0:
                        target_w, target_h = max_w, min_h
                    else:
                        # 等比缩放：图片按比例填入显示框
                        scale = min(max_w / orig_w, max_h / orig_h)
                        target_w = max(1, int(orig_w * scale))
                        target_h = max(1, int(orig_h * scale))
                        # 保底：至少 24px 宽
                        if target_w < 24:
                            target_w = 24
                        if target_h < 24:
                            target_h = 24

                    pixmap = QPixmap.fromImage(image).scaled(
                        target_w, target_h,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )

                    # 存入内存缓存
                    with self._image_cache_lock:
                        if len(self._image_cache) >= 50:
                            oldest_key = next(iter(self._image_cache))
                            del self._image_cache[oldest_key]
                        self._image_cache[image_url] = pixmap

                    label.setFixedSize(max_w, max_h)  # 显示框固定
                    # 用 Alignment 让小图居中显示在大框内
                    label.setAlignment(Qt.AlignCenter)
                    label.setPixmap(pixmap)
                    self._fit_row_height_to_image(row, max_h)
                    return
                except Exception as e:
                    print(f"图片处理失败: {e}")
            try:
                label.setText("暂无图片")
            except RuntimeError:
                pass

        self._thread_pool.submit(fetch_image).add_done_callback(on_done)

    def _fit_row_height_to_image(self, row, max_h: int = 100):
        """调整指定行的行高和图片列列宽。

        关键策略（2026-06-16 修复）：
        - 行高 = max(ORDER_DETAIL_ROW_HEIGHT, max_h + 上下内边距 8px)
          即所有行的行高统一 = max(ORDER_DETAIL_ROW_HEIGHT, max_h + 8)，避免图片大小不一导致行高错乱
        - 图片列列宽 = 显示框宽度 + 内边距（固定），不再累加扩张

        参数：
            row: 行号
            max_h: 显示框最大高度（默认 100），实际行高 = max(32, max_h + 8) = 108
        """
        if row is None or row < 0 or row >= self._table.rowCount():
            return

        # 行高：固定 = max(ORDER_DETAIL_ROW_HEIGHT, max_h + 8)
        target_row_h = max(ORDER_DETAIL_ROW_HEIGHT, max_h + 8)
        self._table.setRowHeight(row, target_row_h)

        # 图片列列宽：固定为 100 + 8 = 108，不再基于 current_col_w 累加
        # 防止多次调用导致列宽无限扩大
        target_col_w = 108  # 显示框 100 + 左右内边距 8
        self._table.setColumnWidth(6, target_col_w)

    # 2026-06-11 任务 4：右键菜单
    def _is_item_purchased(self, item: dict) -> bool:
        """判断产品是否已采购（基于 supplier_name 是否存在）"""
        if not item:
            return False
        return bool(item.get('supplier_name'))

    def _check_formal_record_async(self, pi_id):
        """2026-06-23：异步检查订单是否有正式PI（"保存正式记录" 后才置为 True）

        用同步请求快速拿到结果（fastapi 本地毫秒级），完成后更新 _has_formal_record。
        若订单切换、组件销毁前完成，early-return 不更新。
        """
        if not pi_id:
            return
        # 保存当时的 pi_id，避免异步回调污染其他订单
        captured_pi_id = pi_id

        def _on_success(resp):
            # 订单可能已切换
            if not self._current_order or self._current_order.get('id') != captured_pi_id:
                return
            # 兼容两种返回类型：dict（后端原始响应）或 bool（API 客户端已解包）
            if isinstance(resp, dict):
                self._has_formal_record = bool(resp.get('exists'))
            else:
                self._has_formal_record = bool(resp)
            # 同步更新顶部"采购全部"按钮（采购时与右键菜单共用同一份权限）
            if hasattr(self, '_purchase_btn'):
                self._purchase_btn.setEnabled(self._has_formal_record)
                if self._has_formal_record:
                    self._purchase_btn.setToolTip("")
                else:
                    self._purchase_btn.setToolTip("请先点击『保存正式记录』锁定PI后再采购")
            # 2026-06-23：同步更新"保存正式纪录"按钮（已保存过则禁用，防止重复覆盖）
            if hasattr(self, '_formal_btn'):
                can_save = not self._has_formal_record
                self._formal_btn.setEnabled(can_save)
                if self._has_formal_record:
                    self._formal_btn.setToolTip("已保存正式纪录，PI 已锁定")
                else:
                    self._formal_btn.setToolTip("请先点击此按钮保存正式纪录，锁定PI后再进行采购/入库操作")
            # 2026-06-26：正式PI 状态提示
            if hasattr(self, '_formal_hint_label'):
                if self._has_formal_record:
                    self._formal_hint_label.setText("✅ 已保存正式PI")
                    self._formal_hint_label.setStyleSheet("""
                        QLabel {
                            color: #059669;
                            background-color: #ecfdf5;
                            border: 1px solid #a7f3d0;
                            border-radius: 4px;
                            padding: 4px 10px;
                            font-size: 12px;
                            font-weight: bold;
                        }
                    """)
                else:
                    self._formal_hint_label.setText("⚠ 未保存正式PI")
                    self._formal_hint_label.setStyleSheet("""
                        QLabel {
                            color: #dc2626;
                            background-color: #fef2f2;
                            border: 1px solid #fecaca;
                            border-radius: 4px;
                            padding: 4px 10px;
                            font-size: 12px;
                            font-weight: bold;
                        }
                    """)
                self._formal_hint_label.setVisible(True)
            # 通知外部 tab 刷新"全部入库"按钮状态
            if hasattr(self, 'formalRecordChecked'):
                try:
                    self.formalRecordChecked.emit(self._has_formal_record)
                except RuntimeError:
                    pass

        def _on_error(exc):
            print(f"[OrderDetailPanel] 检查正式PI失败: {exc}")
            # 失败默认不开权限（保守）
            self._has_formal_record = False

        # 优先用异步，没有就降级同步
        async_check = getattr(self.api_client, 'formal_record_exists_async', None)
        if callable(async_check):
            try:
                async_check(pi_id, on_success=_on_success, on_error=_on_error)
            except Exception as e:
                _on_error(e)
        else:
            try:
                resp = self.api_client.formal_record_exists(pi_id)
                _on_success(resp)
            except Exception as e:
                _on_error(e)

    def _on_save_formal_record(self):
        """2026-06-23：点击"保存正式纪录"按钮 → 调用 API → 保存后锁定按钮 + 启用采购/入库"""
        pi_id = self._current_order.get('id') if self._current_order else None
        if not pi_id:
            return
        from PySide6.QtWidgets import QMessageBox
        pi_no = self._current_order.get('pi_no', '') or ''
        reply = QMessageBox.question(
            self, "确认保存",
            f"确定将当前状态固化为正式纪录？\nPI 编号：{pi_no}\n注意：正式纪录保存后将锁定该 PI，不可再修改。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        # 保存中禁用按钮防重复点击
        if hasattr(self, '_formal_btn'):
            self._formal_btn.setEnabled(False)
            self._formal_btn.setText("保存中...")
        try:
            result = self.api_client.save_formal_record(pi_id)
            # 保存成功后乐观更新状态
            self._has_formal_record = True
            # 立即启用采购/入库按钮（无需等待下次 API 检查）
            if hasattr(self, '_purchase_btn'):
                self._purchase_btn.setEnabled(True)
                self._purchase_btn.setToolTip("")
            if hasattr(self, '_formal_btn'):
                self._formal_btn.setText("📌 已锁定")
                self._formal_btn.setEnabled(False)
                self._formal_btn.setToolTip("已保存正式纪录，PI 已锁定")
            # 2026-06-26: 切换为"已保存正式PI"提示
            if hasattr(self, '_formal_hint_label'):
                self._formal_hint_label.setText("✅ 已保存正式PI")
                self._formal_hint_label.setStyleSheet("""
                    QLabel {
                        color: #059669;
                        background-color: #ecfdf5;
                        border: 1px solid #a7f3d0;
                        border-radius: 4px;
                        padding: 4px 10px;
                        font-size: 12px;
                        font-weight: bold;
                    }
                """)
                self._formal_hint_label.setVisible(True)
            # 通知外部 tab 刷新"全部入库"按钮
            if hasattr(self, 'formalRecordChecked'):
                try:
                    self.formalRecordChecked.emit(True)
                except RuntimeError:
                    pass
            if hasattr(self, 'formalRecordSaved'):
                self.formalRecordSaved.emit()
            QMessageBox.information(
                self, "成功",
                f"正式纪录已保存\nPI 已锁定，可进行采购/入库操作\n{result.get('file_path', '')}"
            )
        except Exception as e:
            # 保存失败恢复按钮状态
            if hasattr(self, '_formal_btn'):
                self._formal_btn.setEnabled(True)
                self._formal_btn.setText("📌 保存正式纪录")
                self._formal_btn.setToolTip("保存失败，请重试")
            QMessageBox.warning(self, "错误", f"保存失败: {e}")

    def _show_column_filter_menu(self):
        """显示列筛选菜单"""
        menu = QMenu(self._col_filter_btn)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #d1d5db;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
            }
            QMenu::item:selected {
                background-color: #f3f4f6;
            }
        """)

        # 创建所有列的复选框
        for col in range(self._table.columnCount()):
            header_text = self._table.horizontalHeaderItem(col).text() if self._table.horizontalHeaderItem(col) else f"列{col}"
            action = menu.addAction(header_text)
            action.setCheckable(True)
            action.setChecked(not self._table.isColumnHidden(col))
            action.triggered.connect(
                lambda checked, c=col: self._toggle_column(c, checked)
            )

        # 显示菜单在按钮下方
        menu.exec(self._col_filter_btn.mapToGlobal(self._col_filter_btn.rect().bottomLeft()))

    def _toggle_column(self, col: int, visible: bool):
        """切换列的显示/隐藏"""
        self._table.setColumnHidden(col, not visible)

    def _on_context_menu(self, pos):
        """右键菜单触发"""
        row = self._table.rowAt(pos.y())
        if row < 0 or row >= len(self._current_items):
            return
        menu = self._build_context_menu(row)
        if menu is None:
            return
        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _build_context_menu(self, row: int):
        """根据行状态构建右键菜单

        2026-06-23：采购/入库必须先有正式PI（"保存正式记录" 后才允许操作）
        否则菜单项灰化 + tooltip 提示原因。
        """
        item = self.get_item_at_row(row)
        if not item:
            return None
        is_purchased = self._is_item_purchased(item)
        # 2026-06-23：未保存正式PI 时禁止采购/入库（订单总表是动态报价，不适合留档）
        has_formal = self._has_formal_record
        no_formal_hint = "请先点击『保存正式记录』锁定PI后再采购/入库"

        menu = QMenu(self)
        purchase_single = menu.addAction("采购该产品")
        purchase_single.setEnabled(has_formal and not is_purchased)
        if not has_formal:
            purchase_single.setToolTip(no_formal_hint)
        purchase_single.triggered.connect(
            lambda: self.purchaseSingleRequested.emit(row)
        )

        purchase_repurchase = menu.addAction("重新采购")
        purchase_repurchase.setEnabled(has_formal and is_purchased)
        if not has_formal:
            purchase_repurchase.setToolTip(no_formal_hint)
        purchase_repurchase.triggered.connect(
            lambda: self.purchaseRepurchaseRequested.emit(row)
        )

        # 2026-06-12 需求#40：入库 / 删除菜单项
        # 2026-06-23：已入库的产品不再重复入库，增加库存状态判断
        is_stored = item.get('storage_status') == '已入库'
        # 检查库存记录状态（如果 API 返回了 inv_stock_type）
        inv_stock_type = item.get('inv_stock_type') or item.get('stock_type')
        is_inv_stocked = inv_stock_type == 3  # 3=已入库(绿)

        menu.addSeparator()
        stock_in = menu.addAction("入库该产品")
        can_inbound = has_formal and not is_stored and not is_inv_stocked
        stock_in.setEnabled(can_inbound)
        if not has_formal:
            stock_in.setToolTip(no_formal_hint)
        elif is_stored:
            stock_in.setToolTip("该产品已入库，无需重复操作")
        elif is_inv_stocked:
            stock_in.setToolTip("该产品库存状态为已入库")
        else:
            stock_in.setToolTip("执行入库操作")
        stock_in.triggered.connect(lambda: self.stockInSingleRequested.emit(row))

        delete_action = menu.addAction("删除商品")
        delete_action.setEnabled(True)
        delete_action.triggered.connect(lambda: self.deleteItemRequested.emit(row))

        # 2026-07-02 新增：编辑产品 / 更换供应商 / 采购快照 / 访问店铺网站
        menu.addSeparator()
        edit_action = menu.addAction("编辑产品")
        edit_action.triggered.connect(lambda: self.editProductRequested.emit(row, -1))

        change_supplier_action = menu.addAction("更换供应商")
        has_po = self._is_item_purchased(item)
        change_supplier_action.setEnabled(has_po)
        change_supplier_action.setToolTip("尚未生成采购单" if not has_po else "更换供应商将重新生成采购单")
        change_supplier_action.triggered.connect(lambda: self.changeSupplierRequested.emit(row))

        snapshot_action = menu.addAction("采购快照")
        snapshot_action.triggered.connect(lambda: self.purchaseSnapshotRequested.emit(row))

        open_url_action = menu.addAction("访问店铺网站")
        shop_url = item.get("shop_url", "")
        open_url_action.setEnabled(bool(shop_url))
        open_url_action.triggered.connect(lambda: self.openShopUrlRequested.emit(row))

        # 2026-06-23 新增：订单级缺货标记
        menu.addSeparator()
        order_storage = (self._current_order or {}).get('storage_status', '')
        if order_storage == '缺货':
            shortage_action = menu.addAction("🔓 取消订单缺货标记")
            shortage_action.triggered.connect(lambda: self._toggle_order_shortage(False))
        else:
            shortage_action = menu.addAction("🔒 标记订单缺货")
            shortage_action.triggered.connect(lambda: self._toggle_order_shortage(True))

        return menu

    def _toggle_order_shortage(self, mark_as_shortage: bool):
        """切换当前订单的缺货标记状态"""
        order = self._current_order
        if not order:
            return
        pi_id = order.get('id')
        if not pi_id:
            return

        try:
            new_status = "缺货" if mark_as_shortage else None
            result = self.api_client.update_pi_storage_status(pi_id, new_status)
            if result and result.get('success'):
                order['storage_status'] = result.get('storage_status')
                # 刷新当前详情表格，让 Col 27 和行背景色立即更新
                self.show_order_detail(order, self._current_items)
                QMessageBox.information(
                    self, "成功",
                    f"订单缺货标记已{'设置' if mark_as_shortage else '取消'}"
                )
        except Exception as e:
            print(f"[ERROR] 订单缺货标记失败: {e}")
            QMessageBox.warning(self, "操作失败", f"更新缺货状态失败：{e}")