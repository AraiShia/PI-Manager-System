# -*- coding: utf-8 -*-
"""
ShipmentTab — 出货管理 Tab (双模式: 列表 / 详情)

历史: 2026-06-05 计划双模式重写
状态: ✅ 已实现 - 列表模式 + 详情模式

模式:
    - "list"  : 出货单列表
    - "detail": 选中出货单后展示 19 列出货明细
"""

import logging
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QLineEdit,
    QSplitter, QFrame
)
from PySide6.QtGui import QColor

logger = logging.getLogger(__name__)


# 19 列出货明细表头
SHIPMENT_DETAIL_COLUMNS = [
    "序号", "客户编号", "OE号", "图片", "订单数量", "单价", "金额",
    "总箱数", "总体积", "总重量",
    "出货数量", "出货单价", "出货金额",
    "出货箱数", "出货体积", "出货重量",
    "剩余数量", "剩余箱数", "剩余体积"
]

# 状态映射
STATUS_MAP = {
    1: "待出货",
    2: "出货中",
    3: "已出货",
    4: "已到达",
}

STATUS_COLOR = {
    1: "#f59e0b",  # 橙色 - 待出货
    2: "#3b82f6",  # 蓝色 - 出货中
    3: "#10b981",  # 绿色 - 已出货
    4: "#6b7280",  # 灰色 - 已到达
}


class ShipmentTab(QWidget):
    """出货管理 Tab - 双模式设计 (列表 / 详情)"""

    mode_changed = Signal(str)

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self._mode = "list"
        self._shipments = []
        self._current_shipment = None

        # 主布局
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # 初始化列表模式
        self._init_list_mode()

    def _init_list_mode(self):
        """初始化列表模式 UI"""
        # 清除旧内容
        self._clear_layout(self._main_layout)

        # 顶部工具栏
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(12, 12, 12, 12)

        title = QLabel("出货管理 — 列表")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1f2937;")
        toolbar.addWidget(title)
        toolbar.addStretch()

        # 状态筛选
        toolbar.addWidget(QLabel("状态:"))
        self.status_filter = QComboBox()
        self.status_filter.addItem("全部", None)
        self.status_filter.addItem("待出货", 1)
        self.status_filter.addItem("出货中", 2)
        self.status_filter.addItem("已出货", 3)
        self.status_filter.addItem("已到达", 4)
        self.status_filter.currentIndexChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self.status_filter)

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索出货单号/CI号/PI号...")
        self.search_input.setMaximumWidth(250)
        self.search_input.textChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self.search_input)

        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(self.refresh_btn)

        self._main_layout.addLayout(toolbar)

        # 表格
        self.list_table = QTableWidget()
        self.list_table.setColumnCount(11)
        self.list_table.setHorizontalHeaderLabels([
            "ID", "出货单号", "CI号", "报关单", "PI号",
            "总金额", "总箱数", "状态", "创建日期", "操作", ""
        ])
        self.list_table.setColumnHidden(0, True)  # 隐藏 ID 列

        # 列宽可拖动
        header = self.list_table.horizontalHeader()
        for i in range(1, 10):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
        header.setSectionResizeMode(9, QHeaderView.Fixed)
        header.resizeSection(9, 120)

        self.list_table.verticalHeader().setDefaultSectionSize(32)
        self.list_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.list_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.list_table.cellDoubleClicked.connect(self._on_row_double_clicked)

        self._main_layout.addWidget(self.list_table)

    def _init_detail_mode(self):
        """初始化详情模式 UI"""
        self._clear_layout(self._main_layout)

        # 顶部工具栏
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(12, 12, 12, 12)

        self.back_btn = QPushButton("← 返回出货单列表")
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                padding: 6px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        self.back_btn.clicked.connect(lambda: self.set_mode("list"))
        toolbar.addWidget(self.back_btn)

        toolbar.addStretch()

        # 操作按钮
        self.export_pl_btn = QPushButton("📋 导出PL")
        self.export_pl_btn.clicked.connect(self._on_export_pl)
        toolbar.addWidget(self.export_pl_btn)

        self.export_ci_btn = QPushButton("📄 导出CI")
        self.export_ci_btn.clicked.connect(self._on_export_ci)
        toolbar.addWidget(self.export_ci_btn)

        self._main_layout.addLayout(toolbar)

        # 标题区
        title_frame = QFrame()
        title_frame.setStyleSheet("""
            QFrame {
                background-color: #f3f4f6;
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                padding: 12px;
            }
        """)
        title_layout = QVBoxLayout(title_frame)
        title_layout.setContentsMargins(16, 12, 16, 12)

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1f2937;")
        title_layout.addWidget(self.title_label)

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-size: 13px; color: #4b5563; margin-top: 6px;")
        title_layout.addWidget(self.summary_label)

        self._main_layout.addWidget(title_frame)

        # 19 列出货明细表格
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(19)
        self.detail_table.setHorizontalHeaderLabels(SHIPMENT_DETAIL_COLUMNS)

        # 列宽可拖动
        header = self.detail_table.horizontalHeader()
        for i in range(19):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 50)

        self.detail_table.verticalHeader().setDefaultSectionSize(40)
        self.detail_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.detail_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self._main_layout.addWidget(self.detail_table)

    def _clear_layout(self, layout):
        """清除布局中的所有内容"""
        while layout.count():
            child = layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.deleteLater()
            else:
                sub_layout = child.layout()
                if sub_layout:
                    self._clear_layout(sub_layout)

    def set_mode(self, mode: str):
        """切换模式"""
        if mode not in ("list", "detail"):
            return
        if mode == self._mode:
            return

        self._mode = mode

        if mode == "list":
            self._init_list_mode()
            self._render_list()
        else:
            self._init_detail_mode()
            self._render_detail()

        self.mode_changed.emit(mode)

    def refresh_data(self):
        """异步刷新出货列表 - 调用API获取数据"""
        logger.info("[出货Tab] refresh_data 开始")
        try:
            self._shipments = self.api_client.get_shipments() or []
            logger.info(f"[出货Tab] 获取到 {len(self._shipments)} 条记录")
        except Exception as e:
            logger.error(f"[出货Tab] 获取出货列表失败: {e}")
            self._shipments = []
        self._render_list()

    def _render_list(self):
        """渲染列表"""
        if not hasattr(self, 'list_table'):
            return

        self.list_table.setRowCount(0)
        for idx, shipment in enumerate(self._shipments):
            self.list_table.insertRow(idx)
            self._populate_list_row(idx, shipment)

    def _populate_list_row(self, row, shipment):
        """填充列表行"""
        self.list_table.setItem(row, 0, QTableWidgetItem(str(shipment.get('id', ''))))
        self.list_table.setItem(row, 1, QTableWidgetItem(shipment.get('shipment_no', '')))
        self.list_table.setItem(row, 2, QTableWidgetItem(shipment.get('ci_no', '')))
        self.list_table.setItem(row, 3, QTableWidgetItem(shipment.get('customs_no', '')))
        self.list_table.setItem(row, 4, QTableWidgetItem(shipment.get('pi_no', '')))
        self.list_table.setItem(row, 5, QTableWidgetItem(f"{shipment.get('total_amount', 0):.2f}"))
        self.list_table.setItem(row, 6, QTableWidgetItem(str(shipment.get('total_cartons', 0))))

        # 状态（带颜色）
        status = shipment.get('status', 1)
        status_text = STATUS_MAP.get(status, "未知")
        status_item = QTableWidgetItem(status_text)
        color = STATUS_COLOR.get(status, "#6b7280")
        status_item.setForeground(QColor(color))
        self.list_table.setItem(row, 7, status_item)

        self.list_table.setItem(row, 8, QTableWidgetItem(shipment.get('created_at', '')))

    def _render_detail(self):
        """渲染详情"""
        if not hasattr(self, 'detail_table') or not self._current_shipment:
            return

        sh = self._current_shipment
        self.title_label.setText(f"出货单号: {sh.get('shipment_no', '')} | CI号: {sh.get('ci_no', '')}")
        self.summary_label.setText(
            f"PI号: {sh.get('pi_no', '')} | "
            f"总箱数: {sh.get('total_cartons', 0)} | "
            f"总金额: {sh.get('total_amount', 0):.2f}"
        )

        self.detail_table.setRowCount(0)
        items = sh.get('items', [])
        for idx, item in enumerate(items):
            self.detail_table.insertRow(idx)
            for col, key in enumerate(['_seq', 'customer_code', 'oe_number', 'product_image',
                                       'order_quantity', 'order_unit_price', 'order_total_amount',
                                       'cartons_estimated', 'volume_estimated', 'gross_weight_kg',
                                       'shipment_quantity', 'shipment_unit_price', 'shipment_total_amount',
                                       'shipment_cartons', 'shipment_volume', 'shipment_weight',
                                       'remaining_quantity', 'remaining_cartons', 'remaining_volume']):
                if key == '_seq':
                    self.detail_table.setItem(idx, col, QTableWidgetItem(str(idx + 1)))
                else:
                    val = item.get(key, '')
                    self.detail_table.setItem(idx, col, QTableWidgetItem(str(val) if val is not None else ''))

    def _on_filter_changed(self):
        """筛选条件变化"""
        self._render_list()

    def _on_row_double_clicked(self, row, col):
        """双击行 - 进入详情（从API获取完整含items的数据）"""
        if row < 0 or row >= len(self._shipments):
            return
        shipment_id = self._shipments[row].get('id')
        try:
            self._current_shipment = self.api_client.get_shipment(shipment_id)
            logger.info(f"[出货Tab] 获取详情 id={shipment_id}, items={len(self._current_shipment.get('items', []))}")
        except Exception as e:
            logger.error(f"[出货Tab] 获取详情失败: {e}, 降级用列表数据")
            self._current_shipment = self._shipments[row]
        self.set_mode("detail")

    def _on_export_pl(self):
        """导出 PL"""
        logger.info("[出货Tab] 导出 PL")
        if not self._current_shipment:
            QMessageBox.warning(self, "提示", "请先选择出货单")
            return

        try:
            import tempfile, os
            shipment_id = self._current_shipment.get('id')
            shipment_no = self._current_shipment.get('shipment_no', shipment_id)
            content = self.api_client.export_pl_excel(shipment_id)

            filename = f"PL_{shipment_no}.xlsx"
            filepath = os.path.join(tempfile.gettempdir(), filename)
            with open(filepath, 'wb') as f:
                f.write(content)

            os.startfile(filepath)
            logger.info(f"[出货Tab] PL导出成功: {filename}")
        except Exception as e:
            logger.error(f"[出货Tab] PL导出失败: {e}")
            QMessageBox.warning(self, "错误", f"PL导出失败: {str(e)}")

    def _on_export_ci(self):
        """导出 CI"""
        logger.info("[出货Tab] 导出 CI")
        if not self._current_shipment:
            QMessageBox.warning(self, "提示", "请先选择出货单")
            return

        try:
            import tempfile, os
            shipment_id = self._current_shipment.get('id')
            shipment_no = self._current_shipment.get('shipment_no', shipment_id)
            content = self.api_client.export_ci_excel(shipment_id)

            filename = f"CI_{shipment_no}.xlsx"
            filepath = os.path.join(tempfile.gettempdir(), filename)
            with open(filepath, 'wb') as f:
                f.write(content)

            os.startfile(filepath)
            logger.info(f"[出货Tab] CI导出成功: {filename}")
        except Exception as e:
            logger.error(f"[出货Tab] CI导出失败: {e}")
            QMessageBox.warning(self, "错误", f"CI导出失败: {str(e)}")
