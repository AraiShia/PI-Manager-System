# -*- coding: utf-8 -*-
"""采购快照对话框"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFormLayout
from PySide6.QtCore import Qt


class PurchaseSnapshotDialog(QDialog):
    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("采购快照")
        self.setMinimumSize(500, 400)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        fields = [
            ("工厂简称", "supplier_name"),
            ("店铺链接", "shop_url"),
            ("工厂编号", "factory_code"),
            ("品牌", "brand"),
            ("采购价格", "purchase_price"),
            ("工厂订金", "factory_deposit"),
            ("工厂尾款", "factory_balance"),
            ("开票情况", "invoice_status"),
            ("采购单状态", "storage_status"),
            ("已采购数量", "purchase_quantity"),
            ("已入库数量", "stocked_qty"),
        ]

        for label, key in fields:
            value = self.item.get(key, "")
            if isinstance(value, (int, float)):
                value = str(value)
            form.addRow(label + ":", QLabel(value or "-"))

        layout.addLayout(form)
        btn = QPushButton("关闭")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
