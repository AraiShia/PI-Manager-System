# -*- coding: utf-8 -*-
"""
CustomerPaymentDialog - 客户收款对话框
需求 #41：订单总表"添加付款"按钮弹出收款录入对话框

字段（全部可手工输入）：
- 收款日期、付款金额、手续费、到账金额、上传水单、付款方式、备注
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QMessageBox,
    QComboBox, QFileDialog, QDateTimeEdit
)
from PySide6.QtCore import Qt, QDateTime


class CustomerPaymentDialog(QDialog):
    """客户收款对话框"""

    def __init__(self, order: dict, api_client, parent=None):
        super().__init__(parent)
        self.order = order
        self.api = api_client
        self._water_path = None
        self.setWindowTitle("客户收款")
        self.setMinimumWidth(480)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)

        # PI 信息（只读）
        pi_no = self.order.get('pi_no', '-')
        total_amount = self.order.get('total_amount', 0) or 0
        currency = self.order.get('currency', 'USD')
        info_label = QLabel(f"PI: {pi_no}  |  总金额: {total_amount} {currency}")
        info_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addRow("", info_label)

        # 1. 收款日期 *
        self.payment_date_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.payment_date_edit.setCalendarPopup(True)
        self.payment_date_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        layout.addRow("收款日期 *:", self.payment_date_edit)

        # 2. 付款金额 *
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText(f"应收金额: {total_amount}")
        self.amount_input.textChanged.connect(self._on_amount_changed)
        layout.addRow("付款金额 *:", self.amount_input)

        # 3. 手续费
        self.fee_input = QLineEdit("0")
        self.fee_input.textChanged.connect(self._on_amount_changed)
        layout.addRow("手续费:", self.fee_input)

        # 4. 到账金额（自动计算：付款金额 - 手续费，也可手工修改）
        self.actual_input = QLineEdit()
        self.actual_input.setPlaceholderText("自动计算 = 付款金额 - 手续费")
        self.actual_input.setStyleSheet("background: #f9fafb;")
        layout.addRow("到账金额:", self.actual_input)

        # 5. 上传水单
        water_layout = QHBoxLayout()
        self.water_label = QLabel("未选择文件")
        self.water_label.setStyleSheet("color: #9ca3af;")
        water_btn = QPushButton("选择文件...")
        water_btn.setFixedWidth(100)
        water_btn.clicked.connect(self._on_select_water)
        clear_btn = QPushButton("清除")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(self._on_clear_water)
        water_layout.addWidget(self.water_label, stretch=1)
        water_layout.addWidget(water_btn)
        water_layout.addWidget(clear_btn)
        layout.addRow("上传水单:", water_layout)

        # 6. 付款方式
        self.method_combo = QComboBox()
        self.method_combo.addItems(["银行转账", "现金", "支票", "其他"])
        layout.addRow("付款方式:", self.method_combo)

        # 7. 备注
        self.remark_input = QLineEdit()
        self.remark_input.setPlaceholderText("可选")
        layout.addRow("备注:", self.remark_input)

        # 按钮行
        btns = QHBoxLayout()
        btns.addStretch()
        self.ok_btn = QPushButton("确认收款")
        self.ok_btn.setFixedWidth(110)
        self.ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.ok_btn)
        btns.addWidget(cancel_btn)
        layout.addRow("", btns)

        self.setLayout(layout)

    def _on_amount_changed(self):
        """付款金额或手续费变化时自动计算到账金额"""
        try:
            amount = float(self.amount_input.text().strip() or "0")
            fee = float(self.fee_input.text().strip() or "0")
            actual = amount - fee
            if amount > 0:
                self.actual_input.setText(f"{actual:.2f}")
        except ValueError:
            pass

    def _on_select_water(self):
        """选择水单图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择水单图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*)"
        )
        if file_path:
            self._water_path = file_path
            self.water_label.setText(os.path.basename(file_path))
            self.water_label.setStyleSheet("color: #059669;")

    def _on_clear_water(self):
        """清除水单"""
        self._water_path = None
        self.water_label.setText("未选择文件")
        self.water_label.setStyleSheet("color: #9ca3af;")

    def _on_ok(self):
        """验证并提交"""
        amount_text = self.amount_input.text().strip()
        if not amount_text:
            QMessageBox.warning(self, "提示", "请输入付款金额")
            return
        try:
            amount = float(amount_text)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "提示", "付款金额必须大于 0")
            return

        try:
            fee = float(self.fee_input.text().strip() or "0")
            if fee < 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "提示", "手续费必须 >= 0")
            return

        # 调用 API 创建收款记录
        data = self.get_data()
        try:
            result = self.api.create_customer_payment(data)
            if result and result.get('id'):
                QMessageBox.information(
                    self, "成功",
                    f"收款记录已创建！\n收据编号: {result.get('receipt_no', '-')}"
                )
                self.accept()
            else:
                QMessageBox.warning(self, "失败", "创建收款记录失败，请重试")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建收款记录失败:\n{e}")

    def get_data(self) -> dict:
        """返回表单数据，用于 API 提交"""
        payment_date = self.payment_date_edit.dateTime().toPython()
        amount = float(self.amount_input.text().strip() or "0")
        handling_fee = float(self.fee_input.text().strip() or "0")
        actual_text = self.actual_input.text().strip()

        # order dict 中 pi_id 存储在 "id" 字段
        return {
            "dept_id": "01",
            "pi_id": self.order.get('id'),           # 修正: 用 'id' 而非 'pi_id'
            "customer_id": self.order.get('customer_id'),
            "amount": amount,
            "handling_fee": handling_fee if handling_fee else None,
            "actual_amount": float(actual_text) if actual_text else None,
            "payment_date": payment_date.isoformat(),
            "currency": self.order.get('currency', 'USD'),
            "water_image": self._water_path,
            "payment_method": self.method_combo.currentText(),
            "remark": self.remark_input.text().strip() or None,
        }
