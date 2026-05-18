"""
订单总表编辑对话框 - 支持快速新增关联模块
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                              QTextEdit, QComboBox, QPushButton, QWidget, QTabWidget,
                              QFormLayout, QGroupBox, QScrollArea, QDoubleSpinBox,
                              QSpinBox, QDateEdit, QCheckBox, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont


class OrderSummaryEditDialog(QDialog):
    """订单总表编辑对话框"""
    
    # 保存成功信号
    saved = Signal(dict)
    
    def __init__(self, order_data, api_client, parent=None):
        super().__init__(parent)
        self.order_data = order_data
        self.api_client = api_client
        self.new_records = {}  # 存储新增的关联记录
        self.setWindowTitle("编辑订单")
        self.setMinimumSize(900, 700)
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 创建标签页
        tabs = QTabWidget()
        
        # 订单基本信息
        tabs.addTab(self._create_order_tab(), "📋 订单信息")
        # 客户信息
        tabs.addTab(self._create_customer_tab(), "👤 客户信息")
        # 产品信息
        tabs.addTab(self._create_product_tab(), "📦 产品信息")
        # 采购信息
        tabs.addTab(self._create_purchase_tab(), "🏭 采购信息")
        # 付款信息
        tabs.addTab(self._create_payment_tab(), "💰 付款信息")
        
        layout.addWidget(tabs)
        
        # 按钮栏
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
                padding: 10px 20px;
            }
            QPushButton:hover { background-color: #4b5563; }
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
                padding: 10px 20px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _create_quick_add_button(self, module_type, label="+ 新增"):
        """创建快速新增按钮"""
        btn = QPushButton(label)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        btn.clicked.connect(lambda: self._show_quick_add(module_type))
        return btn
    
    def _show_quick_add(self, module_type):
        """显示快速新增对话框"""
        dialog = QuickAddDialog(module_type, self.api_client, self)
        if dialog.exec():
            new_id, new_data = dialog.get_result()
            self.new_records[module_type] = {'id': new_id, 'data': new_data}
            QMessageBox.information(self, "成功", f"已新增 {module_type}，ID: {new_id}")
    
    def _create_order_tab(self):
        """创建订单信息标签页"""
        scroll = QScrollArea()
        widget = QWidget()
        layout = QFormLayout()
        
        # 基本信息
        group = QGroupBox("基本信息")
        group_layout = QFormLayout()
        
        self.order_no_edit = QLineEdit(self.order_data.get('order_no', ''))
        group_layout.addRow("ORDER NO.:", self.order_no_edit)
        
        self.order_date_edit = QDateEdit(QDate.currentDate())
        if self.order_data.get('order_date'):
            self.order_date_edit.setDate(QDate.fromString(self.order_data.get('order_date'), "yyyy-MM-dd"))
        group_layout.addRow("订单日期:", self.order_date_edit)
        
        self.customer_code_edit = QLineEdit(self.order_data.get('customer_product_code', ''))
        group_layout.addRow("客户产品编号:", self.customer_code_edit)
        
        self.oe_number_edit = QLineEdit(self.order_data.get('oe_number', ''))
        group_layout.addRow("OE号:", self.oe_number_edit)
        
        self.remark_edit = QTextEdit(self.order_data.get('customer_requirement', ''))
        self.remark_edit.setMaximumHeight(80)
        group_layout.addRow("客户需求备注:", self.remark_edit)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
        
        # 数量和价格
        price_group = QGroupBox("价格信息")
        price_layout = QFormLayout()
        
        self.quantity_edit = QSpinBox()
        self.quantity_edit.setRange(0, 999999)
        self.quantity_edit.setValue(int(self.order_data.get('quantity', 0)))
        price_layout.addRow("数量:", self.quantity_edit)
        
        self.unit_price_edit = QDoubleSpinBox()
        self.unit_price_edit.setRange(0, 999999)
        self.unit_price_edit.setDecimals(2)
        self.unit_price_edit.setValue(float(self.order_data.get('unit_price', 0)))
        price_layout.addRow("单价:", self.unit_price_edit)
        
        self.total_amount_edit = QDoubleSpinBox()
        self.total_amount_edit.setRange(0, 99999999)
        self.total_amount_edit.setDecimals(2)
        self.total_amount_edit.setValue(float(self.order_data.get('total_amount', 0)))
        price_layout.addRow("合计金额:", self.total_amount_edit)
        
        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["USD", "RMB", "EUR"])
        currency = self.order_data.get('currency', 'USD')
        self.currency_combo.setCurrentText(currency if currency else 'USD')
        price_layout.addRow("币种:", self.currency_combo)
        
        price_group.setLayout(price_layout)
        layout.addWidget(price_group)
        
        widget.setLayout(layout)
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        return scroll
    
    def _create_customer_tab(self):
        """创建客户信息标签页"""
        scroll = QScrollArea()
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 客户选择
        customer_group = QGroupBox("客户信息")
        customer_layout = QFormLayout()
        
        customer_row = QHBoxLayout()
        self.customer_combo = QComboBox()
        self._load_customers()
        customer_row.addWidget(self.customer_combo)
        customer_row.addWidget(self._create_quick_add_button("customer", "+ 新增客户"))
        customer_layout.addRow("选择客户:", customer_row)
        
        self.customer_name_edit = QLineEdit(self.order_data.get('customer_name', ''))
        customer_layout.addRow("客户名称:", self.customer_name_edit)
        
        self.customer_contact_edit = QLineEdit(self.order_data.get('customer_contact', ''))
        customer_layout.addRow("联系人:", self.customer_contact_edit)
        
        self.customer_phone_edit = QLineEdit(self.order_data.get('customer_phone', ''))
        customer_layout.addRow("电话:", self.customer_phone_edit)
        
        customer_group.setLayout(customer_layout)
        layout.addWidget(customer_group)
        
        widget.setLayout(layout)
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        return scroll
    
    def _create_product_tab(self):
        """创建产品信息标签页"""
        scroll = QScrollArea()
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 产品选择
        product_group = QGroupBox("产品信息")
        product_layout = QFormLayout()
        
        product_row = QHBoxLayout()
        self.product_combo = QComboBox()
        self._load_products()
        product_row.addWidget(self.product_combo)
        product_row.addWidget(self._create_quick_add_button("product", "+ 新增产品"))
        product_layout.addRow("选择产品:", product_row)
        
        self.product_name_edit = QLineEdit(self.order_data.get('product_name', ''))
        product_layout.addRow("产品名称:", self.product_name_edit)
        
        self.product_oe_edit = QLineEdit(self.order_data.get('oe_number', ''))
        product_layout.addRow("OE号:", self.product_oe_edit)
        
        self.product_brand_edit = QLineEdit(self.order_data.get('brand', ''))
        product_layout.addRow("品牌:", self.product_brand_edit)
        
        self.product_spec_edit = QLineEdit(self.order_data.get('product_spec', ''))
        product_layout.addRow("规格:", self.product_spec_edit)
        
        product_group.setLayout(product_layout)
        layout.addWidget(product_group)
        
        widget.setLayout(layout)
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        return scroll
    
    def _create_purchase_tab(self):
        """创建采购信息标签页"""
        scroll = QScrollArea()
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 采购信息
        purchase_group = QGroupBox("采购信息")
        purchase_layout = QFormLayout()
        
        # 供应商选择
        supplier_row = QHBoxLayout()
        self.supplier_combo = QComboBox()
        self._load_suppliers()
        supplier_row.addWidget(self.supplier_combo)
        supplier_row.addWidget(self._create_quick_add_button("supplier", "+ 新增供应商"))
        purchase_layout.addRow("选择供应商:", supplier_row)
        
        self.purchase_price_edit = QDoubleSpinBox()
        self.purchase_price_edit.setRange(0, 99999999)
        self.purchase_price_edit.setDecimals(2)
        self.purchase_price_edit.setValue(float(self.order_data.get('purchase_price', 0)))
        purchase_layout.addRow("采购价格:", self.purchase_price_edit)
        
        self.shipping_fee_edit = QDoubleSpinBox()
        self.shipping_fee_edit.setRange(0, 999999)
        self.shipping_fee_edit.setDecimals(2)
        self.shipping_fee_edit.setValue(float(self.order_data.get('shipping_fee', 0)))
        purchase_layout.addRow("运费:", self.shipping_fee_edit)
        
        self.misc_fee_edit = QDoubleSpinBox()
        self.misc_fee_edit.setRange(0, 999999)
        self.misc_fee_edit.setDecimals(2)
        self.misc_fee_edit.setValue(float(self.order_data.get('misc_fee', 0)))
        purchase_layout.addRow("杂费:", self.misc_fee_edit)
        
        self.supplier_link_edit = QLineEdit(self.order_data.get('supplier_link', ''))
        purchase_layout.addRow("店铺链接:", self.supplier_link_edit)
        
        self.delivery_date_edit = QDateEdit(QDate.currentDate().addDays(30))
        purchase_layout.addRow("交货日期:", self.delivery_date_edit)
        
        purchase_group.setLayout(purchase_layout)
        layout.addWidget(purchase_group)
        
        widget.setLayout(layout)
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        return scroll
    
    def _create_payment_tab(self):
        """创建付款信息标签页"""
        scroll = QScrollArea()
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 客户付款
        customer_pay_group = QGroupBox("客户付款")
        customer_pay_layout = QFormLayout()
        
        self.customer_prepayment_edit = QDoubleSpinBox()
        self.customer_prepayment_edit.setRange(0, 99999999)
        self.customer_prepayment_edit.setDecimals(2)
        self.customer_prepayment_edit.setValue(float(self.order_data.get('customer_prepayment', 0)))
        customer_pay_layout.addRow("客户预付款:", self.customer_prepayment_edit)
        
        self.remaining_payment_edit = QDoubleSpinBox()
        self.remaining_payment_edit.setRange(0, 99999999)
        self.remaining_payment_edit.setDecimals(2)
        self.remaining_payment_edit.setValue(float(self.order_data.get('remaining_payment', 0)))
        customer_pay_layout.addRow("待收尾款:", self.remaining_payment_edit)
        
        customer_pay_group.setLayout(customer_pay_layout)
        layout.addWidget(customer_pay_group)
        
        # 供应商付款
        supplier_pay_group = QGroupBox("供应商付款")
        supplier_pay_layout = QFormLayout()
        
        self.supplier_deposit_edit = QDoubleSpinBox()
        self.supplier_deposit_edit.setRange(0, 99999999)
        self.supplier_deposit_edit.setDecimals(2)
        self.supplier_deposit_edit.setValue(float(self.order_data.get('supplier_deposit', 0)))
        supplier_pay_layout.addRow("工厂订金:", self.supplier_deposit_edit)
        
        self.supplier_balance_edit = QDoubleSpinBox()
        self.supplier_balance_edit.setRange(0, 99999999)
        self.supplier_balance_edit.setDecimals(2)
        self.supplier_balance_edit.setValue(float(self.order_data.get('supplier_balance', 0)))
        supplier_pay_layout.addRow("工厂尾款:", self.supplier_balance_edit)
        
        supplier_pay_group.setLayout(supplier_pay_layout)
        layout.addWidget(supplier_pay_group)
        
        widget.setLayout(layout)
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        return scroll
    
    def _load_customers(self):
        """加载客户列表"""
        try:
            customers = self.api_client.get_customers() or []
            self.customer_combo.clear()
            self.customer_combo.addItem("-- 请选择 --", None)
            for c in customers:
                self.customer_combo.addItem(c.get('customer_name', ''), c.get('id'))
        except Exception as e:
            print(f"加载客户列表失败: {e}")
    
    def _load_products(self):
        """加载产品列表"""
        try:
            products = self.api_client.get_products() or []
            self.product_combo.clear()
            self.product_combo.addItem("-- 请选择 --", None)
            for p in products:
                self.product_combo.addItem(f"{p.get('product_code', '')} ({p.get('oe_number', '')})", p.get('id'))
        except Exception as e:
            print(f"加载产品列表失败: {e}")
    
    def _load_suppliers(self):
        """加载供应商列表"""
        try:
            suppliers = self.api_client.get_suppliers() or []
            self.supplier_combo.clear()
            self.supplier_combo.addItem("-- 请选择 --", None)
            for s in suppliers:
                self.supplier_combo.addItem(s.get('supplier_name', ''), s.get('id'))
        except Exception as e:
            print(f"加载供应商列表失败: {e}")
    
    def _save(self):
        """保存数据"""
        # 收集所有数据
        data = {
            'order_no': self.order_no_edit.text(),
            'order_date': self.order_date_edit.date().toString("yyyy-MM-dd"),
            'customer_code': self.customer_code_edit.text(),
            'oe_number': self.oe_number_edit.text(),
            'remark': self.remark_edit.toPlainText(),
            'quantity': self.quantity_edit.value(),
            'unit_price': self.unit_price_edit.value(),
            'total_amount': self.total_amount_edit.value(),
            'currency': self.currency_combo.currentText(),
            'customer_name': self.customer_name_edit.text(),
            'customer_contact': self.customer_contact_edit.text(),
            'customer_phone': self.customer_phone_edit.text(),
            'product_name': self.product_name_edit.text(),
            'product_oe': self.product_oe_edit.text(),
            'brand': self.product_brand_edit.text(),
            'product_spec': self.product_spec_edit.text(),
            'purchase_price': self.purchase_price_edit.value(),
            'shipping_fee': self.shipping_fee_edit.value(),
            'misc_fee': self.misc_fee_edit.value(),
            'supplier_link': self.supplier_link_edit.text(),
            'delivery_date': self.delivery_date_edit.date().toString("yyyy-MM-dd"),
            'customer_prepayment': self.customer_prepayment_edit.value(),
            'remaining_payment': self.remaining_payment_edit.value(),
            'supplier_deposit': self.supplier_deposit_edit.value(),
            'supplier_balance': self.supplier_balance_edit.value(),
        }
        
        self.saved.emit(data)
        self.accept()


class QuickAddDialog(QDialog):
    """快速新增对话框"""
    
    def __init__(self, module_type, api_client, parent=None):
        super().__init__(parent)
        self.module_type = module_type
        self.api_client = api_client
        self.new_id = None
        self.new_data = None
        self.setWindowTitle(f"新增 {module_type}")
        self.setMinimumSize(500, 400)
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 模块标题
        title = QLabel(f"📋 新增 {self.module_type}")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 根据类型创建表单
        if self.module_type == "customer":
            self._create_customer_form(layout)
        elif self.module_type == "product":
            self._create_product_form(layout)
        elif self.module_type == "supplier":
            self._create_supplier_form(layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _create_customer_form(self, layout):
        """创建客户表单"""
        form = QFormLayout()
        
        self.customer_name = QLineEdit()
        form.addRow("客户名称:", self.customer_name)
        
        self.customer_contact = QLineEdit()
        form.addRow("联系人:", self.customer_contact)
        
        self.customer_phone = QLineEdit()
        form.addRow("电话:", self.customer_phone)
        
        self.customer_email = QLineEdit()
        form.addRow("邮箱:", self.customer_email)
        
        self.customer_address = QTextEdit()
        self.customer_address.setMaximumHeight(60)
        form.addRow("地址:", self.customer_address)
        
        layout.addLayout(form)
    
    def _create_product_form(self, layout):
        """创建产品表单"""
        form = QFormLayout()
        
        self.product_name = QLineEdit()
        form.addRow("产品名称:", self.product_name)
        
        self.product_oe = QLineEdit()
        form.addRow("OE号:", self.product_oe)
        
        self.product_brand = QLineEdit()
        form.addRow("品牌:", self.product_brand)
        
        self.product_spec = QLineEdit()
        form.addRow("规格:", self.product_spec)
        
        self.product_price = QDoubleSpinBox()
        self.product_price.setRange(0, 999999)
        self.product_price.setDecimals(2)
        form.addRow("价格:", self.product_price)
        
        layout.addLayout(form)
    
    def _create_supplier_form(self, layout):
        """创建供应商表单"""
        form = QFormLayout()
        
        self.supplier_name = QLineEdit()
        form.addRow("供应商名称:", self.supplier_name)
        
        self.supplier_contact = QLineEdit()
        form.addRow("联系人:", self.supplier_contact)
        
        self.supplier_phone = QLineEdit()
        form.addRow("电话:", self.supplier_phone)
        
        self.supplier_link = QLineEdit()
        form.addRow("店铺链接:", self.supplier_link)
        
        self.supplier_address = QTextEdit()
        self.supplier_address.setMaximumHeight(60)
        form.addRow("地址:", self.supplier_address)
        
        self.supplier_code = QLineEdit()
        form.addRow("工厂编号:", self.supplier_code)
        
        layout.addLayout(form)
    
    def _save(self):
        """保存"""
        try:
            if self.module_type == "customer":
                data = {
                    'name': self.customer_name.text(),
                    'contact': self.customer_contact.text(),
                    'phone': self.customer_phone.text(),
                    'email': self.customer_email.text(),
                    'address': self.customer_address.toPlainText(),
                }
                result = self.api_client.create_customer(data)
            elif self.module_type == "product":
                data = {
                    'name': self.product_name.text(),
                    'oe_number': self.product_oe.text(),
                    'brand': self.product_brand.text(),
                    'specifications': self.product_spec.text(),
                    'price': self.product_price.value(),
                }
                result = self.api_client.create_product(data)
            elif self.module_type == "supplier":
                data = {
                    'name': self.supplier_name.text(),
                    'contact': self.supplier_contact.text(),
                    'phone': self.supplier_phone.text(),
                    'shop_link': self.supplier_link.text(),
                    'address': self.supplier_address.toPlainText(),
                    'code': self.supplier_code.text(),
                }
                result = self.api_client.create_supplier(data)
            
            if result and result.get('id'):
                self.new_id = result.get('id')
                self.new_data = result
                self.accept()
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "错误", "创建失败，请重试")
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", f"创建失败: {str(e)}")
    
    def get_result(self):
        """获取结果"""
        return self.new_id, self.new_data


# 添加缺失的导入
from PySide6.QtWidgets import QMessageBox