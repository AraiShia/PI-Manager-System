from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                               QAbstractItemView, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class ShipmentExportTab(QWidget):
    """导出数据Tab（CI/PL/自定义）"""
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.shipment_id = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 导出类型Tab
        self.tab_widget = QTabWidget()
        
        # CI表
        ci_widget = QWidget()
        ci_layout = QVBoxLayout(ci_widget)
        self.ci_table = QTableWidget()
        self.ci_table.setColumnCount(10)
        self.ci_table.setHorizontalHeaderLabels([
            "序号", "客户编号", "OE号", "产品描述", "数量",
            "单价", "总金额", "箱数", "重量", "体积"
        ])
        self.ci_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        ci_layout.addWidget(self.ci_table)
        self.tab_widget.addTab(ci_widget, "CI表")
        
        # PL表
        pl_widget = QWidget()
        pl_layout = QVBoxLayout(pl_widget)
        self.pl_table = QTableWidget()
        self.pl_table.setColumnCount(12)
        self.pl_table.setHorizontalHeaderLabels([
            "序号", "PI号", "客户编号", "OE号", "产品描述", "订单数量",
            "出货数量", "单价", "金额", "箱数", "重量", "体积"
        ])
        self.pl_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        pl_layout.addWidget(self.pl_table)
        self.tab_widget.addTab(pl_widget, "PL表")
        
        # 自定义数据
        custom_widget = QWidget()
        custom_layout = QVBoxLayout(custom_widget)
        self.custom_table = QTableWidget()
        custom_layout.addWidget(self.custom_table)
        self.tab_widget.addTab(custom_widget, "自定义")
        
        layout.addWidget(self.tab_widget)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        export_btn = QPushButton("导出Excel")
        export_btn.setStyleSheet("background-color: #10b981; color: white; padding: 8px 20px;")
        export_btn.clicked.connect(self._on_export_excel)
        btn_layout.addStretch()
        btn_layout.addWidget(export_btn)
        layout.addLayout(btn_layout)
    
    def set_shipment_data(self, shipment_id: int, data: dict = None):
        """设置出货单数据"""
        self.shipment_id = shipment_id
        
        if data is None:
            try:
                data = self.api_client.get(f"/shipments/{shipment_id}")
            except Exception:
                return
        
        if not data:
            return
        
        items = data.get('items', [])
        
        # 填充CI表
        self.ci_table.setRowCount(len(items))
        for i, item in enumerate(items):
            self.ci_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.ci_table.setItem(i, 1, QTableWidgetItem(item.get('customer_code', '')))
            self.ci_table.setItem(i, 2, QTableWidgetItem(item.get('oe_number', '')))
            self.ci_table.setItem(i, 3, QTableWidgetItem(item.get('product_name', '')))
            self.ci_table.setItem(i, 4, QTableWidgetItem(str(item.get('quantity', 0))))
            self.ci_table.setItem(i, 5, QTableWidgetItem(str(item.get('price', 0))))
            self.ci_table.setItem(i, 6, QTableWidgetItem(str(item.get('total_amount', 0))))
            self.ci_table.setItem(i, 7, QTableWidgetItem(str(item.get('cartons', 0))))
            self.ci_table.setItem(i, 8, QTableWidgetItem(str(item.get('weight', 0))))
            self.ci_table.setItem(i, 9, QTableWidgetItem(str(item.get('volume', 0))))
        
        # 填充PL表
        self.pl_table.setRowCount(len(items))
        for i, item in enumerate(items):
            self.pl_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.pl_table.setItem(i, 1, QTableWidgetItem(data.get('pi_nos', '').split(',')[0] if data.get('pi_nos') else ''))
            self.pl_table.setItem(i, 2, QTableWidgetItem(item.get('customer_code', '')))
            self.pl_table.setItem(i, 3, QTableWidgetItem(item.get('oe_number', '')))
            self.pl_table.setItem(i, 4, QTableWidgetItem(item.get('product_name', '')))
            self.pl_table.setItem(i, 5, QTableWidgetItem(str(item.get('quantity', 0))))
            self.pl_table.setItem(i, 6, QTableWidgetItem(str(item.get('ship_quantity', 0))))
            self.pl_table.setItem(i, 7, QTableWidgetItem(str(item.get('ship_price', 0))))
            self.pl_table.setItem(i, 8, QTableWidgetItem(str(item.get('ship_amount', 0))))
            self.pl_table.setItem(i, 9, QTableWidgetItem(str(item.get('ship_cartons', 0))))
            self.pl_table.setItem(i, 10, QTableWidgetItem(str(item.get('ship_weight', 0))))
            self.pl_table.setItem(i, 11, QTableWidgetItem(str(item.get('ship_volume', 0))))
    
    def _on_export_excel(self):
        """导出Excel"""
        try:
            from PySide6.QtWidgets import QFileDialog
            
            current_tab = self.tab_widget.currentIndex()
            table_map = {0: self.ci_table, 1: self.pl_table, 2: self.custom_table}
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存Excel文件", f"shipment_{self.shipment_id or 'export'}.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
            
            table = table_map.get(current_tab, self.ci_table)
            self._save_to_excel(table, file_path)
        except ImportError:
            print("需要安装 openpyxl 库来支持 Excel 导出")
        except Exception as e:
            print(f"导出失败: {e}")
    
    def _save_to_excel(self, table: QTableWidget, file_path: str):
        """将表格内容保存到Excel"""
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        
        # 写入表头
        headers = []
        for col in range(table.columnCount()):
            header_item = table.horizontalHeaderItem(col)
            headers.append(header_item.text() if header_item else f"Col{col}")
        ws.append(headers)
        
        # 写入数据
        for row in range(table.rowCount()):
            row_data = []
            for col in range(table.columnCount()):
                item = table.item(row, col)
                row_data.append(item.text() if item else '')
            ws.append(row_data)
        
        wb.save(file_path)
