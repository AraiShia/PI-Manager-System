from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                               QPushButton, QHeaderView, QAbstractItemView, QLabel)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class ShipmentSummaryPanel(QWidget):
    """出货汇总面板（模式一主表）"""
    record_double_clicked = Signal(int)  # 出货单ID
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self._setup_ui()
        self.load_data()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("出货单列表（双击记录进入详情）")
        title.setFont(QFont("", 11, QFont.Bold))
        layout.addWidget(title)
        
        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID", "出货单号", "CI号", "报关单", "PI号",
            "总箱数", "总重量", "总数量", "总金额", "操作"
        ])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)
    
    def load_data(self):
        """加载出货单汇总数据"""
        try:
            shipments = self.api_client.get("/shipments") or []
        except Exception:
            shipments = []
        
        self.table.setRowCount(len(shipments))
        for i, s in enumerate(shipments):
            id_item = QTableWidgetItem(str(s.get('id', '')))
            id_item.setData(Qt.UserRole, s.get('id'))
            self.table.setItem(i, 0, id_item)
            
            self.table.setItem(i, 1, QTableWidgetItem(s.get('shipment_no', '')))
            self.table.setItem(i, 2, QTableWidgetItem(s.get('ci_no', '')))
            self.table.setItem(i, 3, QTableWidgetItem(s.get('customs_no', '')))
            self.table.setItem(i, 4, QTableWidgetItem(s.get('pi_nos', '')))
            self.table.setItem(i, 5, QTableWidgetItem(str(s.get('total_cartons', 0))))
            self.table.setItem(i, 6, QTableWidgetItem(str(s.get('total_gross_weight', 0))))
            self.table.setItem(i, 7, QTableWidgetItem(str(int(s.get('total_quantity', 0)))))
            self.table.setItem(i, 8, QTableWidgetItem(str(s.get('total_amount', 0))))
            
            # 操作按钮
            edit_btn = QPushButton("编辑")
            edit_btn.clicked.connect(lambda _, sid=s.get('id'): self._edit_shipment(sid))
            self.table.setCellWidget(i, 9, edit_btn)
    
    def refresh_data(self):
        """刷新数据"""
        self.load_data()
    
    def _on_double_click(self, row, column):
        shipment_id = int(self.table.item(row, 0).text())
        self.record_double_clicked.emit(shipment_id)
    
    def _edit_shipment(self, shipment_id):
        self.record_double_clicked.emit(shipment_id)
