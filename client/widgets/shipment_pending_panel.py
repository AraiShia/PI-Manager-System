from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTableWidget, QTableWidgetItem, QCheckBox, QLabel,
                               QHeaderView, QAbstractItemView, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class ShipmentPendingPanel(QWidget):
    """待出货队列面板（可折叠）"""
    items_confirmed = Signal(list)  # 确认出货时发出
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.is_collapsed = False
        self._setup_ui()
        self.load_data()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 折叠控制按钮
        self.toggle_btn = QPushButton("◀")
        self.toggle_btn.setFixedWidth(30)
        self.toggle_btn.clicked.connect(self._toggle_collapse)
        self.toggle_btn.setStyleSheet("border: none; background: transparent; font-size: 14px;")
        layout.addWidget(self.toggle_btn)
        
        # 展开内容区
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题栏
        title_layout = QHBoxLayout()
        self.title_label = QLabel("▼待出货队列")
        self.title_label.setFont(QFont("", 10, QFont.Bold))
        self.count_label = QLabel("[待出货: 0]")
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.count_label)
        title_layout.addStretch()
        content_layout.addLayout(title_layout)
        
        # 产品列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["", "PI号", "产品", "客户", "数量"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        content_layout.addWidget(self.table)
        
        # 确认出货按钮
        confirm_btn = QPushButton("+ 确认出货")
        confirm_btn.setStyleSheet("background-color: #10b981; color: white; padding: 8px;")
        confirm_btn.clicked.connect(self._on_confirm)
        content_layout.addWidget(confirm_btn)
        
        layout.addWidget(self.content_widget)
    
    def _toggle_collapse(self):
        """切换折叠状态"""
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.content_widget.hide()
            self.toggle_btn.setText("▶")
            self.toggle_btn.setToolTip("点击展开待出货队列")
            # 折叠时收缩到最小宽度，让右侧汇总表占满空间
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            self.setFixedWidth(30)
        else:
            self.content_widget.show()
            self.toggle_btn.setText("◀")
            self.toggle_btn.setToolTip("点击折叠待出货队列")
            # 展开时恢复弹性宽度
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            self.setMinimumWidth(200)
            self.setMaximumWidth(16777215)  # QWIDGETSIZE_MAX
    
    def load_data(self):
        """加载待出货队列数据"""
        try:
            items = self.api_client.get("/pending-shipment") or []
        except Exception:
            items = []
        
        self.table.setRowCount(len(items))
        for i, item in enumerate(items):
            chk = QCheckBox()
            chk.setProperty("item_id", item.get('id'))
            self.table.setCellWidget(i, 0, chk)
            
            pi_item = QTableWidgetItem(item.get('pi_no', ''))
            pi_item.setData(Qt.UserRole, item.get('id'))
            self.table.setItem(i, 1, pi_item)
            
            self.table.setItem(i, 2, QTableWidgetItem(item.get('product_name', '')))
            self.table.setItem(i, 3, QTableWidgetItem(item.get('customer_name', '')))
            self.table.setItem(i, 4, QTableWidgetItem(str(item.get('quantity', 0))))
        
        self.count_label.setText(f"[待出货: {len(items)}]")
    
    def _on_confirm(self):
        """确认出货"""
        selected_ids = []
        for i in range(self.table.rowCount()):
            chk = self.table.cellWidget(i, 0)
            if chk and chk.isChecked():
                item_id = chk.property("item_id") or int(self.table.item(i, 1).data(Qt.UserRole))
                if item_id:
                    selected_ids.append(int(item_id))
        
        if not selected_ids:
            return
        
        # 先调用确认API
        try:
            resp = self.api_client.post("/pending-shipment/confirm", {
                "item_ids": selected_ids
            })
            if resp and resp.get('success'):
                self.items_confirmed.emit(selected_ids)
                self.load_data()
        except Exception as e:
            print(f"确认出货失败: {e}")
