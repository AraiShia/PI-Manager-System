"""
BatchInboundDialog - 批量入库对话框
需求 #40：模式二"全部入库"按钮，弹出对话框列出所有产品，用户可批量修改入库数量
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QTableWidget,
    QTableWidgetItem, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt


class BatchInboundDialog(QDialog):
    """批量入库对话框"""
    COL_NAME = 0
    COL_PURCHASE_QTY = 1
    COL_INBOUND_QTY = 2

    def __init__(self, items: list[dict], parent=None):
        super().__init__(parent)
        self.items = items
        self.setWindowTitle("批量入库")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        # 标题信息
        main_layout.addWidget(QLabel(f"共 {len(self.items)} 个产品待入库"))

        # 验收人输入
        inspector_layout = QHBoxLayout()
        inspector_layout.addWidget(QLabel("验收人:"))
        self.inspector_input = QLineEdit()
        inspector_layout.addWidget(self.inspector_input)
        inspector_layout.addStretch()
        main_layout.addLayout(inspector_layout)

        # 产品表格（只读名称 + 采购数量，可编辑入库数量）
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["产品名称", "采购数量", "入库数量"])
        self.table.setRowCount(len(self.items))
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        for i, item in enumerate(self.items):
            name = QTableWidgetItem(item.get("product_name", ""))
            name.setFlags(name.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, self.COL_NAME, name)

            purchase_qty = item.get("purchase_quantity", item.get("quantity", ""))
            pqty_item = QTableWidgetItem(str(purchase_qty))
            pqty_item.setFlags(pqty_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, self.COL_PURCHASE_QTY, pqty_item)

            inbound_item = QTableWidgetItem(str(purchase_qty))
            self.table.setItem(i, self.COL_INBOUND_QTY, inbound_item)

        self.table.resizeColumnsToContents()
        main_layout.addWidget(self.table)

        # 按钮行
        btns = QHBoxLayout()
        ok_btn = QPushButton("确认入库")
        ok_btn.setFixedWidth(100)
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        main_layout.addLayout(btns)

        self.setLayout(main_layout)

    def _on_ok(self):
        """验证入库数量并接受"""
        for i in range(self.table.rowCount()):
            try:
                qty_text = self.table.item(i, self.COL_INBOUND_QTY).text().strip()
                qty = float(qty_text)
                if qty < 0:
                    raise ValueError()
            except ValueError:
                QMessageBox.warning(
                    self, "警告", f"第 {i + 1} 行入库数量无效（需为非负数字）"
                )
                return
        self.accept()

    def get_data(self) -> tuple[list[dict], str]:
        """返回 (入库条目列表, 验收人)"""
        entries = []
        for i, item in enumerate(self.items):
            entries.append({
                "pi_item_id": item.get("id"),
                "quantity": float(self.table.item(i, self.COL_INBOUND_QTY).text().strip()),
                "remark": "",
            })
        return entries, self.inspector_input.text().strip()