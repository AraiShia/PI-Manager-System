# -*- coding: utf-8 -*-
"""
产品项编辑对话框

文件：client/widgets/product_item_edit_dialog.py
创建日期：2026-06-04
来源：main.py L153-266（已迁移）
用途：编辑订单产品项的基本信息（产品名称、型号、数量、单价等）

调用方式：
```python
from widgets import ProductItemEditDialog

dialog = ProductItemEditDialog(item, products, parent=self)
if dialog.exec():
    updated_item = dialog.get_item()
```

依赖：
- PySide6.QtWidgets: QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QDoubleSpinBox, QPushButton, QFormLayout
- PySide6.QtCore: Qt
- api.client.ApiClient: 用于获取产品 OE 号
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QDoubleSpinBox, QPushButton, QFormLayout
)
from PySide6.QtCore import Qt


class ProductItemEditDialog(QDialog):
    """
    产品项编辑对话框
    
    功能：
    - 选择产品并自动填充字段
    - 编辑客户产品编号、OE号、产品名称、客户型号、数量、单价
    
    构造参数：
    - item: dict, 当前产品项数据
    - products: list[dict], 产品列表
    - parent: QWidget, 父窗口
    """
    
    def __init__(self, item, products, parent=None):
        super().__init__(parent)
        self.item = item.copy()
        self.products = products
        self.setWindowTitle("编辑产品")
        self.setMinimumWidth(500)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 产品下拉选择（从产品列表读取）
        product_layout = QHBoxLayout()
        product_layout.addWidget(QLabel("选择产品:"))
        self.product_combo = QComboBox()
        self.product_combo.addItem("-- 请选择 --", None)
        for p in self.products:
            product_name = p.get('detail_desc', '') or p.get('name', '')
            self.product_combo.addItem(product_name, p.get('id'))
        product_layout.addWidget(self.product_combo)
        layout.addLayout(product_layout)
        
        # 可编辑字段
        fields = [
            ("客户产品编号", "customer_product_code", ""),
            ("OE号", "oe_number", ""),
            ("产品名称", "product_name", ""),
            ("客户型号", "customer_model", ""),
            ("数量", "quantity", "number"),
            ("单价", "unit_price", "number"),
        ]
        
        self.editors = {}
        form_layout = QFormLayout()
        for label, key, field_type in fields:
            if field_type == "number":
                editor = QDoubleSpinBox()
                editor.setRange(0, 99999999)
                editor.setDecimals(2)
                try:
                    val = float(self.item.get(key, 0) or 0)
                    editor.setValue(val)
                except:
                    editor.setValue(0)
            else:
                editor = QLineEdit(str(self.item.get(key, '')))
                editor.setFixedHeight(30)
            self.editors[key] = editor
            form_layout.addRow(f"{label}:", editor)
        
        layout.addLayout(form_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
        """)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
        # 产品选择变化时自动填充
        self.product_combo.currentIndexChanged.connect(self._on_product_selected)
    
    def _on_product_selected(self, index):
        """选择产品后自动填充字段"""
        product_id = self.product_combo.currentData()
        if not product_id:
            return
        
        for p in self.products:
            if p.get('id') == product_id:
                # 自动填充可用的字段
                if not self.editors['customer_product_code'].text():
                    self.editors['customer_product_code'].setText(p.get('product_code', ''))
                if not self.editors['oe_number'].text():
                    # 尝试获取主要OE号
                    # 注意：需要通过 parent().parent() 访问 api_client（这是 MainWindow 的结构）
                    try:
                        api_client = self.parent().parent().api_client
                        oe_list = api_client.get_product_oes(product_id) or []
                        primary_oe = next((oe for oe in oe_list if oe.get('is_primary')), None)
                        if primary_oe:
                            self.editors['oe_number'].setText(primary_oe.get('oe_number', ''))
                    except Exception as e:
                        print(f"[WARN] ProductItemEditDialog: 获取OE号失败: {e}")
                if not self.editors['product_name'].text():
                    self.editors['product_name'].setText(p.get('detail_desc', '') or p.get('name', ''))
                break
    
    def _on_save(self):
        """保存编辑结果"""
        print("[DEBUG] ProductItemEditDialog._on_save: 开始保存")
        for key, editor in self.editors.items():
            if isinstance(editor, QLineEdit):
                self.item[key] = editor.text()
                print(f"[DEBUG] 字段 {key}: {editor.text()}")
            elif isinstance(editor, QDoubleSpinBox):
                self.item[key] = editor.value()
                print(f"[DEBUG] 字段 {key}: {editor.value()}")
        print(f"[DEBUG] ProductItemEditDialog._on_save: 保存完成, item={self.item}")
        self.accept()
    
    def get_item(self):
        """
        获取编辑后的产品项
        
        Returns:
            dict: 编辑后的产品项数据
        """
        return self.item