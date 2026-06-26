from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
    QMessageBox, QComboBox, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont


class PaymentDialog(QDialog):
    def __init__(self, api_client, pi_id, pi_no=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.pi_id = pi_id
        self.pi_no = pi_no or str(pi_id)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        self.setWindowTitle(f"往来款管理 - {self.pi_no}")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout()

        title = QLabel(f"往来款管理 - PI: {self.pi_no}")
        title.setFont(QFont("", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        customer_label = QLabel("客户付款记录")
        customer_label.setFont(QFont("", 10, QFont.Weight.Bold))
        layout.addWidget(customer_label)

        self.customer_table = QTableWidget()
        self.customer_table.setColumnCount(5)
        self.customer_table.setHorizontalHeaderLabels(["日期", "金额", "类型", "状态", "操作"])
        self.customer_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.customer_table.setAlternatingRowColors(True)
        layout.addWidget(self.customer_table)

        add_customer_btn = QPushButton("+ 添加客户付款")
        add_customer_btn.clicked.connect(lambda: self.add_payment("customer"))
        layout.addWidget(add_customer_btn)

        supplier_label = QLabel("供应商付款记录")
        supplier_label.setFont(QFont("", 10, QFont.Weight.Bold))
        layout.addWidget(supplier_label)

        self.supplier_table = QTableWidget()
        self.supplier_table.setColumnCount(5)
        self.supplier_table.setHorizontalHeaderLabels(["日期", "金额", "类型", "状态", "操作"])
        self.supplier_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.supplier_table.setAlternatingRowColors(True)
        layout.addWidget(self.supplier_table)

        add_supplier_btn = QPushButton("+ 添加供应商付款")
        add_supplier_btn.clicked.connect(lambda: self.add_payment("supplier"))
        layout.addWidget(add_supplier_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def load_data(self):
        try:
            customer_payments = self.api_client.get_customer_payments_by_pi(self.pi_id) or []
            self.populate_table(self.customer_table, customer_payments)

            supplier_payments = self.api_client.get_supplier_payments_by_pi(self.pi_id) or []
            self.populate_table(self.supplier_table, supplier_payments)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载数据失败: {e}")

    def populate_table(self, table, payments):
        table.setRowCount(len(payments))
        for i, payment in enumerate(payments):
            table.setItem(i, 0, QTableWidgetItem(str(payment.get('payment_date', ''))))
            table.setItem(i, 1, QTableWidgetItem(f"¥{payment.get('amount', 0):.2f}"))
            table.setItem(i, 2, QTableWidgetItem(payment.get('payment_type', '')))
            table.setItem(i, 3, QTableWidgetItem(payment.get('status', '')))

            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(lambda checked, p=payment: self.delete_payment(p))
            table.setCellWidget(i, 4, delete_btn)

    def add_payment(self, payment_type):
        from widgets.add_payment_dialog import AddPaymentDialog
        dialog = AddPaymentDialog(self.api_client, self.pi_id, payment_type, self)
        if dialog.exec():
            self.load_data()

    def delete_payment(self, payment):
        reply = QMessageBox.question(
            self, "确认删除", "确定删除这条付款记录吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if payment.get('payment_type') == 'customer':
                    self.api_client.delete_customer_payment(payment['id'])
                else:
                    self.api_client.delete_supplier_payment(payment['id'])
                self.load_data()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败: {e}")
