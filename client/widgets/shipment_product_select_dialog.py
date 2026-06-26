from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QCheckBox, QAbstractItemView, QLabel, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class ShipmentProductSelectDialog(QDialog):
    """商品选择对话框"""
    def __init__(self, api_client, pi_ids: list[int], parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.pi_ids = pi_ids
        self._setup_ui()
        self.load_products()
    
    def _setup_ui(self):
        self.setWindowTitle("选择出货商品")
        self.setMinimumSize(900, 500)
        layout = QVBoxLayout(self)
        
        # 说明
        info = QLabel("勾选要出货的商品（可跨PI选择）")
        info.setFont(QFont("", 9))
        layout.addWidget(info)
        
        # 商品列表
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "", "PI号", "产品名称", "型号", "客户", "订单数量", "剩余数量"
        ])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        # 全选/反选
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self._select_all)
        deselect_btn = QPushButton("反选")
        deselect_btn.clicked.connect(self._deselect_all)
        select_layout.addWidget(select_all_btn)
        select_layout.addWidget(deselect_btn)
        select_layout.addStretch()
        layout.addLayout(select_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        confirm_btn = QPushButton("确认加入待出货队列")
        confirm_btn.setStyleSheet("background-color: #10b981; color: white; padding: 8px 20px;")
        confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)
    
    def load_products(self):
        """加载所选PI下的产品"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[出货选择Dialog] 开始加载产品, pi_ids={self.pi_ids}")
        
        products = []
        for pi_id in self.pi_ids:
            try:
                logger.info(f"[出货选择Dialog] 获取PI {pi_id} 的订单项...")
                items = self.api_client.get(f"/pi/{pi_id}/items") or []
                logger.info(f"[出货选择Dialog] PI {pi_id} 返回 {len(items)} 个订单项")
                products.extend(items)
            except Exception as e:
                logger.error(f"[出货选择Dialog] 获取PI {pi_id} 失败: {e}")
                continue
        
        logger.info(f"[出货选择Dialog] 共加载 {len(products)} 个产品")
        self.table.setRowCount(len(products))
        
        self.table.setRowCount(len(products))
        for i, p in enumerate(products):
            chk = QCheckBox()
            chk.setProperty("pi_item_id", p.get('id'))
            self.table.setCellWidget(i, 0, chk)
            
            # 存储pi_item_id用于后续处理
            id_item = QTableWidgetItem(str(p.get('id', '')))
            id_item.setData(Qt.UserRole, p.get('id'))
            self.table.setItem(i, 0, id_item)
            
            self.table.setItem(i, 1, QTableWidgetItem(p.get('pi_no', '')))
            self.table.setItem(i, 2, QTableWidgetItem(p.get('product_name', '')))
            self.table.setItem(i, 3, QTableWidgetItem(p.get('model', '')))
            self.table.setItem(i, 4, QTableWidgetItem(p.get('customer_name', '')))
            
            quantity = p.get('quantity', 0) or 0
            shipped = p.get('shipped_quantity', 0) or 0
            remain = float(quantity) - float(shipped)
            
            self.table.setItem(i, 5, QTableWidgetItem(str(int(quantity))))
            self.table.setItem(i, 6, QTableWidgetItem(f"{remain:.2f}"))
    
    def _select_all(self):
        for i in range(self.table.rowCount()):
            chk = self.table.cellWidget(i, 0)
            if chk:
                chk.setChecked(True)
    
    def _deselect_all(self):
        for i in range(self.table.rowCount()):
            chk = self.table.cellWidget(i, 0)
            if chk:
                chk.setChecked(False)
    
    def _on_confirm(self):
        """确认选择"""
        selected_ids = []
        for i in range(self.table.rowCount()):
            chk = self.table.cellWidget(i, 0)
            if chk and chk.isChecked():
                item_id = chk.property("pi_item_id") or int(self.table.item(i, 0).data(Qt.UserRole))
                if item_id:
                    selected_ids.append(int(item_id))
        
        if not selected_ids:
            QMessageBox.warning(self, "提示", "请至少选择一个商品")
            return
        
        # 调用API添加到待出货队列
        try:
            resp = self.api_client.post("/pending-shipment", {
                "pi_item_ids": selected_ids,
                "user_id": "current_user"
            })
            
            if resp and resp.get('success'):
                count = resp.get('count', len(selected_ids))
                QMessageBox.information(self, "成功", f"已添加 {count} 个商品到待出货队列")
                self.accept()
            else:
                QMessageBox.warning(self, "错误", "添加失败，请重试")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"添加失败: {str(e)}")
