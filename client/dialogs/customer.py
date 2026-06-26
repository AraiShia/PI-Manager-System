# -*- coding: utf-8 -*-
"""
客户相关 Dialog

文件：client/dialogs/customer.py
创建日期：2026-06-04
来源：main.py L706-1494（已迁移合并）
包含：
- CustomerDialog: 客户编辑/新建对话框
- CustomerDetailDialog: 客户详情查看对话框
- AddressDialog: 收货地址编辑对话框
- ContactDialog: 联系人编辑对话框

调用方式：
```python
from dialogs import CustomerDialog, CustomerDetailDialog, AddressDialog, ContactDialog

# 新建客户
dialog = CustomerDialog(api_client)
if dialog.exec():
    new_customer = dialog.get_customer()

# 编辑客户
dialog = CustomerDialog(api_client, customer=customer_data)
if dialog.exec():
    updated = dialog.get_customer()

# 查看客户详情
dialog = CustomerDetailDialog(api_client, customer)
dialog.exec()

# 编辑地址
dialog = AddressDialog(api_client, customer_id=123)
dialog.exec()

# 编辑联系人
dialog = ContactDialog(api_client, customer_id=123, contact=contact_data)
dialog.exec()
```

依赖：
- PySide6.QtWidgets: QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel, QLineEdit, QTextEdit, QComboBox, QTableWidget, QTableWidgetItem, QPushButton, QCheckBox, QHeaderView, QAbstractItemView, QTabWidget
- PySide6.QtCore: Qt
- PySide6.QtGui: QFont, QColor, QBrush
- api.client.ApiClient: api_client 实例
- cache_manager.invalidate_cache: 缓存失效
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QTextEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QPushButton, QCheckBox, QHeaderView, QAbstractItemView, QTabWidget,
    QMessageBox, QRadioButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QBrush

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.client import ApiClient


class CustomerDialog(QDialog):
    """
    客户编辑/新建对话框
    
    功能：
    - 新建客户（填写基本信息）
    - 编辑现有客户
    - 管理客户联系人
    
    构造参数：
    - api_client: ApiClient, API 客户端
    - customer: dict, 客户数据（编辑模式），None 表示新建模式
    """
    
    def __init__(self, api_client, customer=None):
        super().__init__()
        self.api_client = api_client
        self.customer = customer
        self.is_edit = customer is not None
        self.init_ui()
        if self.is_edit:
            self.load_contacts()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("编辑客户" if self.is_edit else "新增客户")
        self.setMinimumSize(750, 600)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.dept_combo = QComboBox()
        self.dept_combo.addItems([
            "S - 索英普",
            "W - 维那",
            "M - 马迪那",
            "D - 银达"
        ])
        if self.customer:
            dept_text_map = {"S": "S - 索英普", "W": "W - 维那", "M": "M - 马迪那", "D": "D - 银达"}
            saved_dept = self.customer.get('dept_id', 'S')
            self.dept_combo.setCurrentText(dept_text_map.get(saved_dept, "S - 索英普"))
        form_layout.addRow("部门:", self.dept_combo)

        if self.is_edit:
            self.code_label = QLabel(self.customer.get('customer_code', ''))
            form_layout.addRow("客户编号:", self.code_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入客户名称")
        if self.customer:
            self.name_input.setText(self.customer.get('customer_name', ''))
        form_layout.addRow("客户名称 *:", self.name_input)

        self.country_input = QLineEdit()
        self.country_input.setPlaceholderText("请输入所在国家")
        if self.customer:
            self.country_input.setText(self.customer.get('country', ''))
        form_layout.addRow("所在国家 *:", self.country_input)

        self.basic_require_input = QTextEdit()
        self.basic_require_input.setPlaceholderText("请输入通用交易条款")
        self.basic_require_input.setMaximumHeight(60)
        if self.customer:
            self.basic_require_input.setText(self.customer.get('basic_require', ''))
        form_layout.addRow("基本要求:", self.basic_require_input)

        self.special_input = QTextEdit()
        self.special_input.setPlaceholderText("请输入特殊要求，如特定包装、标签等")
        self.special_input.setMaximumHeight(60)
        if self.customer:
            self.special_input.setText(self.customer.get('special_require', ''))
        form_layout.addRow("特殊要求:", self.special_input)

        self.payment_input = QLineEdit()
        self.payment_input.setPlaceholderText("如 T/T 30天")
        if self.customer:
            self.payment_input.setText(self.customer.get('payment_terms', ''))
        form_layout.addRow("付款条款:", self.payment_input)

        layout.addLayout(form_layout)

        contacts_group = QGroupBox("联系人信息")
        contacts_layout = QVBoxLayout()
        contacts_layout.setSpacing(5)

        self.contacts_table = QTableWidget()
        self.contacts_table.setColumnCount(4)
        self.contacts_table.setHorizontalHeaderLabels(["姓名", "电话", "邮箱", "职位"])
        self.contacts_table.setMaximumHeight(150)
        self.contacts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.contacts_table.setAlternatingRowColors(True)
        header = self.contacts_table.horizontalHeader()
        for i in range(4):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        contacts_layout.addWidget(self.contacts_table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ 添加联系人")
        add_btn.setFixedWidth(100)
        add_btn.clicked.connect(self.add_contact_row)
        remove_btn = QPushButton("- 删除选中")
        remove_btn.setFixedWidth(100)
        remove_btn.clicked.connect(self.remove_selected_contact)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        contacts_layout.addLayout(btn_row)

        contacts_group.setLayout(contacts_layout)
        layout.addWidget(contacts_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.save_customer)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_contacts(self):
        """加载客户联系人"""
        if not self.customer:
            return
        try:
            contacts = self.api_client.get_customer_contacts(self.customer['id'])
            self.populate_contacts_table(contacts or [])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载联系人失败: {str(e)}")

    def populate_contacts_table(self, contacts):
        """填充联系人表格"""
        self.contacts_table.setRowCount(len(contacts))
        for row, contact in enumerate(contacts):
            self.contacts_table.setItem(row, 0, QTableWidgetItem(contact.get('name', '')))
            self.contacts_table.setItem(row, 1, QTableWidgetItem(contact.get('phone', '')))
            self.contacts_table.setItem(row, 2, QTableWidgetItem(contact.get('email', '')))
            self.contacts_table.setItem(row, 3, QTableWidgetItem(contact.get('position', '')))

    def add_contact_row(self):
        """添加联系人行"""
        row = self.contacts_table.rowCount()
        self.contacts_table.insertRow(row)
        for col in range(4):
            self.contacts_table.setItem(row, col, QTableWidgetItem(""))

    def remove_selected_contact(self):
        """删除选中的联系人行"""
        current_row = self.contacts_table.currentRow()
        if current_row >= 0:
            self.contacts_table.removeRow(current_row)

    def save_customer(self):
        """保存客户"""
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入客户名称")
            return
        if not self.country_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入所在国家")
            return

        dept_map = {"S - 索英普": "S", "W - 维那": "W", "M - 马迪那": "M", "D - 银达": "D"}
        dept_id = dept_map.get(self.dept_combo.currentText(), "S")

        data = {
            "dept_id": dept_id,
            "customer_name": self.name_input.text().strip(),
            "country": self.country_input.text().strip(),
            "basic_require": self.basic_require_input.toPlainText().strip(),
            "special_require": self.special_input.toPlainText().strip(),
            "payment_terms": self.payment_input.text().strip()
        }

        try:
            if self.is_edit:
                result = self.api_client.update_customer(self.customer['id'], data)
                self.save_contacts(self.customer['id'])
            else:
                result = self.api_client.create_customer(data)
                if result and 'id' in result:
                    self.save_contacts(result['id'])
            invalidate_cache("customers")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")

    def save_contacts(self, customer_id):
        """保存客户联系人"""
        contacts_to_save = []
        for row in range(self.contacts_table.rowCount()):
            name = self.contacts_table.item(row, 0).text().strip()
            phone = self.contacts_table.item(row, 1).text().strip()
            email = self.contacts_table.item(row, 2).text().strip()
            position = self.contacts_table.item(row, 3).text().strip()

            if name or phone or email:
                contacts_to_save.append({
                    "name": name,
                    "phone": phone,
                    "email": email,
                    "position": position,
                    "is_primary": 1 if row == 0 else 0
                })

        try:
            old_contacts = self.api_client.get_customer_contacts(customer_id)
            for contact in old_contacts:
                self.api_client.delete_customer_contact(customer_id, contact['id'])
        except Exception:
            pass

        for contact_data in contacts_to_save:
            try:
                self.api_client.create_customer_contact(customer_id, contact_data)
            except Exception as e:
                print(f"创建联系人失败: {e}")

    def get_customer(self):
        """获取客户数据"""
        return self.customer


class CustomerDetailDialog(QDialog):
    """
    客户详情查看对话框
    
    功能：
    - 显示客户完整信息（基本信息、地址、联系人、PI历史）
    - 管理收货地址
    - 管理联系人
    
    构造参数：
    - api_client: ApiClient, API 客户端
    - customer: dict, 客户数据
    """
    
    def __init__(self, api_client: ApiClient, customer):
        super().__init__()
        self.api_client = api_client
        self.customer = customer
        self.addresses = []
        self.contacts = []
        self.pi_orders = []
        self.init_ui()
        self.load_data()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"客户详情 - {self.customer.get('customer_name', '')}")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # 标签页
        self.tab_widget = QTabWidget()
        
        # 基本信息页
        self.basic_tab = QWidget()
        self.setup_basic_tab()
        
        # 收货地址页
        self.address_tab = QWidget()
        self.setup_address_tab()
        
        # 联系人页
        self.contact_tab = QWidget()
        self.setup_contact_tab()
        
        # PI订单历史页
        self.pi_tab = QWidget()
        self.setup_pi_tab()

        self.tab_widget.addTab(self.basic_tab, "基本信息")
        self.tab_widget.addTab(self.address_tab, "收货地址")
        self.tab_widget.addTab(self.contact_tab, "联系人")
        self.tab_widget.addTab(self.pi_tab, "交易历史")

        layout.addWidget(self.tab_widget)

        # 关闭按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def setup_basic_tab(self):
        """设置基本信息页"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        form_layout.addRow(QLabel("<b>客户编号:</b>"), QLabel(self.customer.get('customer_code', '')))
        form_layout.addRow(QLabel("<b>客户名称:</b>"), QLabel(self.customer.get('customer_name', '')))
        form_layout.addRow(QLabel("<b>所属部门:</b>"), QLabel(self.customer.get('dept_id', '')))
        form_layout.addRow(QLabel("<b>所在国家:</b>"), QLabel(self.customer.get('country', '')))
        
        basic_require = self.customer.get('basic_require', '')
        form_layout.addRow(QLabel("<b>基本要求:</b>"), QLabel(basic_require if basic_require else "-"))
        
        form_layout.addRow(QLabel("<b>付款条款:</b>"), QLabel(self.customer.get('payment_terms', '') or "-"))
        
        status = self.customer.get('status', 1)
        status_text = "启用" if status == 1 else "禁用"
        status_color = "#10b981" if status == 1 else "#ef4444"
        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
        form_layout.addRow(QLabel("<b>状态:</b>"), status_label)

        layout.addLayout(form_layout)
        layout.addStretch()

        special_require = self.customer.get('special_require', '')
        if special_require:
            special_group = QGroupBox("特殊要求")
            special_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #dc2626; border-radius: 5px; }")
            special_layout = QVBoxLayout()
            special_label = QLabel(special_require)
            special_label.setWordWrap(True)
            special_label.setStyleSheet("color: #dc2626; padding: 5px;")
            special_layout.addWidget(special_label)
            special_group.setLayout(special_layout)
            layout.addWidget(special_group)

        self.basic_tab.setLayout(layout)

    def setup_address_tab(self):
        """设置收货地址页"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        toolbar = QHBoxLayout()
        add_btn = QPushButton("+ 添加地址")
        add_btn.clicked.connect(self.add_address)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        toolbar.addWidget(add_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.addresses_table = QTableWidget()
        self.addresses_table.setColumnCount(6)
        self.addresses_table.setHorizontalHeaderLabels(["国家", "港口", "详细地址", "默认地址", "编辑", "删除"])
        self.addresses_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.addresses_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.addresses_table)

        self.address_tab.setLayout(layout)

    def setup_contact_tab(self):
        """设置联系人页"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        toolbar = QHBoxLayout()
        toolbar.addStretch()
        
        add_btn = QPushButton("+ 新增联系人")
        add_btn.clicked.connect(self.add_contact)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        toolbar.addWidget(add_btn)
        
        layout.addLayout(toolbar)

        self.contacts_table = QTableWidget()
        self.contacts_table.setColumnCount(7)
        self.contacts_table.setHorizontalHeaderLabels(["姓名", "职位", "电话", "邮箱", "是否主要", "编辑", "删除"])
        self.contacts_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.contacts_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.contacts_table)

        self.contact_tab.setLayout(layout)

    def setup_pi_tab(self):
        """设置PI订单历史页"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        self.pi_table = QTableWidget()
        self.pi_table.setColumnCount(10)
        self.pi_table.setHorizontalHeaderLabels(["", "ID", "PI号", "金额", "币种", "状态", "创建时间", "操作", "完成", "导出"])
        self.pi_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.pi_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.pi_table.setColumnWidth(0, 40)
        self.pi_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.pi_table)

        self.pi_tab.setLayout(layout)

    def load_data(self):
        """加载数据"""
        try:
            self.addresses = self.api_client.get_customer_addresses(self.customer['id'])
            self.load_addresses_table()
            self.contacts = self.api_client.get_customer_contacts(self.customer['id'])
            self.load_contacts_table()
            self.pi_orders = self.api_client.get_customer_pi_list(self.customer['id'])
            self.load_pi_table()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载数据失败: {str(e)}")

    def load_addresses_table(self):
        """加载地址表格"""
        self.addresses_table.setRowCount(len(self.addresses))
        for row, addr in enumerate(self.addresses):
            self.addresses_table.setItem(row, 0, QTableWidgetItem(addr.get('country', '')))
            self.addresses_table.setItem(row, 1, QTableWidgetItem(addr.get('port', '')))
            self.addresses_table.setItem(row, 2, QTableWidgetItem(addr.get('address_detail', '')))
            
            is_default = addr.get('is_default', 0)
            default_text = "是" if is_default == 1 else "否"
            self.addresses_table.setItem(row, 3, QTableWidgetItem(default_text))

            edit_btn = QPushButton("编辑")
            edit_btn.setFixedWidth(50)
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
            edit_btn.clicked.connect(lambda _, addr=addr: self.edit_address(addr))
            self.addresses_table.setCellWidget(row, 4, edit_btn)
            
            delete_btn = QPushButton("删除")
            delete_btn.setFixedWidth(50)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton:hover { background-color: #dc2626; }
            """)
            delete_btn.clicked.connect(lambda _, addr=addr: self.delete_address(addr))
            self.addresses_table.setCellWidget(row, 5, delete_btn)

    def load_contacts_table(self):
        """加载联系人表格"""
        self.contacts_table.setRowCount(len(self.contacts))
        for row, contact in enumerate(self.contacts):
            self.contacts_table.setItem(row, 0, QTableWidgetItem(contact.get('name', '')))
            self.contacts_table.setItem(row, 1, QTableWidgetItem(contact.get('position', '')))
            self.contacts_table.setItem(row, 2, QTableWidgetItem(contact.get('phone', '')))
            self.contacts_table.setItem(row, 3, QTableWidgetItem(contact.get('email', '')))
            
            is_primary = contact.get('is_primary', 0)
            primary_text = "是" if is_primary == 1 else "否"
            self.contacts_table.setItem(row, 4, QTableWidgetItem(primary_text))

            edit_btn = QPushButton("编辑")
            edit_btn.setFixedWidth(50)
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
            edit_btn.clicked.connect(lambda _, c=contact: self.edit_contact(c))
            self.contacts_table.setCellWidget(row, 5, edit_btn)
            
            delete_btn = QPushButton("删除")
            delete_btn.setFixedWidth(50)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton:hover { background-color: #dc2626; }
            """)
            delete_btn.clicked.connect(lambda _, c=contact: self.delete_contact(c))
            self.contacts_table.setCellWidget(row, 6, delete_btn)

    def load_pi_table(self):
        """加载PI订单表格"""
        self.pi_table.setRowCount(len(self.pi_orders))
        for row, pi in enumerate(self.pi_orders):
            self.pi_table.setItem(row, 0, QTableWidgetItem(pi.get('pi_number', '')))
            self.pi_table.setItem(row, 1, QTableWidgetItem(str(pi.get('total_amount', ''))))
            status = pi.get('status', '')
            self.pi_table.setItem(row, 2, QTableWidgetItem(status))
            created_at = pi.get('created_at', '')
            if created_at:
                created_at = created_at[:19] if isinstance(created_at, str) else str(created_at)
            self.pi_table.setItem(row, 3, QTableWidgetItem(created_at))

    def add_address(self):
        """添加地址"""
        dialog = AddressDialog(self.api_client, customer_id=self.customer['id'])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def edit_address(self, address):
        """编辑地址"""
        dialog = AddressDialog(self.api_client, customer_id=self.customer['id'], address=address)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def delete_address(self, address):
        """删除地址"""
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个地址吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.api_client.delete_customer_address(self.customer['id'], address['id'])
                self.load_data()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败：{str(e)}")

    def add_contact(self):
        """添加联系人"""
        dialog = ContactDialog(self.api_client, customer_id=self.customer['id'])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def edit_contact(self, contact):
        """编辑联系人"""
        dialog = ContactDialog(self.api_client, customer_id=self.customer['id'], contact=contact)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def delete_contact(self, contact):
        """删除联系人"""
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个联系人吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.api_client.delete_customer_contact(self.customer['id'], contact['id'])
                self.load_data()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败：{str(e)}")


class AddressDialog(QDialog):
    """
    收货地址编辑对话框
    
    功能：
    - 添加新地址
    - 编辑现有地址
    - 设置默认地址
    
    构造参数：
    - api_client: ApiClient, API 客户端
    - customer_id: int, 客户ID
    - address: dict, 地址数据（编辑模式），None 表示新建模式
    """
    
    def __init__(self, api_client: ApiClient, customer_id, address=None):
        super().__init__()
        self.api_client = api_client
        self.customer_id = customer_id
        self.address = address
        self.is_edit = address is not None
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("编辑地址" if self.is_edit else "添加地址")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.country_input = QLineEdit()
        if self.address:
            self.country_input.setText(self.address.get('country', ''))
        form_layout.addRow("国家:", self.country_input)

        self.port_input = QLineEdit()
        if self.address:
            self.port_input.setText(self.address.get('port', ''))
        form_layout.addRow("港口:", self.port_input)

        self.detail_input = QTextEdit()
        if self.address:
            self.detail_input.setText(self.address.get('address_detail', ''))
        self.detail_input.setMaximumHeight(80)
        form_layout.addRow("详细地址:", self.detail_input)

        self.default_checkbox = QCheckBox("设为默认地址")
        if self.address and self.address.get('is_default', 0) == 1:
            self.default_checkbox.setChecked(True)
        form_layout.addRow("", self.default_checkbox)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.save_address)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def save_address(self):
        """保存地址"""
        data = {
            "country": self.country_input.text().strip(),
            "port": self.port_input.text().strip(),
            "address_detail": self.detail_input.toPlainText().strip(),
            "is_default": 1 if self.default_checkbox.isChecked() else 0
        }

        try:
            if self.is_edit:
                self.api_client.update_customer_address(self.customer_id, self.address['id'], data)
            else:
                self.api_client.create_customer_address(self.customer_id, data)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败：{str(e)}")


class ContactDialog(QDialog):
    """
    联系人编辑对话框
    
    功能：
    - 添加新联系人
    - 编辑现有联系人
    - 设置为主要联系人
    
    构造参数：
    - api_client: ApiClient, API 客户端
    - customer_id: int, 客户ID
    - contact: dict, 联系人数据（编辑模式），None 表示新建模式
    """
    
    def __init__(self, api_client: ApiClient, customer_id, contact=None):
        super().__init__()
        self.api_client = api_client
        self.customer_id = customer_id
        self.contact = contact
        self.is_edit = contact is not None
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("编辑联系人" if self.is_edit else "添加联系人")
        self.setFixedSize(400, 350)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.name_input = QLineEdit()
        if self.contact:
            self.name_input.setText(self.contact.get('name', ''))
        form_layout.addRow("姓名:", self.name_input)

        self.position_input = QLineEdit()
        if self.contact:
            self.position_input.setText(self.contact.get('position', ''))
        form_layout.addRow("职位:", self.position_input)

        self.phone_input = QLineEdit()
        if self.contact:
            self.phone_input.setText(self.contact.get('phone', ''))
        form_layout.addRow("电话:", self.phone_input)

        self.email_input = QLineEdit()
        if self.contact:
            self.email_input.setText(self.contact.get('email', ''))
        form_layout.addRow("邮箱:", self.email_input)

        self.primary_checkbox = QCheckBox("设为主要联系人")
        if self.contact and self.contact.get('is_primary', 0) == 1:
            self.primary_checkbox.setChecked(True)
        form_layout.addRow("", self.primary_checkbox)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.save_contact)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def save_contact(self):
        """保存联系人"""
        data = {
            "name": self.name_input.text().strip(),
            "position": self.position_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "email": self.email_input.text().strip(),
            "is_primary": 1 if self.primary_checkbox.isChecked() else 0
        }

        try:
            if self.is_edit:
                self.api_client.update_customer_contact(self.customer_id, self.contact['id'], data)
            else:
                self.api_client.create_customer_contact(self.customer_id, data)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败：{str(e)}")