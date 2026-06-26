# -*- coding: utf-8 -*-
"""
付款相关 Dialog

文件：client/dialogs/payment.py
创建日期：2026-06-04
来源：main.py L9896-10359（CustomerPaymentDialog + SupplierPaymentDialog + SupplierPaymentStageDialog）（已迁移合并）
包含：
- CustomerPaymentDialog: 客户付款对话框
- SupplierPaymentDialog: 供应商付款对话框
- SupplierPaymentStageDialog: 付款阶段编辑对话框

调用方式：
```python
from dialogs import CustomerPaymentDialog, SupplierPaymentDialog, SupplierPaymentStageDialog

# 新建客户付款
dialog = CustomerPaymentDialog(api_client, dept_id)
dialog.exec()

# 编辑客户付款
dialog = CustomerPaymentDialog(api_client, dept_id, payment=payment_data)
dialog.exec()

# 新建供应商付款
dialog = SupplierPaymentDialog(api_client, dept_id)
dialog.exec()
```

依赖：
- PySide6.QtWidgets: QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
  QComboBox, QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QDateEdit,
  QMessageBox, QTextEdit
- PySide6.QtCore: Qt, QTimer
- PySide6.QtGui: QFont
- api.client.ApiClient: api_client 实例
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QComboBox, QTableWidget, QTableWidgetItem, QPushButton,
    QLineEdit, QDateEdit, QMessageBox, QTextEdit, QAbstractItemView, QHeaderView
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.client import ApiClient


class CustomerPaymentDialog(QDialog):
    """
    客户付款对话框
    
    功能：
    - 新建/编辑客户付款记录
    - 选择PI单、付款日期、金额、付款方式、备注
    
    构造参数：
    - api_client: ApiClient, API 客户端
    - dept_id: str, 部门ID
    - payment: dict, 付款数据（编辑模式），None 表示新建模式
    """
    
    def __init__(self, api_client, dept_id=None, payment=None):
        super().__init__()
        self.api_client = api_client
        self.dept_id = dept_id or "S"
        self.payment = payment
        self.is_edit = payment is not None
        self.pi_orders = []
        self.init_ui()
        QTimer.singleShot(0, self.load_data)

    def load_data(self):
        """加载PI订单列表"""
        try:
            self.pi_orders = self.api_client.get_pi_orders()
            self.pi_combo.clear()
            self.pi_combo.addItem("", "")
            for pi in self.pi_orders:
                self.pi_combo.addItem(f"{pi.get('pi_no')} - {pi.get('total_amount')}", pi)
            if self.payment:
                idx = self.pi_combo.findData(self.payment.get('pi_id'))
                if idx >= 0:
                    self.pi_combo.setCurrentIndex(idx)
        except Exception as e:
            print(f"加载PI订单失败: {e}")

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("编辑客户付款" if self.is_edit else "新建客户付款")
        self.setFixedSize(500, 350)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.pi_combo = QComboBox()
        self.pi_combo.setFixedHeight(35)
        form_layout.addRow("PI单:", self.pi_combo)

        self.payment_date_input = QDateEdit()
        self.payment_date_input.setCalendarPopup(True)
        self.payment_date_input.setFixedHeight(35)
        self.payment_date_input.setDate(QDate.currentDate())
        form_layout.addRow("付款日期:", self.payment_date_input)

        self.amount_input = QLineEdit()
        self.amount_input.setFixedHeight(35)
        form_layout.addRow("付款金额:", self.amount_input)

        self.payment_method_combo = QComboBox()
        self.payment_method_combo.setFixedHeight(35)
        self.payment_method_combo.addItems(["银行转账", "现金", "支票", "其他"])
        form_layout.addRow("付款方式:", self.payment_method_combo)

        self.remark_input = QTextEdit()
        self.remark_input.setFixedHeight(80)
        form_layout.addRow("备注:", self.remark_input)

        layout.addLayout(form_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_payment)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        buttons_layout.addWidget(save_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        if self.payment:
            self.payment_date_input.setDate(QDate.fromString(self.payment.get('payment_date', ''), "yyyy-MM-dd"))
            self.amount_input.setText(str(self.payment.get('actual_amount', '')))
            method_map = {"银行转账": 0, "现金": 1, "支票": 2, "其他": 3}
            self.payment_method_combo.setCurrentIndex(method_map.get(self.payment.get('payment_method', '银行转账'), 0))
            self.remark_input.setPlainText(self.payment.get('remark', ''))

    def save_payment(self):
        """保存客户付款"""
        pi = self.pi_combo.currentData()
        if not pi:
            QMessageBox.warning(self, "警告", "请选择PI单")
            return
        amount_text = self.amount_input.text().strip()
        if not amount_text:
            QMessageBox.warning(self, "警告", "请输入付款金额")
            return
        try:
            amount = float(amount_text)
        except ValueError:
            QMessageBox.warning(self, "警告", "付款金额必须是数字")
            return
        payment_data = {
            "dept_id": self.dept_id,
            "pi_id": pi.get('id'),
            "customer_id": pi.get('customer_id'),
            "amount": amount,
            "actual_amount": amount,
            "payment_date": self.payment_date_input.date().toString("yyyy-MM-dd"),
            "payment_method": self.payment_method_combo.currentText(),
            "remark": self.remark_input.toPlainText()
        }
        try:
            if self.is_edit:
                self.api_client.update_customer_payment(self.payment.get('id'), payment_data)
            else:
                self.api_client.create_customer_payment(payment_data)
            QMessageBox.information(self, "成功", "付款记录已保存")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")


class SupplierPaymentDialog(QDialog):
    """
    供应商付款对话框
    
    功能：
    - 新建/编辑供应商付款
    - 支持定金+尾款多阶段管理
    - 自动计算总金额、已付、未付
    
    构造参数：
    - api_client: ApiClient, API 客户端
    - dept_id: str, 部门ID
    - payment: dict, 付款数据（编辑模式），None 表示新建模式
    """
    
    def __init__(self, api_client, dept_id=None, payment=None):
        super().__init__()
        self.api_client = api_client
        self.dept_id = dept_id or "S"
        self.payment = payment
        self.is_edit = payment is not None
        self.suppliers = []
        self.purchases = []
        self.stages = []
        self.init_ui()
        QTimer.singleShot(0, self.load_data)

    def load_data(self):
        """加载供应商列表"""
        try:
            self.suppliers = self.api_client.get_suppliers()
            self.supplier_combo.clear()
            self.supplier_combo.addItem("", "")
            for s in self.suppliers:
                self.supplier_combo.addItem(f"{s.get('supplier_code')} - {s.get('supplier_name')}", s.get('id'))
            if self.payment:
                idx = self.supplier_combo.findData(self.payment.get('supplier_id'))
                if idx >= 0:
                    self.supplier_combo.setCurrentIndex(idx)
                if 'stages' in self.payment and self.payment['stages']:
                    self.stages = self.payment['stages']
                    self.refresh_stages_table()
        except Exception as e:
            print(f"加载供应商失败: {e}")

    def load_purchases(self):
        """加载供应商的采购单"""
        supplier_id = self.supplier_combo.currentData()
        if not supplier_id:
            return
        try:
            purchases = self.api_client.get_purchases_by_supplier(supplier_id)
            self.purchase_combo.clear()
            self.purchase_combo.addItem("", "")
            for p in purchases:
                self.purchase_combo.addItem(f"PO-{p.get('id')} - {p.get('total_amount', 0)}", p)
            if self.payment and self.payment.get('po_id'):
                for i in range(self.purchase_combo.count()):
                    data = self.purchase_combo.itemData(i)
                    if data and data.get('id') == self.payment.get('po_id'):
                        self.purchase_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            print(f"加载采购单失败: {e}")

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("编辑供应商付款" if self.is_edit else "新建供应商付款")
        self.setMinimumSize(700, 600)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout()
        basic_layout.setSpacing(10)

        self.supplier_combo = QComboBox()
        self.supplier_combo.setFixedHeight(35)
        self.supplier_combo.currentIndexChanged.connect(self.load_purchases)
        basic_layout.addRow("供应商:", self.supplier_combo)

        self.purchase_combo = QComboBox()
        self.purchase_combo.setFixedHeight(35)
        basic_layout.addRow("采购单:", self.purchase_combo)

        self.payment_method_combo = QComboBox()
        self.payment_method_combo.setFixedHeight(35)
        self.payment_method_combo.addItems(["银行转账", "现金", "支票", "其他"])
        basic_layout.addRow("付款方式:", self.payment_method_combo)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        stages_group = QGroupBox("付款阶段管理")
        stages_layout = QVBoxLayout()

        self.stages_table = QTableWidget()
        self.stages_table.setColumnCount(5)
        self.stages_table.setHorizontalHeaderLabels(["阶段名称", "应付金额", "已付金额", "状态", "操作"])
        self.stages_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.stages_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.stages_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.stages_table.setMaximumHeight(200)
        stages_layout.addWidget(self.stages_table)

        add_stage_layout = QHBoxLayout()
        add_stage_layout.addStretch()

        add_deposit_btn = QPushButton("+ 添加定金")
        add_deposit_btn.clicked.connect(lambda: self.add_stage('deposit'))
        add_deposit_btn.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #d97706; }
        """)
        add_stage_layout.addWidget(add_deposit_btn)

        add_balance_btn = QPushButton("+ 添加尾款")
        add_balance_btn.clicked.connect(lambda: self.add_stage('balance'))
        add_balance_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        add_stage_layout.addWidget(add_balance_btn)
        stages_layout.addLayout(add_stage_layout)

        summary_layout = QHBoxLayout()
        summary_layout.addStretch()
        self.total_label = QLabel("总金额: 0.00")
        self.total_label.setStyleSheet("font-weight: bold; color: #374151;")
        summary_layout.addWidget(self.total_label)
        summary_layout.addSpacing(20)
        self.paid_label = QLabel("已付: 0.00")
        self.paid_label.setStyleSheet("font-weight: bold; color: #10b981;")
        summary_layout.addWidget(self.paid_label)
        summary_layout.addSpacing(20)
        self.unpaid_label = QLabel("未付: 0.00")
        self.unpaid_label.setStyleSheet("font-weight: bold; color: #ef4444;")
        summary_layout.addWidget(self.unpaid_label)
        stages_layout.addLayout(summary_layout)
        stages_group.setLayout(stages_layout)
        layout.addWidget(stages_group)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_payment)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        buttons_layout.addWidget(save_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        if self.payment:
            method_map = {"银行转账": 0, "现金": 1, "支票": 2, "其他": 3}
            self.payment_method_combo.setCurrentIndex(method_map.get(self.payment.get('payment_method', '银行转账'), 0))

    def add_stage(self, stage_type):
        """添加付款阶段"""
        dialog = SupplierPaymentStageDialog(self, stage_type, len(self.stages))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            stage_data = dialog.get_stage_data()
            self.stages.append(stage_data)
            self.refresh_stages_table()

    def edit_stage(self, index):
        """编辑付款阶段"""
        if index < 0 or index >= len(self.stages):
            return
        dialog = SupplierPaymentStageDialog(self, self.stages[index].get('stage_type', 'balance'), index, self.stages[index])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.stages[index] = dialog.get_stage_data()
            self.refresh_stages_table()

    def delete_stage(self, index):
        """删除付款阶段"""
        if index < 0 or index >= len(self.stages):
            return
        reply = QMessageBox.question(self, "确认", f"确定要删除阶段 '{self.stages[index].get('stage_name')}' 吗？")
        if reply == QMessageBox.StandardButton.Yes:
            self.stages.pop(index)
            self.refresh_stages_table()

    def refresh_stages_table(self):
        """刷新阶段表格"""
        self.stages_table.setRowCount(len(self.stages))
        status_map = {1: "待付", 2: "部分付", 3: "已付清"}
        total = 0
        paid = 0
        for row, stage in enumerate(self.stages):
            self.stages_table.setItem(row, 0, QTableWidgetItem(stage.get('stage_name', '')))
            amount = stage.get('amount', 0) or 0
            total += float(amount)
            self.stages_table.setItem(row, 1, QTableWidgetItem(f"{float(amount):,.2f}"))
            stage_paid = stage.get('paid_amount', 0) or 0
            paid += float(stage_paid)
            self.stages_table.setItem(row, 2, QTableWidgetItem(f"{float(stage_paid):,.2f}"))
            status = stage.get('status', 1)
            self.stages_table.setItem(row, 3, QTableWidgetItem(status_map.get(status, "未知")))
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0, 0, 0, 0)
            edit_btn = QPushButton("编辑")
            edit_btn.setFixedWidth(50)
            edit_btn.clicked.connect(lambda _, r=row: self.edit_stage(r))
            btn_layout.addWidget(edit_btn)
            del_btn = QPushButton("删除")
            del_btn.setFixedWidth(50)
            del_btn.setStyleSheet("color: #ef4444;")
            del_btn.clicked.connect(lambda _, r=row: self.delete_stage(r))
            btn_layout.addWidget(del_btn)
            btn_widget.setLayout(btn_layout)
            self.stages_table.setCellWidget(row, 4, btn_widget)
        unpaid = total - paid
        self.total_label.setText(f"总金额: {total:,.2f}")
        self.paid_label.setText(f"已付: {paid:,.2f}")
        self.unpaid_label.setText(f"未付: {unpaid:,.2f}")

    def save_payment(self):
        """保存供应商付款"""
        supplier_id = self.supplier_combo.currentData()
        purchase = self.purchase_combo.currentData()
        if not supplier_id:
            QMessageBox.warning(self, "警告", "请选择供应商")
            return
        if not purchase:
            QMessageBox.warning(self, "警告", "请选择采购单")
            return
        if not self.stages:
            QMessageBox.warning(self, "警告", "请至少添加一个付款阶段")
            return
        stages_data = [
            {
                'id': stage.get('id'),
                'stage_type': stage.get('stage_type'),
                'stage_name': stage.get('stage_name'),
                'amount': stage.get('amount'),
                'paid_amount': stage.get('paid_amount', 0),
                'status': stage.get('status', 1),
                'payment_date': stage.get('payment_date'),
                'payment_proof': stage.get('payment_proof'),
                'remark': stage.get('remark')
            }
            for stage in self.stages
        ]
        payment_data = {
            "dept_id": self.dept_id,
            "supplier_id": supplier_id,
            "po_id": purchase.get('id'),
            "payment_method": self.payment_method_combo.currentText(),
            "stages": stages_data,
            "remark": ""
        }
        try:
            if self.is_edit:
                self.api_client.update_supplier_payment(self.payment.get('id'), payment_data)
            else:
                self.api_client.create_supplier_payment(payment_data)
            QMessageBox.information(self, "成功", "付款记录已保存")
            self.accept()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")


class SupplierPaymentStageDialog(QDialog):
    """
    付款阶段编辑对话框
    
    功能：
    - 添加/编辑付款阶段
    - 自动根据已付金额计算状态
    
    构造参数：
    - parent: QWidget, 父窗口
    - stage_type: str, 阶段类型 'deposit' 或 'balance'
    - index: int, 阶段索引
    - stage_data: dict, 阶段数据（编辑模式），None 表示新建
    """
    
    def __init__(self, parent, stage_type, index, stage_data=None):
        super().__init__(parent)
        self.stage_type = stage_type
        self.index = index
        self.stage_data = stage_data or {}
        self.is_edit = stage_data is not None
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        type_name = "定金" if self.stage_type == 'deposit' else f"尾款{self.index}"
        self.setWindowTitle(f"编辑{type_name}" if self.is_edit else f"添加{type_name}")
        self.setFixedSize(400, 350)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setFixedHeight(35)
        default_name = self.stage_data.get('stage_name', '')
        if not default_name:
            default_name = "定金" if self.stage_type == 'deposit' else f"尾款{self.index + 1}"
        self.name_input.setText(default_name)
        form_layout.addRow("阶段名称:", self.name_input)

        self.amount_input = QLineEdit()
        self.amount_input.setFixedHeight(35)
        self.amount_input.setText(str(self.stage_data.get('amount', '')))
        form_layout.addRow("应付金额:", self.amount_input)

        self.paid_input = QLineEdit()
        self.paid_input.setFixedHeight(35)
        self.paid_input.setText(str(self.stage_data.get('paid_amount', '0')))
        form_layout.addRow("已付金额:", self.paid_input)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setFixedHeight(35)
        payment_date = self.stage_data.get('payment_date')
        if payment_date:
            self.date_input.setDate(QDate.fromString(str(payment_date)[:10], "yyyy-MM-dd"))
        else:
            self.date_input.setDate(QDate.currentDate())
        form_layout.addRow("付款日期:", self.date_input)

        self.remark_input = QTextEdit()
        self.remark_input.setFixedHeight(60)
        self.remark_input.setPlainText(self.stage_data.get('remark', ''))
        form_layout.addRow("备注:", self.remark_input)

        layout.addLayout(form_layout)
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
        """)
        buttons_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
        """)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def get_stage_data(self):
        """获取阶段数据"""
        amount = float(self.amount_input.text() or 0)
        paid = float(self.paid_input.text() or 0)
        status = 1
        if paid >= amount and amount > 0:
            status = 3
        elif paid > 0:
            status = 2
        return {
            'id': self.stage_data.get('id'),
            'stage_type': self.stage_type,
            'stage_name': self.name_input.text(),
            'amount': amount,
            'paid_amount': paid,
            'status': status,
            'payment_date': self.date_input.date().toString("yyyy-MM-dd"),
            'remark': self.remark_input.toPlainText()
        }