"""
产品OE显示对话框 - 点击"多OE号"时显示完整OE列表
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                              QTableWidget, QTableWidgetItem, QHeaderView, QHBoxLayout)
from PySide6.QtCore import Qt


class ProductOEDialog(QDialog):
    """产品OE列表弹窗"""
    
    def __init__(self, product_id: int, oe_list: list, api_client, parent=None):
        super().__init__(parent)
        self.product_id = product_id
        self.oe_list = oe_list
        self.api_client = api_client
        self.setWindowTitle(f"OE号列表 - 产品ID:{product_id}")
        self.setMinimumSize(500, 300)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel(f"产品ID: {self.product_id}")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        # OE列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["OE号", "是否主OE", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        
        self._populate_table()
        layout.addWidget(self.table)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #4b5563; }
        """)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def _populate_table(self):
        """填充OE列表"""
        self.table.setRowCount(len(self.oe_list))
        
        for row, oe in enumerate(self.oe_list):
            # OE号
            self.table.setItem(row, 0, QTableWidgetItem(oe.get('oe_number', '')))
            
            # 是否主OE
            is_primary = "✓ 主OE" if oe.get('is_primary') else "—"
            primary_item = QTableWidgetItem(is_primary)
            primary_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, primary_item)
            
            # 操作按钮
            op_widget = QWidget()
            op_layout = QHBoxLayout()
            op_layout.setContentsMargins(0, 0, 0, 0)
            
            if not oe.get('is_primary'):
                set_primary_btn = QPushButton("设为主")
                set_primary_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3b82f6;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 4px 8px;
                        font-size: 11px;
                    }
                    QPushButton:hover { background-color: #2563eb; }
                """)
                set_primary_btn.clicked.connect(lambda checked, oid=oe.get('id'): self._set_primary(oid))
                op_layout.addWidget(set_primary_btn)
            
            delete_btn = QPushButton("删除")
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                }
                QPushButton:hover { background-color: #dc2626; }
            """)
            delete_btn.clicked.connect(lambda checked, oid=oe.get('id'): self._delete_oe(oid))
            op_layout.addWidget(delete_btn)
            
            op_widget.setLayout(op_layout)
            self.table.setCellWidget(row, 2, op_widget)
    
    def _set_primary(self, oe_id: int):
        """设置为主OE"""
        try:
            self.api_client.set_primary_oe(self.product_id, oe_id)
            # 刷新列表
            self.oe_list = self.api_client.get_product_oes(self.product_id) or []
            self._populate_table()
        except Exception as e:
            print(f"设置主OE失败: {e}")
    
    def _delete_oe(self, oe_id: int):
        """删除OE"""
        try:
            self.api_client.delete_product_oe(oe_id)
            # 刷新列表
            self.oe_list = self.api_client.get_product_oes(self.product_id) or []
            self._populate_table()
        except Exception as e:
            print(f"删除OE失败: {e}")


class AddOEDialog(QDialog):
    """添加OE号对话框"""
    
    added = ...  # Signal placeholder
    
    def __init__(self, product_id: int, api_client, parent=None):
        from PySide6.QtCore import Signal
        super().__init__(parent)
        self.product_id = product_id
        self.api_client = api_client
        self.added = Signal(str)  # 添加成功信号
        
        self.setWindowTitle("添加OE号")
        self.setMinimumSize(400, 150)
        self._setup_ui()
    
    def _setup_ui(self):
        from PySide6.QtWidgets import QLineEdit, QCheckBox, QFormLayout
        
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        self.oe_number_edit = QLineEdit()
        self.oe_number_edit.setPlaceholderText("输入OE号，如: 12710304 /M365")
        form.addRow("OE号:", self.oe_number_edit)
        
        self.is_primary_check = QCheckBox()
        self.is_primary_check.setText("设为主OE号")
        form.addRow("主OE:", self.is_primary_check)
        
        layout.addLayout(form)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }
        """)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _save(self):
        """保存OE号"""
        from PySide6.QtWidgets import QMessageBox
        
        oe_number = self.oe_number_edit.text().strip()
        if not oe_number:
            QMessageBox.warning(self, "提示", "请输入OE号")
            return
        
        try:
            data = {
                "product_id": self.product_id,
                "oe_number": oe_number,
                "is_primary": self.is_primary_check.isChecked()
            }
            self.api_client.create_product_oe(data)
            self.added.emit(oe_number)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {e}")