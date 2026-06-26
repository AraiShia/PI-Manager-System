"""
InboundDialog - 单品入库对话框
需求 #40：右键"入库该产品"弹出对话框，用户输入入库数量后提交
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QMessageBox
)


class InboundDialog(QDialog):
    """单品入库对话框"""
    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("入库")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)

        # 产品名称（只读）
        self.product_name_label = QLabel(self.item.get("product_name", ""))
        layout.addRow("产品名称:", self.product_name_label)

        # 采购数量（只读）
        purchase_qty = self.item.get("purchase_quantity", self.item.get("quantity", ""))
        self.purchase_qty_label = QLabel(str(purchase_qty))
        layout.addRow("采购数量:", self.purchase_qty_label)

        # 入库数量（可编辑）
        self.qty_input = QLineEdit(str(purchase_qty))
        layout.addRow("入库数量 *:", self.qty_input)

        # 验收人
        self.inspector_input = QLineEdit()
        layout.addRow("验收人:", self.inspector_input)

        # 备注
        self.remark_input = QLineEdit()
        layout.addRow("备注:", self.remark_input)

        # 按钮行
        btns = QHBoxLayout()
        self.ok_btn = QPushButton("确定入库")
        self.ok_btn.setFixedWidth(100)
        self.ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(self.ok_btn)
        btns.addWidget(cancel_btn)
        layout.addRow("", btns)

        self.setLayout(layout)

    def _on_ok(self):
        """验证并接受"""
        try:
            qty = float(self.qty_input.text().strip())
            purchase_qty = float(self.purchase_qty_label.text())
            if qty <= 0:
                raise ValueError()
            if qty > purchase_qty:
                QMessageBox.warning(self, "警告", "入库数量不能大于采购数量")
                return
            self.accept()
        except ValueError:
            QMessageBox.warning(self, "警告", "请输入有效的入库数量（大于 0）")

    def get_data(self) -> dict:
        """返回入库数据"""
        return {
            "quantity": float(self.qty_input.text().strip()),
            "inspector": self.inspector_input.text().strip(),
            "remark": self.remark_input.text().strip(),
        }