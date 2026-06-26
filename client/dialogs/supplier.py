# -*- coding: utf-8 -*-
"""
供应商相关 Dialog

文件：client/dialogs/supplier.py
创建日期：2026-06-04
来源：main.py L424-705（SupplierSchemeDialog）, L1495-1672（SupplierDialog）（已迁移合并）
包含：
- SupplierSchemeDialog: 供应商方案编辑对话框
- SupplierDialog: 供应商编辑/新建对话框

调用方式：
```python
from dialogs import SupplierDialog, SupplierSchemeDialog

# 新建/编辑供应商
dialog = SupplierDialog(api_client)
if dialog.exec():
    # 保存成功

# 编辑供应商方案
dialog = SupplierSchemeDialog(api_client, suppliers, customers, scheme=scheme_data)
if dialog.exec():
    scheme = dialog.get_scheme_data()

# 新建供应商方案
dialog = SupplierSchemeDialog(api_client, suppliers, customers)
if dialog.exec():
    scheme = dialog.get_scheme_data()
```

依赖：
- PySide6.QtWidgets: QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QGridLayout,
  QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton, QCheckBox
- PySide6.QtCore: Qt, QTimer
- PySide6.QtGui: QFont
- api.client.ApiClient: api_client 实例
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QGridLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton, QCheckBox,
    QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.client import ApiClient


class SupplierSchemeDialog(QDialog):
    """
    供应商方案编辑对话框
    
    功能：
    - 创建/编辑供应商方案
    - 设置默认方案或指定客户专属方案
    - 配置价格信息（EXW/FOB含税/不含税）
    - 配置包装尺寸和重量
    
    构造参数：
    - api_client: ApiClient, API 客户端
    - suppliers: list[dict], 供应商列表
    - customers: list[dict], 客户列表
    - scheme: dict, 方案数据（编辑模式），None 表示新建模式
    - parent: QWidget, 父窗口
    """
    
    def __init__(self, api_client, suppliers, customers, scheme=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.suppliers = suppliers
        self.customers = customers
        self.scheme = scheme or {}
        self.is_edit = bool(scheme)
        self.setWindowTitle("编辑供应商方案" if self.is_edit else "添加供应商方案")
        self.setFixedSize(650, 700)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        # 供应商
        self.supplier_combo = QComboBox()
        self.supplier_combo.setFixedHeight(35)
        self.supplier_combo.addItem("请选择供应商", None)
        for s in self.suppliers:
            self.supplier_combo.addItem(f"{s.get('supplier_code')} - {s.get('supplier_name')}", s.get('id'))
        if self.scheme.get('supplier_id'):
            for i in range(self.supplier_combo.count()):
                if self.supplier_combo.itemData(i) == self.scheme.get('supplier_id'):
                    self.supplier_combo.setCurrentIndex(i)
                    break
        form_layout.addRow("供应商 *:", self.supplier_combo)

        # 方案类型选择
        self.scheme_type_combo = QComboBox()
        self.scheme_type_combo.setFixedHeight(35)
        self.scheme_type_combo.addItem("🏷️ 默认方案（不指定客户）", {'type': 'default', 'customer_id': None})
        self.scheme_type_combo.addItem("👤 指定客户专属方案", {'type': 'customer', 'customer_id': None})
        self.scheme_type_combo.currentIndexChanged.connect(self.on_scheme_type_changed)
        form_layout.addRow("方案类型 *:", self.scheme_type_combo)

        # 客户选择（仅在指定客户时显示）
        self.customer_combo = QComboBox()
        self.customer_combo.setFixedHeight(35)
        self.customer_combo.addItem("请选择客户", None)
        for c in self.customers:
            self.customer_combo.addItem(f"{c.get('customer_code')} - {c.get('customer_name')}", c.get('id'))
        self.customer_combo.setVisible(False)
        
        if self.is_edit:
            if self.scheme.get('customer_id'):
                self.scheme_type_combo.setCurrentIndex(1)
                self.customer_combo.setVisible(True)
                for i in range(self.customer_combo.count()):
                    if self.customer_combo.itemData(i) == self.scheme.get('customer_id'):
                        self.customer_combo.setCurrentIndex(i)
                        break
            else:
                self.scheme_type_combo.setCurrentIndex(0)
        
        form_layout.addRow("选择客户:", self.customer_combo)

        # 客户产品编号
        self.customer_code_input = QLineEdit()
        self.customer_code_input.setPlaceholderText("客户在对方系统中的产品编号")
        default_code = self.scheme.get('factory_code') or self.scheme.get('customer_product_code', '')
        if not default_code and not self.is_edit and self.parent() and hasattr(self.parent(), 'oe_input'):
            default_code = self.parent().oe_input.text().strip()
        self.customer_code_input.setText(default_code)
        form_layout.addRow("客户产品编号:", self.customer_code_input)

        layout.addLayout(form_layout)

        # 价格信息
        price_group = QGroupBox("价格信息")
        price_layout = QGridLayout()
        price_layout.setSpacing(10)

        self.exw_incl_input = QLineEdit()
        self.exw_incl_input.setPlaceholderText("EXW含税价")
        exw_val = self.scheme.get('exw_price_incl') or self.scheme.get('purchase_price', '')
        self.exw_incl_input.setText(str(exw_val or ''))
        price_layout.addWidget(QLabel("EXW含税价:"), 0, 0)
        price_layout.addWidget(self.exw_incl_input, 0, 1)

        self.exw_excl_input = QLineEdit()
        self.exw_excl_input.setPlaceholderText("EXW不含税价")
        self.exw_excl_input.setText(str(self.scheme.get('exw_price_excl', '') or ''))
        price_layout.addWidget(QLabel("EXW不含税价:"), 0, 2)
        price_layout.addWidget(self.exw_excl_input, 0, 3)

        self.fob_incl_input = QLineEdit()
        self.fob_incl_input.setPlaceholderText("FOB含税价")
        self.fob_incl_input.setText(str(self.scheme.get('fob_price_incl', '') or ''))
        price_layout.addWidget(QLabel("FOB含税价:"), 1, 0)
        price_layout.addWidget(self.fob_incl_input, 1, 1)

        self.fob_excl_input = QLineEdit()
        self.fob_excl_input.setPlaceholderText("FOB不含税价")
        self.fob_excl_input.setText(str(self.scheme.get('fob_price_excl', '') or ''))
        price_layout.addWidget(QLabel("FOB不含税价:"), 1, 2)
        price_layout.addWidget(self.fob_excl_input, 1, 3)

        self.freight_input = QLineEdit()
        self.freight_input.setPlaceholderText("运费")
        self.freight_input.setText(str(self.scheme.get('freight', '') or ''))
        price_layout.addWidget(QLabel("运费:"), 2, 0)
        price_layout.addWidget(self.freight_input, 2, 1)

        self.packing_fee_input = QLineEdit()
        self.packing_fee_input.setPlaceholderText("包装费")
        self.packing_fee_input.setText(str(self.scheme.get('packing_fee', '') or ''))
        price_layout.addWidget(QLabel("包装费:"), 2, 2)
        price_layout.addWidget(self.packing_fee_input, 2, 3)

        price_group.setLayout(price_layout)
        layout.addWidget(price_group)

        # 包装尺寸
        size_group = QGroupBox("包装尺寸")
        size_layout = QGridLayout()
        self.carton_length_input = QLineEdit()
        self.carton_length_input.setPlaceholderText("长(cm)")
        self.carton_length_input.setText(str(self.scheme.get('carton_length_cm', '') or ''))
        size_layout.addWidget(QLabel("纸箱长(cm):"), 0, 0)
        size_layout.addWidget(self.carton_length_input, 0, 1)

        self.carton_width_input = QLineEdit()
        self.carton_width_input.setPlaceholderText("宽(cm)")
        self.carton_width_input.setText(str(self.scheme.get('carton_width_cm', '') or ''))
        size_layout.addWidget(QLabel("纸箱宽(cm):"), 0, 2)
        size_layout.addWidget(self.carton_width_input, 0, 3)

        self.carton_height_input = QLineEdit()
        self.carton_height_input.setPlaceholderText("高(cm)")
        self.carton_height_input.setText(str(self.scheme.get('carton_height_cm', '') or ''))
        size_layout.addWidget(QLabel("纸箱高(cm):"), 1, 0)
        size_layout.addWidget(self.carton_height_input, 1, 1)

        self.units_input = QLineEdit()
        self.units_input.setPlaceholderText("每箱数量")
        self.units_input.setText(str(self.scheme.get('units_per_carton', '') or ''))
        size_layout.addWidget(QLabel("每箱数量:"), 1, 2)
        size_layout.addWidget(self.units_input, 1, 3)
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)

        # 重量信息
        weight_group = QGroupBox("重量信息")
        weight_layout = QHBoxLayout()
        self.gross_weight_input = QLineEdit()
        self.gross_weight_input.setPlaceholderText("毛重(kg)")
        self.gross_weight_input.setText(str(self.scheme.get('gross_weight_kg', '') or ''))
        weight_layout.addWidget(QLabel("毛重(kg):"))
        weight_layout.addWidget(self.gross_weight_input)

        self.weight_input = QLineEdit()
        self.weight_input.setPlaceholderText("净重(kg)")
        self.weight_input.setText(str(self.scheme.get('weight_kg', '') or ''))
        weight_layout.addWidget(QLabel("净重(kg):"))
        weight_layout.addWidget(self.weight_input)
        weight_group.setLayout(weight_layout)
        layout.addWidget(weight_group)

        # 备注
        self.remark_input = QTextEdit()
        self.remark_input.setPlaceholderText("备注信息")
        self.remark_input.setText(self.scheme.get('remark', ''))
        self.remark_input.setMaximumHeight(60)
        layout.addWidget(QLabel("备注:"))
        layout.addWidget(self.remark_input)
        
        # 设为默认方案
        self.is_default_checkbox = QCheckBox("设为默认供应商方案（优先使用）")
        self.is_default_checkbox.setStyleSheet("color: #2563eb; font-weight: 500;")
        if self.scheme.get('is_default'):
            self.is_default_checkbox.setChecked(True)
        layout.addWidget(self.is_default_checkbox)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.save_scheme)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def on_scheme_type_changed(self):
        """方案类型变化时显示/隐藏客户选择"""
        scheme_data = self.scheme_type_combo.currentData()
        if scheme_data and scheme_data.get('type') == 'customer':
            self.customer_combo.setVisible(True)
        else:
            self.customer_combo.setVisible(False)

    def save_scheme(self):
        """保存方案"""
        supplier_id = self.supplier_combo.currentData()
        
        if not supplier_id:
            QMessageBox.warning(self, "警告", "请选择供应商")
            return
        
        scheme_data = self.scheme_type_combo.currentData()
        customer_id = None
        if scheme_data and scheme_data.get('type') == 'customer':
            customer_id = self.customer_combo.currentData()
            if not customer_id:
                QMessageBox.warning(self, "警告", "请选择客户")
                return

        def try_float(value):
            try:
                return float(value) if value.strip() else None
            except ValueError:
                return None

        supplier_name = self.supplier_combo.currentText()
        customer_name = self.customer_combo.currentText()

        self.scheme_data = {
            "id": self.scheme.get('id') if self.is_edit else None,
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "customer_product_code": self.customer_code_input.text().strip(),
            "is_default": self.is_default_checkbox.isChecked(),
            "exw_price_incl": try_float(self.exw_incl_input.text()),
            "exw_price_excl": try_float(self.exw_excl_input.text()),
            "fob_price_incl": try_float(self.fob_incl_input.text()),
            "fob_price_excl": try_float(self.fob_excl_input.text()),
            "freight": try_float(self.freight_input.text()),
            "packing_fee": try_float(self.packing_fee_input.text()),
            "carton_length_cm": try_float(self.carton_length_input.text()),
            "carton_width_cm": try_float(self.carton_width_input.text()),
            "carton_height_cm": try_float(self.carton_height_input.text()),
            "units_per_carton": int(self.units_input.text()) if self.units_input.text().strip() else None,
            "gross_weight_kg": try_float(self.gross_weight_input.text()),
            "weight_kg": try_float(self.weight_input.text()),
            "remark": self.remark_input.toPlainText()
        }
        print(f"DEBUG - save_scheme: scheme_data = {self.scheme_data}")
        self.accept()

    def get_scheme_data(self):
        """获取方案数据"""
        return getattr(self, 'scheme_data', None)


class SupplierDialog(QDialog):
    """
    供应商编辑/新建对话框
    
    功能：
    - 新建供应商
    - 编辑现有供应商
    - 选择省份/城市，自动生成城市编码
    
    构造参数：
    - api_client: ApiClient, API 客户端
    - supplier: dict, 供应商数据（编辑模式），None 表示新建模式
    """
    
    def __init__(self, api_client: ApiClient, supplier=None):
        super().__init__()
        self.api_client = api_client
        self.supplier = supplier
        self.is_edit = supplier is not None
        self.provinces = []
        self.cities = []
        self.selected_city_code = ""
        self.init_ui()
        QTimer.singleShot(0, self.load_provinces)

    def load_provinces(self):
        """加载省份列表"""
        try:
            self.provinces = self.api_client.get_provinces()
            self.province_combo.clear()
            self.province_combo.addItems(self.provinces)
            if self.supplier and self.supplier.get('region'):
                region = self.supplier.get('region', '')
                for prov in self.provinces:
                    if region.startswith(prov):
                        self.province_combo.setCurrentText(prov)
                        self.load_cities(prov)
                        city_name = region[len(prov):].strip()
                        if city_name and city_name in self.cities:
                            self.city_combo.setCurrentText(city_name)
                        break
        except Exception as e:
            print(f"加载省份失败: {e}")

    def load_cities(self, province):
        """加载城市列表"""
        try:
            self.cities = self.api_client.get_cities(province)
            self.city_combo.clear()
            self.city_combo.addItems(self.cities)
        except Exception as e:
            print(f"加载城市失败: {e}")

    def on_province_changed(self, province):
        """省份变化"""
        self.load_cities(province)

    def on_city_changed(self, city):
        """城市变化，生成城市编码"""
        province = self.province_combo.currentText()
        try:
            # 使用模块级别的静态映射
            from main import PROVINCE_CODE_MAP, CITY_CODE_MAP
            p_code = PROVINCE_CODE_MAP.get(province, "")
            c_map = CITY_CODE_MAP.get(p_code, {})
            self.selected_city_code = p_code + c_map.get(city, "0")
        except Exception as e:
            print(f"获取城市编码失败: {e}")

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("编辑供应商" if self.is_edit else "新增供应商")
        self.setFixedSize(500, 480)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        if self.is_edit:
            self.code_label = QLabel(self.supplier.get('supplier_code', ''))
            form_layout.addRow("供应商编号:", self.code_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入供应商名称")
        if self.supplier:
            self.name_input.setText(self.supplier.get('supplier_name', ''))
        form_layout.addRow("供应商名称:", self.name_input)

        province_layout = QHBoxLayout()
        self.province_combo = QComboBox()
        self.province_combo.setFixedHeight(35)
        self.province_combo.currentTextChanged.connect(self.on_province_changed)
        province_layout.addWidget(self.province_combo)

        self.city_combo = QComboBox()
        self.city_combo.setFixedHeight(35)
        self.city_combo.currentTextChanged.connect(self.on_city_changed)
        province_layout.addWidget(self.city_combo)
        form_layout.addRow("省份/城市:", province_layout)

        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("请输入联系人")
        if self.supplier:
            self.contact_input.setText(self.supplier.get('contact_person', ''))
        form_layout.addRow("联系人:", self.contact_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("请输入联系电话")
        if self.supplier:
            self.phone_input.setText(self.supplier.get('phone', ''))
        form_layout.addRow("联系电话:", self.phone_input)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("请输入邮箱地址")
        if self.supplier:
            self.email_input.setText(self.supplier.get('email', ''))
        form_layout.addRow("邮箱:", self.email_input)

        self.address_input = QTextEdit()
        self.address_input.setPlaceholderText("请输入详细地址")
        if self.supplier:
            self.address_input.setText(self.supplier.get('address', ''))
        self.address_input.setMaximumHeight(80)
        form_layout.addRow("详细地址:", self.address_input)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.save_supplier)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def save_supplier(self):
        """保存供应商"""
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入供应商名称")
            return

        province = self.province_combo.currentText()
        city = self.city_combo.currentText()
        region = f"{province} {city}" if province and city else ""

        data = {
            "supplier_name": self.name_input.text().strip(),
            "province": province,
            "city": city,
            "city_code": self.selected_city_code,
            "region": region,
            "contact_person": self.contact_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "email": self.email_input.text().strip(),
            "address": self.address_input.toPlainText().strip()
        }

        try:
            if self.is_edit:
                self.api_client.update_supplier(self.supplier['id'], data)
            else:
                self.api_client.create_supplier(data)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")