# -*- coding: utf-8 -*-
"""更换供应商对话框"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QDoubleSpinBox, QPushButton, QFormLayout, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt


class SupplierChangeDialog(QDialog):
    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.item = item.copy()
        self.setWindowTitle("更换供应商")
        self.setMinimumSize(600, 500)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.supplier_name_edit = QLineEdit(self.item.get("supplier_name", ""))
        self.shop_url_edit = QLineEdit(self.item.get("shop_url", ""))
        self.factory_code_edit = QLineEdit(self.item.get("factory_code", ""))
        self.brand_edit = QLineEdit(self.item.get("brand", ""))

        self.purchase_price_spin = QDoubleSpinBox()
        self.purchase_price_spin.setRange(0, 99999999)
        self.purchase_price_spin.setDecimals(4)
        self.purchase_price_spin.setValue(float(self.item.get("purchase_price", 0) or 0))

        self.factory_deposit_spin = QDoubleSpinBox()
        self.factory_deposit_spin.setRange(0, 99999999)
        self.factory_deposit_spin.setDecimals(4)
        self.factory_deposit_spin.setValue(float(self.item.get("factory_deposit", 0) or 0))

        self.factory_balance_spin = QDoubleSpinBox()
        self.factory_balance_spin.setRange(0, 99999999)
        self.factory_balance_spin.setDecimals(4)
        self.factory_balance_spin.setValue(float(self.item.get("factory_balance", 0) or 0))

        self.invoice_status_combo = QComboBox()
        self.invoice_status_combo.addItems(["增票", "普票", "不开票"])
        current_invoice = self.item.get("invoice_status", "")
        idx = self.invoice_status_combo.findText(current_invoice)
        if idx >= 0:
            self.invoice_status_combo.setCurrentIndex(idx)

        form.addRow("工厂简称:", self.supplier_name_edit)
        form.addRow("店铺链接:", self.shop_url_edit)
        form.addRow("工厂编号:", self.factory_code_edit)
        form.addRow("品牌:", self.brand_edit)
        form.addRow("采购价格:", self.purchase_price_spin)
        form.addRow("工厂订金:", self.factory_deposit_spin)
        form.addRow("工厂尾款:", self.factory_balance_spin)
        form.addRow("开票情况:", self.invoice_status_combo)

        layout.addLayout(form)

        # 提示信息
        hint = QLabel("保存后将删除原采购单并重新生成新采购单。")
        hint.setStyleSheet("color: #6b7280; font-size: 12px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet("background-color: #10b981; color: white; padding: 8px 16px; border-radius: 4px;")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _on_save(self):
        reply = QMessageBox.question(
            self,
            "确认更换供应商",
            "确定要按以上信息更换供应商并重新生成采购单吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.result_data = {
            "supplier_name": self.supplier_name_edit.text().strip(),
            "shop_url": self.shop_url_edit.text().strip(),
            "factory_code": self.factory_code_edit.text().strip(),
            "brand": self.brand_edit.text().strip(),
            "purchase_price": self.purchase_price_spin.value(),
            "factory_deposit": self.factory_deposit_spin.value(),
            "factory_balance": self.factory_balance_spin.value(),
            "invoice_status": self.invoice_status_combo.currentText(),
        }
        self.accept()

    def get_data(self):
        return getattr(self, "result_data", {})
