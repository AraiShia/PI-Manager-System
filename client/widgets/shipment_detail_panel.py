from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QAbstractItemView, QLabel, QGroupBox, QFormLayout,
                               QLineEdit)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class ShipmentDetailPanel(QWidget):
    """出货详情面板（模式二）"""
    return_clicked = Signal()
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.shipment_id = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 返回按钮
        return_layout = QHBoxLayout()
        self.return_btn = QPushButton("← 返回出货单列表")
        self.return_btn.setStyleSheet("background-color: #f3f4f6; padding: 8px; border-radius: 4px;")
        self.return_btn.clicked.connect(self.return_clicked.emit)
        return_layout.addWidget(self.return_btn)
        return_layout.addStretch()
        layout.addLayout(return_layout)
        
        # 标题区（重要信息）
        self.title_group = QGroupBox("出货信息")
        title_layout = QFormLayout()
        
        self.shipment_no_label = QLabel()
        self.shipment_no_label.setFont(QFont("", 12, QFont.Bold))
        title_layout.addRow("出货单号:", self.shipment_no_label)
        
        self.ci_input = QLineEdit()
        self.ci_input.setPlaceholderText("点击编辑CI号（仅可修改一次）")
        self.ci_locked = False
        self.ci_original = ""
        title_layout.addRow("CI号:", self.ci_input)
        
        self.customs_input = QLineEdit()
        self.customs_input.setPlaceholderText("报关单号")
        title_layout.addRow("报关单:", self.customs_input)
        
        self.pi_nos_label = QLabel()
        title_layout.addRow("PI号:", self.pi_nos_label)
        
        self.summary_label = QLabel()
        self.summary_label.setFont(QFont("", 9))
        title_layout.addRow("汇总:", self.summary_label)
        
        self.title_group.setLayout(title_layout)
        layout.addWidget(self.title_group)
        
        # 出货明细表格（19列）
        detail_label = QLabel("出货明细")
        detail_label.setFont(QFont("", 10, QFont.Bold))
        layout.addWidget(detail_label)
        
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(19)
        headers = [
            "客户编号", "OE号", "图片", "订单数量", "单价", "总金额",
            "总箱数", "总体积", "总重量", "出货数量", "单价", "金额",
            "箱数", "总体积", "重量", "总重量", "剩余数量", "剩余箱数", "剩余体积"
        ]
        self.detail_table.setHorizontalHeaderLabels(headers)
        self.detail_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.detail_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        layout.addWidget(self.detail_table)
        
        # Button区
        btn_layout = QHBoxLayout()
        for text in ["查看PL表", "查看CI表", "导出数据"]:
            btn = QPushButton(text)
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)
    
    def load_shipment(self, shipment_id):
        """加载出货单详情"""
        self.shipment_id = shipment_id
        
        try:
            data = self.api_client.get(f"/shipments/{shipment_id}")
        except Exception:
            data = None
        
        if not data:
            return
        
        self.shipment_no_label.setText(data.get('shipment_no', ''))
        
        ci_no = data.get('ci_no', '')
        self.ci_input.setText(ci_no)
        self.ci_original = ci_no
        
        # CI号锁定状态
        self.ci_locked = data.get('ci_locked', False)
        if self.ci_locked:
            self.ci_input.setReadOnly(True)
            self.ci_input.setStyleSheet("background-color: #f3f4f6;")
        else:
            self.ci_input.textChanged.connect(self._on_ci_changed)
        
        self.customs_input.setText(data.get('customs_no', ''))
        self.pi_nos_label.setText(data.get('pi_nos', ''))
        
        # 汇总信息
        total_cartons = data.get('total_cartons', 0) or 0
        total_weight = data.get('total_gross_weight', 0) or 0
        total_quantity = data.get('total_quantity', 0) or 0
        total_amount = data.get('total_amount', 0) or 0
        
        self.summary_label.setText(
            f"总箱数: {int(total_cartons)}  "
            f"总重量: {float(total_weight):.2f}kg  "
            f"总数量: {int(total_quantity)}  "
            f"总金额: ¥{float(total_amount):.2f}"
        )
        
        # 出货明细
        items = data.get('items', [])
        self.detail_table.setRowCount(len(items))
        
        col_keys = [
            'customer_code', 'oe_number', 'image_url', 'quantity', 'price',
            'total_amount', 'cartons', 'volume', 'weight',
            'ship_quantity', 'ship_price', 'ship_amount', 'ship_cartons',
            'ship_volume', 'ship_weight', 'total_ship_weight',
            'remain_quantity', 'remain_cartons', 'remain_volume'
        ]
        
        for i, item in enumerate(items):
            for col, key in enumerate(col_keys):
                val = item.get(key, '')
                table_item = QTableWidgetItem(str(val) if val is not None else '')
                self.detail_table.setItem(i, col, table_item)
    
    def _on_ci_changed(self):
        """CI号修改处理"""
        if self.ci_locked:
            return
        # CI号修改逻辑由保存按钮触发，这里只做UI更新提示
