# -*- coding: utf-8 -*-
"""订单相关 Dialog"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem, QPushButton,
    QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class OrderEditDialog(QDialog):
    """轻量订单编辑对话框 - 仅订单基本信息 + 客户选择"""
    def __init__(self, order, parent=None, customers=None):
        super().__init__(parent)
        self.order = order
        self.updated_order = order.copy()
        self.customers = customers or []

        if not self.order.get('order_no'):
            from datetime import datetime
            self.order['order_no'] = f"PI-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        if not self.order.get('order_date'):
            from datetime import datetime
            self.order['order_date'] = datetime.now().strftime('%Y-%m-%d')

        self.setWindowTitle(f"编辑订单: {self.order.get('order_no', '新建订单')}")
        self.setMinimumWidth(500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        info_group = QGroupBox("📋 订单基本信息")
        info_layout = QFormLayout()

        order_no_input = QLineEdit(self.order.get('order_no', ''))
        order_no_input.setReadOnly(True)
        order_no_input.setStyleSheet("background-color: #f3f4f6;")
        info_layout.addRow("ORDER NO.:", order_no_input)

        date_input = QLineEdit(self.order.get('order_date', ''))
        date_input.setReadOnly(True)
        date_input.setStyleSheet("background-color: #f3f4f6;")
        info_layout.addRow("订单日期:", date_input)

        self.customer_combo = QComboBox()
        self.customer_combo.addItem("-- 请选择 --", None)
        for c in self.customers:
            customer_name = c.get('customer_name', '') or c.get('name', '')
            self.customer_combo.addItem(customer_name, c.get('id'))
        current_customer_id = self.order.get('customer_id')
        for i in range(self.customer_combo.count()):
            if self.customer_combo.itemData(i) == current_customer_id:
                self.customer_combo.setCurrentIndex(i)
                break
        info_layout.addRow("客户:", self.customer_combo)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["USD", "RMB", "EUR"])
        currency = self.order.get('currency', 'USD')
        self.currency_combo.setCurrentText(currency if currency else 'USD')
        info_layout.addRow("币种:", self.currency_combo)

        self.remark_edit = QTextEdit(self.order.get('remark', ''))
        self.remark_edit.setMaximumHeight(80)
        info_layout.addRow("备注:", self.remark_edit)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("💾 保存")
        save_btn.setFixedWidth(100)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _on_save(self):
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            QMessageBox.warning(self, "警告", "请选择客户")
            return

        self.updated_order['customer_id'] = customer_id
        self.updated_order['currency'] = self.currency_combo.currentText()
        self.updated_order['remark'] = self.remark_edit.toPlainText()
        self.accept()

    def get_order(self):
        return self.updated_order


class ReplyHistoryDialog(QDialog):
    """回复历史对话框"""
    def __init__(self, replies, parent=None):
        super().__init__(parent)
        self.replies = replies or []
        self.setWindowTitle("回复历史记录")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        label = QLabel(f"共 {len(self.replies)} 条回复记录")
        layout.addWidget(label)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["时间", "回复人", "回复内容", "附件"])
        layout.addWidget(self.table)

        for reply in self.replies:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(reply.get('created_at', '')))
            self.table.setItem(row, 1, QTableWidgetItem(reply.get('replier', '')))
            self.table.setItem(row, 2, QTableWidgetItem(reply.get('content', '')))
            self.table.setItem(row, 3, QTableWidgetItem(reply.get('attachment', '') or ''))

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
