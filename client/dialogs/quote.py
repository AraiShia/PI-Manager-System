# -*- coding: utf-8 -*-
"""
报价相关 Dialog

文件：client/dialogs/quote.py
创建日期：2026-06-04
来源：main.py L8320-8598（QuoteDialog）, L8599-8717（QuoteProductDialog）（已迁移合并）
包含：
- QuoteDialog: 报价单对话框
- QuoteProductDialog: 报价产品对话框

调用方式：
```python
from dialogs import QuoteDialog, QuoteProductDialog

# 新建报价单
dialog = QuoteDialog(parent_window, api_client, dept_id)
if dialog.exec():
    # 保存成功

# 编辑报价单
dialog = QuoteDialog(parent_window, api_client, dept_id, quote=quote_data)
if dialog.exec():
    # 编辑成功

# 添加报价产品
dialog = QuoteProductDialog(parent, api_client, customer)
if dialog.exec():
    product = dialog.get_product()
```

依赖：
- PySide6.QtWidgets: QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
  QLabel, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem, QPushButton,
  QDateEdit, QHeaderView, QAbstractItemView, QMessageBox
- PySide6.QtCore: Qt, QTimer
- PySide6.QtGui: QFont
- api.client.ApiClient: api_client 实例
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QPushButton, QDateEdit, QHeaderView, QAbstractItemView, QMessageBox,
    QWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.client import ApiClient


class QuoteDialog(QDialog):
    """
    报价单对话框
    
    功能：
    - 新建/编辑报价单
    - 导入客户历史采购产品
    - 管理报价产品明细
    - 自动计算总金额
    
    构造参数：
    - parent: QWidget, 父窗口
    - api_client: ApiClient, API 客户端
    - dept_id: str, 部门ID
    - quote: dict, 报价单数据（编辑模式），None 表示新建模式
    """
    
    def __init__(self, parent, api_client, dept_id, quote=None):
        super().__init__(parent)
        self.api_client = api_client
        self.dept_id = dept_id
        self.quote = quote
        self.is_edit = quote is not None
        self.customers = []
        self.products = []
        self.items = []
        self.init_ui()
        QTimer.singleShot(0, self.load_data)

    def load_data(self):
        """加载数据"""
        try:
            self.customers = self.api_client.get_customers()
            self.customer_combo.clear()
            self.customer_combo.addItem("", "")
            for c in self.customers:
                self.customer_combo.addItem(f"{c.get('customer_code')} - {c.get('customer_name')}", c.get('id'))
            if self.quote:
                customer_id = self.quote.get('customer_id')
                idx = self.customer_combo.findData(customer_id)
                if idx >= 0:
                    self.customer_combo.setCurrentIndex(idx)
                currency = self.quote.get('currency', 'USD')
                idx = self.currency_combo.findText(currency)
                if idx >= 0:
                    self.currency_combo.setCurrentIndex(idx)
                valid_until = self.quote.get('valid_until')
                if valid_until:
                    from PySide6.QtCore import QDate
                    parts = str(valid_until)[:10].split('-')
                    if len(parts) == 3:
                        self.valid_until_input.setDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))
                remark = self.quote.get('remark', '')
                if remark:
                    self.remark_input.setText(str(remark))
                if 'items' in self.quote and self.quote['items']:
                    self.items = self.quote['items']
                    self.refresh_items_table()
        except Exception as e:
            print(f"加载数据失败: {e}")

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("编辑报价单" if self.is_edit else "新建报价单")
        self.setMinimumSize(900, 600)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout()
        basic_layout.setSpacing(10)

        self.customer_combo = QComboBox()
        self.customer_combo.setFixedHeight(35)
        self.customer_combo.currentIndexChanged.connect(self.on_customer_changed)
        basic_layout.addRow("客户:", self.customer_combo)

        self.currency_combo = QComboBox()
        self.currency_combo.setFixedHeight(35)
        self.currency_combo.addItems(["USD", "EUR", "CNY", "GBP"])
        basic_layout.addRow("币种:", self.currency_combo)

        self.valid_until_input = QDateEdit()
        self.valid_until_input.setCalendarPopup(True)
        self.valid_until_input.setFixedHeight(35)
        self.valid_until_input.setDate(QDate.currentDate().addDays(30))
        basic_layout.addRow("有效期至:", self.valid_until_input)

        self.remark_input = QLineEdit()
        self.remark_input.setFixedHeight(35)
        basic_layout.addRow("备注:", self.remark_input)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        import_group = QGroupBox("产品明细")
        import_layout = QVBoxLayout()

        import_toolbar = QHBoxLayout()
        import_toolbar.addStretch()

        import_btn = QPushButton("导入历史采购")
        import_btn.clicked.connect(self.import_customer_products)
        import_btn.setStyleSheet("""
            QPushButton { background-color: #10b981; color: white; border: none; border-radius: 4px; padding: 8px 16px; }
            QPushButton:hover { background-color: #059669; }
        """)
        import_toolbar.addWidget(import_btn)

        add_product_btn = QPushButton("+ 添加产品")
        add_product_btn.clicked.connect(self.add_product)
        add_product_btn.setStyleSheet("""
            QPushButton { background-color: #3b82f6; color: white; border: none; border-radius: 4px; padding: 8px 16px; }
            QPushButton:hover { background-color: #2563eb; }
        """)
        import_toolbar.addWidget(add_product_btn)
        import_layout.addLayout(import_toolbar)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(8)
        self.items_table.setHorizontalHeaderLabels(["产品编号", "OE号", "客户编号", "产品描述", "数量", "单价", "总价", "操作"])
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.items_table.setMaximumHeight(250)
        import_layout.addWidget(self.items_table)

        summary_layout = QHBoxLayout()
        summary_layout.addStretch()
        self.total_label = QLabel("总金额: $0.00")
        self.total_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2563eb;")
        summary_layout.addWidget(self.total_label)
        import_layout.addLayout(summary_layout)

        import_group.setLayout(import_layout)
        layout.addWidget(import_group)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_quote)
        save_btn.setStyleSheet("""
            QPushButton { background-color: #2563eb; color: white; border: none; border-radius: 6px; padding: 8px 24px; }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        buttons_layout.addWidget(save_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #e5e7eb; color: #374151; border: none; border-radius: 6px; padding: 8px 24px; }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def on_customer_changed(self):
        """客户变化时自动选择币种"""
        customer_id = self.customer_combo.currentData()
        if customer_id:
            for c in self.customers:
                if c.get('id') == customer_id:
                    currency = c.get('currency')
                    if currency:
                        idx = self.currency_combo.findText(currency)
                        if idx >= 0:
                            self.currency_combo.setCurrentIndex(idx)
                    break

    def import_customer_products(self):
        """从客户历史采购导入产品"""
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            QMessageBox.warning(self, "警告", "请先选择客户")
            return
        try:
            products = self.api_client.get_customer_products(customer_id)
            if not products:
                QMessageBox.information(self, "提示", "该客户没有采购历史记录")
                return
            for p in products:
                item = {
                    'product_id': p.get('product_id'),
                    'product_code': p.get('product_code'),
                    'oe_number': p.get('oe_number'),
                    'customer_code': p.get('customer_code'),
                    'detail_desc': p.get('detail_desc'),
                    'quantity': p.get('last_quantity') or 1,
                    'unit_price': p.get('unit_price') or 0,
                    'total_price': (p.get('last_quantity') or 1) * (p.get('unit_price') or 0)
                }
                self.items.append(item)
            self.refresh_items_table()
            QMessageBox.information(self, "成功", f"已导入 {len(products)} 个产品")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导入失败: {str(e)}")

    def add_product(self):
        """添加产品"""
        customer = self.customer_combo.currentData()
        dialog = QuoteProductDialog(self, self.api_client, customer)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            product = dialog.get_product()
            if product:
                self.items.append(product)
                self.refresh_items_table()

    def edit_item(self, index):
        """编辑产品"""
        if index < 0 or index >= len(self.items):
            return
        item = self.items[index]
        dialog = QuoteProductDialog(self, self.api_client, None, item)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.items[index] = dialog.get_product()
            self.refresh_items_table()

    def delete_item(self, index):
        """删除产品"""
        if index < 0 or index >= len(self.items):
            return
        reply = QMessageBox.question(self, "确认", "确定要删除此产品吗？")
        if reply == QMessageBox.StandardButton.Yes:
            self.items.pop(index)
            self.refresh_items_table()

    def refresh_items_table(self):
        """刷新产品表格"""
        self.items_table.setRowCount(len(self.items))
        total = 0
        for row, item in enumerate(self.items):
            self.items_table.setItem(row, 0, QTableWidgetItem(item.get('product_code', '')))
            self.items_table.setItem(row, 1, QTableWidgetItem(item.get('oe_number', '')))
            self.items_table.setItem(row, 2, QTableWidgetItem(item.get('customer_code', '')))
            self.items_table.setItem(row, 3, QTableWidgetItem(item.get('detail_desc', '')))
            self.items_table.setItem(row, 4, QTableWidgetItem(str(item.get('quantity', 0))))
            self.items_table.setItem(row, 5, QTableWidgetItem(f"${item.get('unit_price', 0):.2f}"))
            total_price = item.get('quantity', 0) * item.get('unit_price', 0)
            total += total_price
            self.items_table.setItem(row, 6, QTableWidgetItem(f"${total_price:.2f}"))
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0, 0, 0, 0)
            edit_btn = QPushButton("编辑")
            edit_btn.setFixedWidth(40)
            edit_btn.clicked.connect(lambda _, r=row: self.edit_item(r))
            btn_layout.addWidget(edit_btn)
            del_btn = QPushButton("删除")
            del_btn.setFixedWidth(40)
            del_btn.setStyleSheet("color: #ef4444;")
            del_btn.clicked.connect(lambda _, r=row: self.delete_item(r))
            btn_layout.addWidget(del_btn)
            btn_widget.setLayout(btn_layout)
            self.items_table.setCellWidget(row, 7, btn_widget)
        self.total_label.setText(f"总金额: ${total:,.2f}")

    def save_quote(self):
        """保存报价单"""
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            QMessageBox.warning(self, "警告", "请选择客户")
            return
        if not self.items:
            QMessageBox.warning(self, "警告", "请至少添加一个产品")
            return
        quote_data = {
            "dept_id": self.dept_id,
            "customer_id": customer_id,
            "currency": self.currency_combo.currentText(),
            "valid_until": self.valid_until_input.date().toString("yyyy-MM-dd"),
            "remark": self.remark_input.text().strip(),
            "items": [
                {
                    "product_id": item.get('product_id'),
                    "oe_number": item.get('oe_number'),
                    "customer_code": item.get('customer_code'),
                    "detail_desc": item.get('detail_desc'),
                    "quantity": item.get('quantity', 0),
                    "unit_price": item.get('unit_price', 0),
                    "remark": ""
                }
                for item in self.items
            ]
        }
        try:
            if self.is_edit:
                self.api_client.update_quote(self.quote.get('id'), quote_data)
            else:
                self.api_client.create_quote(quote_data)
            QMessageBox.information(self, "成功", "报价单已保存")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")


class QuoteProductDialog(QDialog):
    """
    报价产品对话框
    
    功能：
    - 添加/编辑报价产品
    - 自动获取最新采购价格
    
    构造参数：
    - parent: QWidget, 父窗口
    - api_client: ApiClient, API 客户端
    - customer: dict, 客户数据
    - item: dict, 产品数据（编辑模式），None 表示新建模式
    """
    
    def __init__(self, parent, api_client, customer, item=None):
        super().__init__(parent)
        self.api_client = api_client
        self.customer = customer
        self.item = item or {}
        self.products = []
        self.init_ui()
        self.load_products()

    def load_products(self):
        """加载产品列表"""
        try:
            self.products = self.api_client.get_products()
            self.product_combo.clear()
            self.product_combo.addItem("", None)
            for p in self.products:
                self.product_combo.addItem(f"{p.get('product_code')} - {p.get('description', '')}", p)
            if self.item.get('product_id'):
                idx = self.product_combo.findData(self.item.get('product_id'))
                if idx >= 0:
                    self.product_combo.setCurrentIndex(idx)
        except Exception as e:
            print(f"加载产品失败: {e}")

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("编辑产品" if self.item else "添加产品")
        self.setFixedSize(500, 400)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.product_combo = QComboBox()
        self.product_combo.setFixedHeight(35)
        self.product_combo.currentIndexChanged.connect(self.on_product_selected)
        form_layout.addRow("产品:", self.product_combo)
        
        self.oe_number_input = QLineEdit()
        self.oe_number_input.setFixedHeight(35)
        form_layout.addRow("OE号:", self.oe_number_input)
        
        self.customer_code_input = QLineEdit()
        self.customer_code_input.setFixedHeight(35)
        if self.customer:
            self.customer_code_input.setText(self.customer.get('customer_code', ''))
        form_layout.addRow("客户编号:", self.customer_code_input)
        
        self.detail_desc_input = QLineEdit()
        self.detail_desc_input.setFixedHeight(35)
        form_layout.addRow("产品描述:", self.detail_desc_input)
        
        self.quantity_input = QLineEdit()
        self.quantity_input.setFixedHeight(35)
        self.quantity_input.setText(str(self.item.get('quantity', 1)))
        form_layout.addRow("数量:", self.quantity_input)
        
        self.unit_price_input = QLineEdit()
        self.unit_price_input.setFixedHeight(35)
        self.unit_price_input.setText(str(self.item.get('unit_price', 0)))
        form_layout.addRow("单价:", self.unit_price_input)
        
        layout.addLayout(form_layout)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.validate_and_accept)
        ok_btn.setStyleSheet("""
            QPushButton { background-color: #2563eb; color: white; border: none; border-radius: 6px; padding: 8px 24px; }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        buttons_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #e5e7eb; color: #374151; border: none; border-radius: 6px; padding: 8px 24px; }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def on_product_selected(self):
        """产品选择后自动填充字段"""
        product = self.product_combo.currentData()
        if product:
            if not self.oe_number_input.text():
                self.oe_number_input.setText(product.get('oe_number', ''))
            if not self.detail_desc_input.text():
                self.detail_desc_input.setText(product.get('description', ''))
            if self.customer and product.get('id'):
                try:
                    price_info = self.api_client.get_latest_price(self.customer.get('id'), product.get('id'))
                    if price_info and price_info.get('unit_price'):
                        self.unit_price_input.setText(str(price_info['unit_price']))
                except Exception:
                    pass

    def validate_and_accept(self):
        """验证并接受"""
        try:
            qty = float(self.quantity_input.text())
            price = float(self.unit_price_input.text())
            if qty <= 0:
                QMessageBox.warning(self, "警告", "数量必须大于0")
                return
            if price < 0:
                QMessageBox.warning(self, "警告", "单价不能为负")
                return
            self.accept()
        except ValueError:
            QMessageBox.warning(self, "警告", "数量和单价必须是数字")
            return

    def get_product(self):
        """获取产品数据"""
        product = self.product_combo.currentData()
        return {
            'product_id': product.get('id') if product else None,
            'product_code': product.get('product_code', '') if product else '',
            'oe_number': self.oe_number_input.text().strip(),
            'customer_code': self.customer_code_input.text().strip(),
            'detail_desc': self.detail_desc_input.text().strip(),
            'quantity': float(self.quantity_input.text() or 0),
            'unit_price': float(self.unit_price_input.text() or 0),
            'total_price': float(self.quantity_input.text() or 0) * float(self.unit_price_input.text() or 0)
        }