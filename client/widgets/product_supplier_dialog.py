from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QPushButton, QComboBox, QLineEdit,
                               QMessageBox, QHeaderView, QTabWidget, QWidget, 
                               QFormLayout, QSpinBox, QDoubleSpinBox, QTextEdit,
                               QLabel, QGroupBox, QSplitter, QCheckBox)
from PySide6.QtCore import Qt
from typing import List, Dict, Optional

class ProductSupplierDetailDialog(QDialog):
    """产品供应商详细信息编辑对话框"""
    def __init__(self, api_client, product_id, supplier_data=None, parent=None, oe_number=None):
        super().__init__(parent)
        self.api_client = api_client
        self.product_id = product_id
        self.supplier_data = supplier_data
        self.is_edit = supplier_data is not None
        self.oe_number = oe_number or ''  # OE号，用于默认工厂编号
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("编辑供应商方案" if self.is_edit else "添加供应商方案")
        self.setMinimumSize(550, 650)
        
        layout = QVBoxLayout()
        
        # 供应商和客户选择
        select_layout = QFormLayout()
        
        if not self.is_edit:
            self.supplier_combo = QComboBox()
            self.supplier_combo.setFixedWidth(300)
            select_layout.addRow("选择供应商*:", self.supplier_combo)
            self.load_suppliers()
        else:
            info_label = QLabel(f"供应商: {self.supplier_data.get('supplier_code', '')} - {self.supplier_data.get('supplier_name', '')}")
            info_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
            select_layout.addRow("供应商:", info_label)
        
        # 方案类型选择（客户专属或默认方案）
        self.scheme_type_combo = QComboBox()
        self.scheme_type_combo.setFixedWidth(300)
        self.scheme_type_combo.addItem("🏷️ 默认方案（不指定客户）", {'type': 'default', 'customer_id': None})
        self.scheme_type_combo.addItem("👤 指定客户专属方案", {'type': 'customer', 'customer_id': None})
        
        # 客户选择（仅在指定客户时显示）
        self.customer_combo = QComboBox()
        self.customer_combo.setFixedWidth(300)
        self.customer_combo.setVisible(False)
        self.load_customers()
        
        # 根据编辑数据设置初始值
        if self.is_edit:
            if self.supplier_data.get('customer_id'):
                # 有指定客户，选择"指定客户专属方案"
                self.scheme_type_combo.setCurrentIndex(1)
                self.customer_combo.setVisible(True)
                # 设置选中的客户
                target_id = self.supplier_data['customer_id']
                for i in range(self.customer_combo.count()):
                    item_data = self.customer_combo.itemData(i)
                    compare_id = item_data.get('id') if isinstance(item_data, dict) else item_data
                    if compare_id == target_id:
                        self.customer_combo.setCurrentIndex(i)
                        break
            else:
                # 无指定客户，选择"默认方案"
                self.scheme_type_combo.setCurrentIndex(0)
        
        select_layout.addRow("方案类型:", self.scheme_type_combo)
        select_layout.addRow("选择客户:", self.customer_combo)
        
        # 客户特殊要求标签
        self.customer_require_label = QLabel("")
        self.customer_require_label.setStyleSheet("color: #d97706; font-size: 11px; padding: 4px 8px; background: #fef3c7; border-radius: 4px;")
        self.customer_require_label.setWordWrap(True)
        self.customer_require_label.setVisible(False)
        select_layout.addRow("", self.customer_require_label)
        
        # 监听方案类型变化
        self.scheme_type_combo.currentIndexChanged.connect(self.on_scheme_type_changed)
        # 监听客户选择变化
        self.customer_combo.currentIndexChanged.connect(self.on_customer_changed)
        
        # 是否设为默认方案
        self.is_default_checkbox = QCheckBox("设为默认供应商方案（优先使用）")
        self.is_default_checkbox.setStyleSheet("color: #2563eb; font-weight: 500;")
        if self.is_edit and self.supplier_data.get('is_default'):
            self.is_default_checkbox.setChecked(True)
        select_layout.addRow("", self.is_default_checkbox)
        
        layout.addLayout(select_layout)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 基本信息页
        basic_tab = QWidget()
        basic_layout = QFormLayout()
        
        self.factory_code_input = QLineEdit()
        self.factory_code_input.setPlaceholderText("工厂编号，默认与OE号相同")
        # 默认值为OE号
        default_factory_code = self.oe_number if not self.is_edit else ''
        if self.is_edit:
            self.factory_code_input.setText(self.supplier_data.get('factory_code', ''))
        else:
            self.factory_code_input.setText(default_factory_code)
        basic_layout.addRow("工厂编号*:", self.factory_code_input)
        
        self.purchase_channel_input = QLineEdit()
        self.purchase_channel_input.setPlaceholderText("请输入采购渠道（如1688、对私付款等）")
        if self.is_edit:
            self.purchase_channel_input.setText(self.supplier_data.get('purchase_channel', '') or '')
        basic_layout.addRow("采购渠道:", self.purchase_channel_input)
        
        self.remark_input = QTextEdit()
        self.remark_input.setPlaceholderText("请输入备注信息")
        self.remark_input.setMaximumHeight(60)
        if self.is_edit:
            self.remark_input.setText(self.supplier_data.get('remark', '') or '')
        basic_layout.addRow("备注:", self.remark_input)
        
        basic_tab.setLayout(basic_layout)
        tab_widget.addTab(basic_tab, "基本信息")
        
        # 价格信息页
        price_tab = QWidget()
        price_layout = QFormLayout()
        
        self.purchase_price_input = QDoubleSpinBox()
        self.purchase_price_input.setRange(0, 9999999)
        self.purchase_price_input.setDecimals(4)
        self.purchase_price_input.setPrefix("¥ ")
        if self.is_edit and self.supplier_data.get('purchase_price'):
            self.purchase_price_input.setValue(float(self.supplier_data['purchase_price']))
        price_layout.addRow("采购价格:", self.purchase_price_input)
        
        self.currency_input = QLineEdit()
        self.currency_input.setPlaceholderText("CNY")
        self.currency_input.setText("CNY")
        if self.is_edit and self.supplier_data.get('currency'):
            self.currency_input.setText(self.supplier_data['currency'])
        price_layout.addRow("币种:", self.currency_input)
        
        self.moq_input = QSpinBox()
        self.moq_input.setRange(0, 999999)
        self.moq_input.setSuffix(" 件")
        if self.is_edit and self.supplier_data.get('moq'):
            self.moq_input.setValue(int(self.supplier_data['moq']))
        price_layout.addRow("最小起订量(MOQ):", self.moq_input)
        
        self.lead_time_input = QSpinBox()
        self.lead_time_input.setRange(0, 365)
        self.lead_time_input.setSuffix(" 天")
        if self.is_edit and self.supplier_data.get('lead_time_days'):
            self.lead_time_input.setValue(int(self.supplier_data['lead_time_days']))
        price_layout.addRow("交货周期:", self.lead_time_input)
        
        price_tab.setLayout(price_layout)
        tab_widget.addTab(price_tab, "价格信息")
        
        # 包装信息页
        package_tab = QWidget()
        package_layout = QFormLayout()
        
        self.units_per_carton_input = QSpinBox()
        self.units_per_carton_input.setRange(0, 99999)
        self.units_per_carton_input.setSuffix(" pcs")
        if self.is_edit and self.supplier_data.get('units_per_carton'):
            self.units_per_carton_input.setValue(int(self.supplier_data['units_per_carton']))
        package_layout.addRow("每箱数量:", self.units_per_carton_input)
        
        # 外箱尺寸
        size_layout = QHBoxLayout()
        self.carton_length_input = QDoubleSpinBox()
        self.carton_length_input.setRange(0, 999)
        self.carton_length_input.setDecimals(2)
        self.carton_length_input.setSuffix(" cm")
        if self.is_edit and self.supplier_data.get('carton_length_cm'):
            self.carton_length_input.setValue(float(self.supplier_data['carton_length_cm']))
        size_layout.addWidget(QLabel("长:"))
        size_layout.addWidget(self.carton_length_input)
        
        self.carton_width_input = QDoubleSpinBox()
        self.carton_width_input.setRange(0, 999)
        self.carton_width_input.setDecimals(2)
        self.carton_width_input.setSuffix(" cm")
        if self.is_edit and self.supplier_data.get('carton_width_cm'):
            self.carton_width_input.setValue(float(self.supplier_data['carton_width_cm']))
        size_layout.addWidget(QLabel("宽:"))
        size_layout.addWidget(self.carton_width_input)
        
        self.carton_height_input = QDoubleSpinBox()
        self.carton_height_input.setRange(0, 999)
        self.carton_height_input.setDecimals(2)
        self.carton_height_input.setSuffix(" cm")
        if self.is_edit and self.supplier_data.get('carton_height_cm'):
            self.carton_height_input.setValue(float(self.supplier_data['carton_height_cm']))
        size_layout.addWidget(QLabel("高:"))
        size_layout.addWidget(self.carton_height_input)
        
        package_layout.addRow("外箱尺寸:", size_layout)
        
        self.gross_weight_input = QDoubleSpinBox()
        self.gross_weight_input.setRange(0, 9999)
        self.gross_weight_input.setDecimals(4)
        self.gross_weight_input.setSuffix(" kg")
        if self.is_edit and self.supplier_data.get('gross_weight_kg'):
            self.gross_weight_input.setValue(float(self.supplier_data['gross_weight_kg']))
        package_layout.addRow("毛重:", self.gross_weight_input)
        
        package_tab.setLayout(package_layout)
        tab_widget.addTab(package_tab, "包装信息")
        
        # 特殊需求页
        special_tab = QWidget()
        special_layout = QVBoxLayout()
        
        special_label = QLabel("记录客户的特殊需求，如特殊包装、标签、认证要求等：")
        special_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        special_layout.addWidget(special_label)
        
        self.special_requirements_input = QTextEdit()
        self.special_requirements_input.setPlaceholderText("例如：\n- 需要贴客户指定标签\n- 特殊包装要求（木箱/托盘）\n- 需要提供认证证书\n- 其他定制需求...")
        if self.is_edit:
            self.special_requirements_input.setText(self.supplier_data.get('special_requirements', '') or '')
        special_layout.addWidget(self.special_requirements_input)
        
        special_tab.setLayout(special_layout)
        tab_widget.addTab(special_tab, "特殊需求")
        
        layout.addWidget(tab_widget)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(100)
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
        save_btn.clicked.connect(self.save)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def load_suppliers(self):
        """加载供应商列表"""
        try:
            suppliers = self.api_client.get_suppliers()
            for s in suppliers:
                self.supplier_combo.addItem(f"{s['supplier_code']} - {s['supplier_name']}", s['id'])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载供应商失败: {str(e)}")
    
    def load_customers(self):
        """加载客户列表"""
        try:
            customers = self.api_client.get_customers()
            for c in customers:
                # 将特殊要求也存入item data，供后续使用
                special_req = c.get('special_require', '') or ''
                display_text = f"{c['customer_code']} - {c['customer_name']}"
                self.customer_combo.addItem(display_text, {'id': c['id'], 'special_require': special_req})
        except Exception as e:
            print(f"加载客户失败: {str(e)}")
    
    def on_scheme_type_changed(self):
        """方案类型变化时显示/隐藏客户选择"""
        scheme_data = self.scheme_type_combo.currentData()
        if scheme_data and scheme_data.get('type') == 'customer':
            self.customer_combo.setVisible(True)
            self.customer_require_label.setVisible(True)
            self.update_customer_require_label()
        else:
            self.customer_combo.setVisible(False)
            self.customer_require_label.setVisible(False)
    
    def on_customer_changed(self):
        """客户选择变化时更新特殊要求显示"""
        self.update_customer_require_label()
    
    def update_customer_require_label(self):
        """更新客户特殊要求标签"""
        current_data = self.customer_combo.currentData()
        if current_data and isinstance(current_data, dict):
            special_req = current_data.get('special_require', '')
            if special_req:
                self.customer_require_label.setText(f"⚠️ 客户特殊要求: {special_req}")
            else:
                self.customer_require_label.setText("")
        else:
            self.customer_require_label.setText("")
    
    def save(self):
        """保存数据"""
        factory_code = self.factory_code_input.text().strip()
        if not factory_code:
            QMessageBox.warning(self, "提示", "请输入工厂编号")
            return
        
        # 根据方案类型获取客户ID
        scheme_data = self.scheme_type_combo.currentData()
        customer_id = None
        if scheme_data and scheme_data.get('type') == 'customer':
            customer_data = self.customer_combo.currentData()
            if isinstance(customer_data, dict):
                customer_id = customer_data.get('id')
            else:
                customer_id = customer_data
            
            if not customer_id:
                QMessageBox.warning(self, "提示", "请选择客户")
                return
        
        data = {
            'factory_code': factory_code,
            'customer_id': customer_id,
            'is_default': self.is_default_checkbox.isChecked(),
            'purchase_channel': self.purchase_channel_input.text().strip() or None,
            'purchase_price': self.purchase_price_input.value() if self.purchase_price_input.value() > 0 else None,
            'currency': self.currency_input.text().strip() or 'CNY',
            'moq': self.moq_input.value() if self.moq_input.value() > 0 else None,
            'lead_time_days': self.lead_time_input.value() if self.lead_time_input.value() > 0 else None,
            'remark': self.remark_input.toPlainText().strip() or None,
            'units_per_carton': self.units_per_carton_input.value() if self.units_per_carton_input.value() > 0 else None,
            'carton_length_cm': self.carton_length_input.value() if self.carton_length_input.value() > 0 else None,
            'carton_width_cm': self.carton_width_input.value() if self.carton_width_input.value() > 0 else None,
            'carton_height_cm': self.carton_height_input.value() if self.carton_height_input.value() > 0 else None,
            'gross_weight_kg': self.gross_weight_input.value() if self.gross_weight_input.value() > 0 else None,
            'special_requirements': self.special_requirements_input.toPlainText().strip() or None
        }
        
        try:
            import json
            print(f"DEBUG - 保存数据: {json.dumps(data, ensure_ascii=False, default=str)}")
            
            if self.is_edit:
                result = self.api_client.update_product_supplier(self.supplier_data['id'], data)
                print(f"DEBUG - 更新成功: {result}")
            else:
                supplier_id = self.supplier_combo.currentData()
                if not supplier_id:
                    QMessageBox.warning(self, "提示", "请选择供应商")
                    return
                data['product_id'] = self.product_id
                data['supplier_id'] = supplier_id
                print(f"DEBUG - 新建数据: {json.dumps(data, ensure_ascii=False, default=str)}")
                result = self.api_client.add_product_supplier_full(data)
                print(f"DEBUG - 创建成功: {result}")
            
            self.accept()
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"DEBUG - 保存失败: {str(e)}\n{error_detail}")
            QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")


class ProductSupplierDialog(QDialog):
    def __init__(self, api_client, product_id, oe_number=None):
        super().__init__()
        self.api_client = api_client
        self.product_id = product_id
        self.oe_number = oe_number or ''  # OE号，用于默认工厂编号
        self.suppliers = []
        self.supplier_map = {}
        self.init_ui()
        self.load_data()

    def load_data(self):
        """加载供应商列表和产品的供应商关联"""
        try:
            self.load_product_suppliers()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载数据失败: {str(e)}")

    def load_product_suppliers(self):
        """加载产品的供应商关联"""
        try:
            self.table.setRowCount(0)
            suppliers = self.api_client.get_product_suppliers(self.product_id)
            
            for idx, supplier in enumerate(suppliers):
                self.table.insertRow(idx)
                self.table.setItem(idx, 0, QTableWidgetItem(supplier.get('supplier_code', '')))
                self.table.setItem(idx, 1, QTableWidgetItem(supplier.get('supplier_name', '')))
                self.table.setItem(idx, 2, QTableWidgetItem(supplier.get('factory_code', '')))
                
                # 客户信息（显示客户编码+名称，或通用）
                customer_code = supplier.get('customer_code', '')
                customer_name = supplier.get('customer_name', '')
                if customer_code and customer_name:
                    customer_text = f"{customer_code} - {customer_name}"
                elif customer_name:
                    customer_text = customer_name
                else:
                    customer_text = "通用"
                self.table.setItem(idx, 3, QTableWidgetItem(customer_text))
                
                # 价格信息
                price = supplier.get('purchase_price')
                price_text = f"¥{price}" if price else "-"
                self.table.setItem(idx, 4, QTableWidgetItem(price_text))
                
                # 包装信息
                units = supplier.get('units_per_carton')
                units_text = f"{units} pcs" if units else "-"
                self.table.setItem(idx, 5, QTableWidgetItem(units_text))
                
                # 是否默认
                is_default = "✓" if supplier.get('is_default') else ""
                default_item = QTableWidgetItem(is_default)
                default_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(idx, 6, default_item)
                
                # 添加操作按钮
                btn_layout = QHBoxLayout()
                edit_btn = QPushButton("编辑")
                edit_btn.setFixedWidth(50)
                edit_btn.clicked.connect(lambda checked, ps=supplier: self.edit_supplier(ps))
                
                delete_btn = QPushButton("删除")
                delete_btn.setFixedWidth(50)
                delete_btn.setStyleSheet("background-color: #ef4444; color: white; border: none; border-radius: 4px;")
                delete_btn.clicked.connect(lambda checked, ps=supplier: self.delete_supplier(ps))
                
                btn_layout.addWidget(edit_btn)
                btn_layout.addWidget(delete_btn)
                
                widget = QWidget()
                widget.setLayout(btn_layout)
                self.table.setCellWidget(idx, 7, widget)
                
                # 存储ID用于后续操作
                self.table.setItem(idx, 8, QTableWidgetItem(str(supplier['id'])))
                self.table.setColumnHidden(8, True)
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载产品供应商关联失败: {str(e)}")

    def init_ui(self):
        self.setWindowTitle("管理产品供应商方案")
        self.setMinimumSize(900, 500)
        
        layout = QVBoxLayout()
        
        # 添加供应商按钮
        add_layout = QHBoxLayout()
        add_layout.addStretch()
        
        add_btn = QPushButton("+ 添加供应商方案")
        add_btn.setFixedWidth(130)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        add_btn.clicked.connect(self.add_supplier)
        add_layout.addWidget(add_btn)
        
        layout.addLayout(add_layout)
        
        # 供应商列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["供应商编号", "供应商名称", "工厂编号", "客户", "采购价格", "每箱数量", "默认", "操作", "ID"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 90)
        self.table.setColumnWidth(6, 50)
        self.table.setColumnWidth(7, 120)
        layout.addWidget(self.table)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)

    def add_supplier(self):
        """添加产品供应商关联"""
        dialog = ProductSupplierDetailDialog(self.api_client, self.product_id, oe_number=self.oe_number, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.load_product_suppliers()
            QMessageBox.information(self, "成功", "添加成功")

    def edit_supplier(self, supplier):
        """编辑产品供应商关联"""
        dialog = ProductSupplierDetailDialog(self.api_client, self.product_id, supplier, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.load_product_suppliers()
            QMessageBox.information(self, "成功", "修改成功")

    def delete_supplier(self, supplier):
        """删除产品供应商关联"""
        if QMessageBox.question(self, "确认", f"确定要删除供应商 {supplier['supplier_name']} 的方案吗？") == QMessageBox.Yes:
            try:
                self.api_client.delete_product_supplier(supplier['id'])
                self.load_product_suppliers()
                QMessageBox.information(self, "成功", "删除成功")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败: {str(e)}")
