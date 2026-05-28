"""
订单总表编辑对话框 - 支持快速新增关联模块
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                              QTextEdit, QComboBox, QPushButton, QWidget, QTabWidget,
                              QFormLayout, QGroupBox, QScrollArea, QDoubleSpinBox,
                              QSpinBox, QDateEdit, QCheckBox, QListWidget, QListWidgetItem,
                              QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView)
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
        self.tabs = None  # 标签页引用，用于智能定位
        self.setWindowTitle("编辑订单")
        self.setMinimumSize(900, 700)
        self._setup_ui()
        # 初始化后自动加载历史包装数据（智能回填）
        self._load_history_package_async()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 订单基本信息
        self.tabs.addTab(self._create_order_tab(), "📋 订单信息")
        # 客户信息
        self.tabs.addTab(self._create_customer_tab(), "👤 客户信息")
        # 产品信息
        self.tabs.addTab(self._create_product_tab(), "📦 产品信息")
        # 采购信息（含包装规格）
        self.tabs.addTab(self._create_purchase_tab(), "🏭 采购信息")
        # 付款信息
        self.tabs.addTab(self._create_payment_tab(), "💰 付款信息")
        
        layout.addWidget(self.tabs)
        
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
        # 检查parent是否是MainWindow
        main_window = None
        if self.parent() and hasattr(self.parent(), 'add_product') and hasattr(self.parent(), 'add_customer'):
            main_window = self.parent()
        
        if module_type == "product" and main_window:
            # 调用MainWindow的新增产品窗口
            main_window.add_product()
            # 刷新产品列表
            self._refresh_product_combo()
        elif module_type == "customer" and main_window:
            # 调用MainWindow的新增客户窗口
            main_window.add_customer()
            # 刷新客户列表
            self._refresh_customer_combo()
        else:
            # 使用内置的QuickAddDialog
            dialog = QuickAddDialog(module_type, self.api_client, self)
            if dialog.exec():
                new_id, new_data = dialog.get_result()
                self.new_records[module_type] = {'id': new_id, 'data': new_data}
                QMessageBox.information(self, "成功", f"已新增 {module_type}，ID: {new_id}")
    
    def _refresh_product_combo(self):
        """刷新产品下拉框"""
        try:
            products = self.api_client.get_products() or []
            self.product_combo.clear()
            self.product_combo.addItem("-- 选择产品 --", None)
            for p in products:
                self.product_combo.addItem(f"{p.get('product_code', '')} - {p.get('detail_desc', '')}", p.get('id'))
        except Exception as e:
            print(f"刷新产品列表失败: {e}")
    
    def _refresh_customer_combo(self):
        """刷新客户下拉框"""
        try:
            customers = self.api_client.get_customers() or []
            self.customer_combo.clear()
            self.customer_combo.addItem("-- 选择客户 --", None)
            for c in customers:
                self.customer_combo.addItem(c.get('customer_name', ''), c.get('id'))
        except Exception as e:
            print(f"刷新客户列表失败: {e}")
    
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
        
        # ===== 产品选择 =====
        product_group = QGroupBox("添加产品")
        product_layout = QFormLayout()
        
        product_row = QHBoxLayout()
        self.product_combo = QComboBox()
        self._load_products()
        product_row.addWidget(self.product_combo)
        product_row.addWidget(self._create_quick_add_button("product", "+ 新增产品"))
        product_layout.addRow("选择产品:", product_row)
        
        # 添加按钮
        add_btn = QPushButton("+ 添加到列表")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        add_btn.clicked.connect(self._add_product_to_list)
        product_layout.addRow("", add_btn)
        
        product_group.setLayout(product_layout)
        layout.addWidget(product_group)
        
        # ===== 产品列表 =====
        list_group = QGroupBox("已添加产品列表")
        list_layout = QVBoxLayout()
        
        # 产品表格
        self.product_list_table = QTableWidget()
        self.product_list_table.setColumnCount(6)
        self.product_list_table.setHorizontalHeaderLabels(["产品名称", "OE号", "品牌", "规格", "数量", "操作"])
        self.product_list_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.product_list_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.product_list_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.product_list_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.product_list_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.product_list_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.product_list_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.product_list_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.product_list_table.setColumnWidth(5, 80)
        self.product_list_table.setMinimumHeight(200)
        
        # 初始化产品列表
        self.product_items = []  # 存储产品数据
        
        list_layout.addWidget(self.product_list_table)
        
        # 批量操作按钮
        btn_layout = QHBoxLayout()
        delete_selected_btn = QPushButton("🗑 删除选中")
        delete_selected_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #dc2626; }
        """)
        delete_selected_btn.clicked.connect(self._delete_selected_products)
        btn_layout.addWidget(delete_selected_btn)
        
        clear_all_btn = QPushButton("清空列表")
        clear_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #4b5563; }
        """)
        clear_all_btn.clicked.connect(self._clear_product_list)
        btn_layout.addWidget(clear_all_btn)
        
        btn_layout.addStretch()
        list_layout.addLayout(btn_layout)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # 添加默认显示的产品（如果订单已有产品信息）
        if self.order_data.get('product_name'):
            self._add_product_from_order()
        
        layout.addStretch()
        widget.setLayout(layout)
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        return scroll
    
    def _add_product_from_order(self):
        """从订单数据添加产品到列表"""
        product_item = {
            'name': self.order_data.get('product_name', ''),
            'oe': self.order_data.get('oe_number', ''),
            'brand': self.order_data.get('brand', ''),
            'spec': self.order_data.get('product_spec', ''),
            'quantity': self.order_data.get('quantity', 1),
        }
        self.product_items.append(product_item)
        self._refresh_product_list()
    
    def _add_product_to_list(self):
        """添加产品到列表"""
        selected_id = self.product_combo.currentData()
        if not selected_id:
            QMessageBox.warning(self, "提示", "请先选择产品")
            return
        
        # 获取产品详情
        try:
            product = self.api_client.get(f"/customer-products/{selected_id}")
            if product:
                product_item = {
                    'id': selected_id,
                    'name': product.get('product_name', ''),
                    'oe': product.get('primary_oe', ''),
                    'brand': product.get('brand', ''),
                    'spec': product.get('specifications', ''),
                    'quantity': 1,
                }
                self.product_items.append(product_item)
                self._refresh_product_list()
                QMessageBox.information(self, "成功", "产品已添加到列表")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"添加产品失败: {e}")
    
    def _refresh_product_list(self):
        """刷新产品列表表格"""
        self.product_list_table.setRowCount(0)
        
        for idx, item in enumerate(self.product_items):
            row = self.product_list_table.rowCount()
            self.product_list_table.insertRow(row)
            
            self.product_list_table.setItem(row, 0, QTableWidgetItem(item.get('name', '')))
            self.product_list_table.setItem(row, 1, QTableWidgetItem(item.get('oe', '')))
            self.product_list_table.setItem(row, 2, QTableWidgetItem(item.get('brand', '')))
            self.product_list_table.setItem(row, 3, QTableWidgetItem(item.get('spec', '')))
            self.product_list_table.setItem(row, 4, QTableWidgetItem(str(item.get('quantity', 1))))
            
            # 删除按钮
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
            delete_btn.clicked.connect(lambda checked, i=idx: self._delete_product(i))
            self.product_list_table.setCellWidget(row, 5, delete_btn)
    
    def _delete_product(self, index):
        """删除指定索引的产品"""
        if 0 <= index < len(self.product_items):
            self.product_items.pop(index)
            self._refresh_product_list()
    
    def _delete_selected_products(self):
        """删除选中的产品"""
        selected_rows = set(item.row() for item in self.product_list_table.selectedItems())
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的产品")
            return
        
        # 按索引排序（降序）以便从后向前删除
        sorted_rows = sorted(selected_rows, reverse=True)
        
        # 同时需要计算映射后的实际索引（因为行号和列表索引一一对应）
        for table_row in sorted_rows:
            if table_row < len(self.product_items):
                self.product_items.pop(table_row)
        
        self._refresh_product_list()
    
    def _clear_product_list(self):
        """清空产品列表"""
        if not self.product_items:
            return
        
        reply = QMessageBox.question(self, "确认", "确定要清空所有产品吗？",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.product_items.clear()
            self._refresh_product_list()
    
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
        
        # ========== 包装规格（新增） ==========
        package_group = QGroupBox("📦 包装规格")
        package_layout = QFormLayout()
        
        # 列29: 包装方式
        self.packing_type_combo = QComboBox()
        self.packing_type_combo.addItems(["", "纸箱", "托盘", "木箱", "无"])
        self.packing_type_combo.setCurrentText(self.order_data.get('packing_type', ''))
        package_layout.addRow("包装方式:", self.packing_type_combo)
        
        # 列30: 采购选项/名称
        self.purchase_channel_edit = QLineEdit(self.order_data.get('purchase_channel', ''))
        package_layout.addRow("采购选项/名称:", self.purchase_channel_edit)
        
        # 列32: 工厂编号
        self.factory_code_edit = QLineEdit(self.order_data.get('factory_code', ''))
        package_layout.addRow("工厂编号:", self.factory_code_edit)
        
        # 列33: 纸箱尺寸 (长×宽×高)
        carton_size_layout = QHBoxLayout()
        self.carton_length_edit = QDoubleSpinBox()
        self.carton_length_edit.setRange(0, 9999)
        self.carton_length_edit.setDecimals(1)
        self.carton_length_edit.setSuffix(" cm")
        self.carton_length_edit.setValue(float(self.order_data.get('carton_length_cm', 0) or 0))
        carton_size_layout.addWidget(QLabel("长:"))
        carton_size_layout.addWidget(self.carton_length_edit)
        
        self.carton_width_edit = QDoubleSpinBox()
        self.carton_width_edit.setRange(0, 9999)
        self.carton_width_edit.setDecimals(1)
        self.carton_width_edit.setSuffix(" cm")
        self.carton_width_edit.setValue(float(self.order_data.get('carton_width_cm', 0) or 0))
        carton_size_layout.addWidget(QLabel("宽:"))
        carton_size_layout.addWidget(self.carton_width_edit)
        
        self.carton_height_edit = QDoubleSpinBox()
        self.carton_height_edit.setRange(0, 9999)
        self.carton_height_edit.setDecimals(1)
        self.carton_height_edit.setSuffix(" cm")
        self.carton_height_edit.setValue(float(self.order_data.get('carton_height_cm', 0) or 0))
        carton_size_layout.addWidget(QLabel("高:"))
        carton_size_layout.addWidget(self.carton_height_edit)
        
        package_layout.addRow("纸箱尺寸:", carton_size_layout)
        
        # 列34: 打包规格
        self.units_per_carton_spin = QSpinBox()
        self.units_per_carton_spin.setRange(0, 99999)
        self.units_per_carton_spin.setSuffix(" 个/箱")
        self.units_per_carton_spin.setValue(int(self.order_data.get('units_per_carton', 0) or 0))
        package_layout.addRow("打包规格:", self.units_per_carton_spin)
        
        # 列37: 整箱毛重
        self.gross_weight_edit = QDoubleSpinBox()
        self.gross_weight_edit.setRange(0, 99999)
        self.gross_weight_edit.setDecimals(2)
        self.gross_weight_edit.setSuffix(" kg")
        self.gross_weight_edit.setValue(float(self.order_data.get('gross_weight_kg', 0) or 0))
        package_layout.addRow("整箱毛重:", self.gross_weight_edit)
        
        # 智能回填按钮
        refill_btn_layout = QHBoxLayout()
        refill_btn = QPushButton("🔄 智能回填历史数据")
        refill_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #7c3aed; }
        """)
        refill_btn.clicked.connect(self._load_history_package_async)
        refill_btn_layout.addWidget(refill_btn)
        refill_btn_layout.addStretch()
        package_layout.addRow("", refill_btn_layout)
        
        package_group.setLayout(package_layout)
        layout.addWidget(package_group)
        
        widget.setLayout(layout)
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        return scroll
    
    def set_default_tab(self, tab_index: int):
        """设置默认打开的标签页（智能 Tab 定位）
        
        Args:
            tab_index: 标签页索引 (0-4)
                0: 订单信息
                1: 客户信息
                2: 产品信息
                3: 采购信息
                4: 付款信息
        """
        if self.tabs and 0 <= tab_index < self.tabs.count():
            self.tabs.setCurrentIndex(tab_index)
            print(f"[DEBUG] 智能定位: 打开 Tab{tab_index}")
    
    def _load_history_package_async(self):
        """异步加载历史包装规格数据（智能回填）
        
        防抖机制：
        - 防止重复请求（_loading_history 标志位）
        - 5秒超时保护
        
        适用场景：
        - 对话框初始化时自动调用
        - 用户点击"智能回填"按钮时手动触发
        - 客户或产品字段变更后自动刷新
        """
        import threading
        
        customer_id = self.order_data.get('customer_id')
        product_id = self.order_data.get('product_id')
        
        if not customer_id or not product_id:
            print(f"[INFO] 智能回填: 缺少客户ID或产品ID，跳过")
            return
        
        # 防抖：检查是否正在加载
        if hasattr(self, '_loading_history') and self._loading_history:
            print("[INFO] 智能回填: 正在加载中，请稍候")
            return
        
        self._loading_history = True
        
        print(f"[INFO] 智能回填: 查询客户{customer_id}+产品{product_id}的历史包装数据...")
        
        def fetch_history():
            try:
                result = self.api_client.get_history_package(customer_id, product_id)
                from PySide6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(
                    self, 
                    "_on_history_package_loaded", 
                    Qt.QueuedConnection,
                    [object, type(result)],
                    result
                )
            except Exception as e:
                print(f"[ERROR] 智能回填失败: {e}")
            finally:
                self._loading_history = False
        
        thread = threading.Thread(target=fetch_history, daemon=True)
        thread.start()
        
        # 5秒超时保护
        from PySide6.QtCore import QTimer
        QTimer.singleShot(5000, self._on_history_load_timeout)
    
    def _on_history_load_timeout(self):
        """处理历史包装数据加载超时"""
        if not hasattr(self, '_loading_history'):
            return
        if self._loading_history:
            self._loading_history = False
            print("[WARN] 智能回填: 请求超时（5秒）")
            if self.isVisible():
                QMessageBox.warning(
                    self,
                    "请求超时",
                    "历史包装数据加载超时，请检查网络连接后重试。"
                )
    
    def _on_history_package_loaded(self, result):
        """处理历史包装数据加载完成（主线程回调）
        
        Args:
            result: API返回的历史包装数据
                - found=True + package: 找到历史数据，自动填充
                - found=False: 无历史数据，保持当前值不变
        """
        if not result or not result.get('found'):
            print(f"[INFO] 智能回填: 未找到历史包装数据（首次订单或无记录）")
            QMessageBox.information(
                self, 
                "智能回填", 
                "未找到该客户+产品的历史包装数据\n\n可能原因：\n• 这是首次订单\n• 历史订单未填写包装规格\n\n请手动填写包装规格"
            )
            return
        
        package = result.get('package', {})
        source = result.get('source', '未知')
        created_at = result.get('created_at', '')
        
        print(f"[INFO] 智能回填: 找到历史数据，来源={source}")
        
        # 自动填充表单字段
        if package.get('packing_type') is not None:
            self.packing_type_combo.setCurrentText(str(package['packing_type']))
        
        if package.get('units_per_carton') is not None:
            self.units_per_carton_spin.setValue(int(package['units_per_carton']))
        
        if package.get('carton_length_cm') is not None:
            self.carton_length_edit.setValue(float(package['carton_length_cm']))
        
        if package.get('carton_width_cm') is not None:
            self.carton_width_edit.setValue(float(package['carton_width_cm']))
        
        if package.get('carton_height_cm') is not None:
            self.carton_height_edit.setValue(float(package['carton_height_cm']))
        
        # 显示成功提示
        msg = f"✅ 已从历史订单回填包装规格\n\n"
        msg += f"来源: {source}\n"
        if created_at:
            msg += f"创建时间: {created_at}\n"
        msg += f"\n请核对数据是否正确，必要时可手动修改"
        
        QMessageBox.information(self, "智能回填成功", msg)
    
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
            resp = self.api_client.get("/customer-products", params={"page_size": 500})
            products = resp.get('items', []) if resp and isinstance(resp, dict) else (resp or [])
            self.product_combo.clear()
            self.product_combo.addItem("-- 请选择 --", None)
            for p in products:
                name = p.get('product_name', '') or p.get('primary_oe', '')
                code = p.get('primary_code', '') or ''
                self.product_combo.addItem(f"{code} - {name}", p.get('id'))
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
        """保存数据（含包装规格）"""
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
            'product_name': self.product_name_edit.text() if hasattr(self, 'product_name_edit') else '',
            'product_oe': self.product_oe_edit.text() if hasattr(self, 'product_oe_edit') else '',
            'brand': self.product_brand_edit.text() if hasattr(self, 'product_brand_edit') else '',
            'product_spec': self.product_spec_edit.text() if hasattr(self, 'product_spec_edit') else '',
            'purchase_price': self.purchase_price_edit.value(),
            'shipping_fee': self.shipping_fee_edit.value(),
            'misc_fee': self.misc_fee_edit.value(),
            'supplier_link': self.supplier_link_edit.text(),
            'delivery_date': self.delivery_date_edit.date().toString("yyyy-MM-dd"),
            'customer_prepayment': self.customer_prepayment_edit.value(),
            'remaining_payment': self.remaining_payment_edit.value(),
            'supplier_deposit': self.supplier_deposit_edit.value(),
            'supplier_balance': self.supplier_balance_edit.value(),
            # 添加产品列表
            'product_items': self.product_items,
        }
        
        # 收集包装规格数据
        po_item_id = self.order_data.get('po_item_id')
        if po_item_id:
            package_data = {
                'packing_type': self.packing_type_combo.currentText() or None,
                'purchase_channel': self.purchase_channel_edit.text() or None,
                'factory_code': self.factory_code_edit.text() or None,
                'carton_length_cm': self.carton_length_edit.value() if self.carton_length_edit.value() > 0 else None,
                'carton_width_cm': self.carton_width_edit.value() if self.carton_width_edit.value() > 0 else None,
                'carton_height_cm': self.carton_height_edit.value() if self.carton_height_edit.value() > 0 else None,
                'units_per_carton': self.units_per_carton_spin.value() if self.units_per_carton_spin.value() > 0 else None,
                'gross_weight_kg': self.gross_weight_edit.value() if self.gross_weight_edit.value() > 0 else None,
            }
            
            # 过滤掉None值
            package_data = {k: v for k, v in package_data.items() if v is not None}
            
            # 调用API保存包装规格
            try:
                save_result = self.api_client.save_purchase_item_package(po_item_id, package_data)
                if save_result:
                    print(f"[INFO] 包装规格已保存: po_item_id={po_item_id}")
                    data['package_saved'] = True
                else:
                    reply = QMessageBox.question(
                        self, "包装规格保存失败",
                        "主订单信息已保存，但包装规格保存失败。\n\n是否仍要关闭对话框？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        return
            except Exception as e:
                QMessageBox.critical(
                    self, "保存错误",
                    f"包装规格保存异常:\n\n{str(e)}\n\n主订单信息已保存成功。"
                )
                return
        
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