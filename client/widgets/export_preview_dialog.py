"""导出预览对话框"""

from typing import Dict, List, Optional, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QLabel, QPushButton,
    QGroupBox, QFormLayout, QLineEdit, QDateEdit, QTextEdit,
    QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class ExportPreviewDialog(QDialog):
    """导出预览对话框"""

    # 信号
    export_confirmed = Signal(dict)  # 导出确认，返回编辑后的数据
    export_cancelled = Signal()     # 导出取消

    def __init__(self, parent, export_type: str, data: Dict[str, Any], api_client):
        super().__init__(parent)
        self.export_type = export_type  # "pi" | "ci" | "pl" | "purchase"
        self.data = data
        self.api_client = api_client
        self.preview_mode = "quick"
        self.editable_fields = {}

        self._setup_ui()
        self._load_preview_data()

    def _setup_ui(self):
        """初始化UI"""
        title_map = {
            "pi": "PI导出预览",
            "ci": "CI商业发票预览",
            "pl": "PL装箱单预览",
            "purchase": "采购合同预览"
        }
        self.setWindowTitle(title_map.get(self.export_type, "导出预览"))
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # 预览模式切换
        mode_layout = QHBoxLayout()
        self.quick_preview_btn = QPushButton("快速预览")
        self.quick_preview_btn.setCheckable(True)
        self.quick_preview_btn.setChecked(True)
        self.quick_preview_btn.clicked.connect(lambda: self._set_preview_mode("quick"))

        self.full_preview_btn = QPushButton("完整预览")
        self.full_preview_btn.setCheckable(True)
        self.full_preview_btn.clicked.connect(lambda: self._set_preview_mode("full"))

        mode_layout.addWidget(self.quick_preview_btn)
        mode_layout.addWidget(self.full_preview_btn)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # 预览内容区
        self.tab_widget = QTabWidget()

        # 基本信息Tab
        self.info_tab = self._create_info_tab()
        self.tab_widget.addTab(self.info_tab, "基本信息")

        # 产品明细Tab
        self.items_tab = self._create_items_tab()
        self.tab_widget.addTab(self.items_tab, "产品明细")

        # 可编辑字段Tab
        self.edit_tab = self._create_edit_tab()
        self.tab_widget.addTab(self.edit_tab, "编辑字段")

        layout.addWidget(self.tab_widget)

        # 错误提示区
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red; padding: 8px; background-color: #fee; border-radius: 4px;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # 按钮区
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(cancel_btn)

        self.export_btn = QPushButton("导出Excel")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(self.export_btn)

        layout.addLayout(btn_layout)

    def _create_info_tab(self) -> QWidget:
        """创建基本信息Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("汇总信息")
        form = QFormLayout()

        # 动态添加字段
        summary = self.data.get("summary", {})
        self._add_info_row(form, "客户名称", summary.get("customer_name", ""))
        self._add_info_row(form, "总金额", f"{summary.get('currency', 'USD')} {summary.get('total_amount', 0):,.2f}")
        self._add_info_row(form, "产品数量", str(summary.get("items_count", 0)))
        self._add_info_row(form, "日期", summary.get("date", ""))

        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()
        return widget

    def _add_info_row(self, form: QFormLayout, label: str, value: str):
        """添加信息行"""
        row = QHBoxLayout()
        row.addWidget(QLabel(f"{label}:"))
        row.addWidget(QLabel(str(value)))
        row.addStretch()
        form.addRow(row)

    def _create_items_tab(self) -> QWidget:
        """创建产品明细Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels(["产品名称", "数量", "单价", "金额", "备注"])

        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.items_table)
        return widget

    def _create_edit_tab(self) -> QWidget:
        """创建可编辑字段Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("可编辑字段")
        form = QFormLayout()

        # 根据类型显示不同的可编辑字段
        if self.export_type == "pi":
            self.delivery_date_edit = QDateEdit()
            self.delivery_date_edit.setCalendarPopup(True)
            form.addRow("交货日期:", self.delivery_date_edit)

            self.payment_terms_edit = QLineEdit()
            form.addRow("付款条款:", self.payment_terms_edit)

            self.price_terms_edit = QLineEdit()
            self.price_terms_edit.setText("FOB")
            form.addRow("价格条款:", self.price_terms_edit)

            self.remark_edit = QTextEdit()
            self.remark_edit.setMaximumHeight(80)
            form.addRow("备注:", self.remark_edit)

        elif self.export_type in ["ci", "pl"]:
            self.loading_date_edit = QDateEdit()
            self.loading_date_edit.setCalendarPopup(True)
            form.addRow("装货日期:", self.loading_date_edit)

        elif self.export_type == "purchase":
            self.delivery_date_edit = QDateEdit()
            self.delivery_date_edit.setCalendarPopup(True)
            form.addRow("交货日期:", self.delivery_date_edit)

            self.payment_method_edit = QLineEdit()
            form.addRow("付款方式:", self.payment_method_edit)

        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()
        return widget

    def _set_preview_mode(self, mode: str):
        """切换预览模式"""
        self.preview_mode = mode
        self.quick_preview_btn.setChecked(mode == "quick")
        self.full_preview_btn.setChecked(mode == "full")

    def _load_preview_data(self):
        """加载预览数据"""
        # 填充产品明细表格
        items = self.data.get("items", [])
        self.items_table.setRowCount(len(items))

        for row, item in enumerate(items):
            self.items_table.setItem(row, 0, QTableWidgetItem(item.get("product_name", "")))
            self.items_table.setItem(row, 1, QTableWidgetItem(str(item.get("quantity", 0))))
            self.items_table.setItem(row, 2, QTableWidgetItem(f"{item.get('unit_price', 0):.2f}"))
            self.items_table.setItem(row, 3, QTableWidgetItem(f"{item.get('total_price', 0):.2f}"))
            self.items_table.setItem(row, 4, QTableWidgetItem(item.get("remark", "")))

    def _validate_data(self) -> tuple[bool, List[str]]:
        """校验数据，返回 (是否有效, 错误列表)"""
        errors = []

        # 检查客户信息
        if not self.data.get("summary", {}).get("customer_name"):
            errors.append("客户名称为空")

        # 检查产品明细
        items = self.data.get("items", [])
        if not items:
            errors.append("没有产品明细")

        for i, item in enumerate(items):
            if not item.get("product_name"):
                errors.append(f"第{i+1}行产品名称为空")
            if not item.get("quantity"):
                errors.append(f"第{i+1}行数量为空")

        return len(errors) == 0, errors

    def _on_export(self):
        """确认导出"""
        valid, errors = self._validate_data()

        if not valid:
            self.error_label.setText("校验失败:\n" + "\n".join(errors))
            self.error_label.show()
            return

        self.error_label.hide()

        # 收集编辑后的字段
        edited_data = {}
        if hasattr(self, "delivery_date_edit"):
            edited_data["delivery_date"] = self.delivery_date_edit.date().toString("yyyy-MM-dd")
        if hasattr(self, "payment_terms_edit"):
            edited_data["payment_terms"] = self.payment_terms_edit.text()
        if hasattr(self, "price_terms_edit"):
            edited_data["price_terms"] = self.price_terms_edit.text()
        if hasattr(self, "remark_edit"):
            edited_data["remark"] = self.remark_edit.toPlainText()
        if hasattr(self, "payment_method_edit"):
            edited_data["payment_method"] = self.payment_method_edit.text()

        self.editable_fields = edited_data
        self.export_confirmed.emit(edited_data)
        self.accept()

    def _on_cancel(self):
        """取消导出"""
        self.export_cancelled.emit()
        self.reject()