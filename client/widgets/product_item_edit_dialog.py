# -*- coding: utf-8 -*-
"""
产品项编辑对话框（完整版）

文件：client/widgets/product_item_edit_dialog.py
用途：编辑订单产品项的所有可编辑字段（简单字段内联编辑，复杂字段 Dialog 编辑）

调用方式：
```python
from widgets import ProductItemEditDialog

dialog = ProductItemEditDialog(
    item, products=None, api_client=api_client,
    focus_column=2, has_formal=False, is_purchased=False,
    parent=self
)
if dialog.exec() == QDialog.DialogCode.Accepted:
    updated_item = dialog.get_item()
```
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QDoubleSpinBox, QPushButton, QFormLayout,
    QMessageBox, QDateEdit, QScrollArea, QWidget, QTextEdit,
    QFileDialog, QListWidget, QListWidgetItem, QStackedWidget,
    QMenu, QApplication
)
from PySide6.QtCore import Qt, QDate, QSize, QThread, Signal
from PySide6.QtGui import QPixmap, QIcon
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from product_categories import get_parent_category_options, get_child_category_options, CATEGORIES, PARENT_CATEGORIES


class ImageUploadWorker(QThread):
    """异步图片上传工作线程，上传期间不阻塞 Dialog，允许用户编辑其他字段"""
    finished = Signal(str, bool, str)  # url, success, message

    def __init__(self, api_client, file_path, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.file_path = file_path

    def run(self):
        try:
            url = self.api_client.upload_image(self.file_path)
            self.finished.emit(url, True, "上传成功")
        except Exception as e:
            self.finished.emit("", False, str(e))


class ProductItemEditDialog(QDialog):
    """
    产品项编辑对话框（完整版）

    支持字段：
    - 基础信息：客户产品编号、OE号、客户需求备注、产品名称、图片、客户型号、产品特性
    - 数量与日期：数量、交货日期
    - 财务：单价、客户预付款、待收尾款、运费、杂费
    - 包装规格：包装方式、采购选项/名称、产品细节、纸箱尺寸、打包规格、整箱毛重
    - 采购/供应商（锁定显示）：工厂简称、店铺链接、工厂编号、品牌、采购价格、工厂订金、工厂尾款、开票情况
    - 客户回复（预留接口）

    状态锁定：
    - has_formal=True: 锁定产品基本信息
    - is_purchased=True: 锁定产品基本信息 + 交货日期 + 包装规格
    """

    COLUMN_TO_FIELD = {
        2: "customer_code_edit",
        3: "oe_number_edit",
        4: "remark_edit",
        5: "product_name_edit",
        6: "image_path_label",
        7: "customer_model_edit",
        8: "product_feature_edit",
        9: "quantity_spin",
        10: "unit_price_spin",
        13: "customer_prepayment_spin",
        14: "remaining_payment_spin",
        18: "shipping_fee_spin",
        19: "misc_fee_spin",
        23: "delivery_date_edit",
        29: "packaging_combo",
        30: "purchase_option_name_edit",
        31: "product_detail_edit",
        33: "carton_length_cm_spin",
        34: "units_per_carton_spin",
        35: "cartons_per_unit_spin",
        37: "carton_gross_weight_spin",
    }

    def __init__(self, item, products=None, api_client=None,
                 focus_column=None, has_formal=False, is_purchased=False,
                 customer_code=None, parent=None):
        super().__init__(parent)
        self.item = item.copy() if item else {}
        self.products = products or []
        self.api_client = api_client
        self.focus_column = focus_column
        self.has_formal = has_formal
        self.is_purchased = is_purchased
        self.customer_code = customer_code
        self.setWindowTitle("编辑产品")
        self.resize(1024, 1000)
        self._editors = {}

        # 2026-07-03 新增：关联客户产品信息（图片、类目、副图）
        self.customer_product = None
        self.categories = []
        self._load_customer_product_and_categories()

        self.image_path = self.item.get("image_url") or self.item.get("default_image_url", "")
        if self.customer_product and not self.image_path:
            self.image_path = self.customer_product.get("image_url", "")
        self.sub_images = []
        if self.customer_product:
            self.sub_images = list(self.customer_product.get("sub_images") or [])

        self.init_ui()
        self._apply_locks()
        self._apply_focus()

    def _load_customer_product_and_categories(self):
        """加载关联客户产品及类目列表"""
        if not self.api_client:
            return
        product_id = self.item.get("product_id")
        if product_id:
            try:
                self.customer_product = self.api_client.get_customer_product_by_id(product_id)
            except Exception as e:
                print(f"[WARN] ProductItemEditDialog: 加载客户产品失败: {e}")
        try:
            self.categories = self.api_client.get_product_categories() or []
        except Exception as e:
            print(f"[WARN] ProductItemEditDialog: 加载类目失败: {e}")

    def init_ui(self):
        """初始化完整 UI"""
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)

        # 产品下拉选择（可选）
        if self.products:
            product_layout = QHBoxLayout()
            product_layout.addWidget(QLabel("选择产品:"))
            self.product_combo = QComboBox()
            self.product_combo.addItem("-- 请选择 --", None)
            for p in self.products:
                product_name = p.get('detail_desc', '') or p.get('name', '')
                self.product_combo.addItem(product_name, p.get('id'))
            product_layout.addWidget(self.product_combo)
            layout.addLayout(product_layout)
            self.product_combo.currentIndexChanged.connect(self._on_product_selected)

        # 基础信息
        layout.addWidget(QLabel("<b>基础信息</b>"))
        base_form = QFormLayout()
        self._add_line_edit(base_form, "customer_code", "客户产品编号", self.item.get("customer_code", ""))
        self._add_line_edit(base_form, "oe_number", "OE号", self.item.get("oe_number", ""))
        self._add_line_edit(base_form, "remark", "客户需求/产品备注", self.item.get("remark", ""))
        self._add_line_edit(base_form, "product_name", "产品名称", self.item.get("product_name", self.item.get("detail_desc", "")))
        self._add_image_field(layout)
        self._add_sub_images_field(layout)
        # 客户型号：带自动生成编号按钮
        model_layout = QHBoxLayout()
        model_edit = QLineEdit(str(self.item.get("customer_model", "") or ""))
        model_edit.setObjectName("customer_model_edit")
        model_layout.addWidget(model_edit)
        auto_code_btn = QPushButton("自动生成编号")
        auto_code_btn.setToolTip("根据 客户编号 + 客户型号 自动生成客户产品编号")
        auto_code_btn.clicked.connect(self._auto_generate_customer_code)
        model_layout.addWidget(auto_code_btn)
        base_form.addRow("客户型号:", model_layout)
        self._editors["customer_model"] = model_edit

        # 颜色：优先从 PI item 读取，其次关联客户产品
        color_value = self.item.get("color")
        if not color_value and self.customer_product:
            color_value = self.customer_product.get("color")
        self._add_line_edit(base_form, "color", "颜色", color_value or "")
        self._add_line_edit(base_form, "product_feature", "产品特性", self.item.get("product_feature", ""))
        self._add_category_field(base_form)
        layout.addLayout(base_form)

        # 数量与日期
        layout.addWidget(QLabel("<b>数量与日期</b>"))
        qty_form = QFormLayout()
        self._add_spin(qty_form, "quantity", "数量", self.item.get("quantity", 0))
        self._add_date(qty_form, "delivery_date", "交货日期", self.item.get("delivery_date"))
        layout.addLayout(qty_form)

        # 财务
        layout.addWidget(QLabel("<b>财务</b>"))
        fin_form = QFormLayout()
        self._add_spin(fin_form, "unit_price", "单价", self.item.get("unit_price", 0))
        self._add_spin(fin_form, "customer_prepayment", "客户预付款", self.item.get("customer_prepayment", 0))
        self._add_spin(fin_form, "remaining_payment", "待收尾款", self.item.get("remaining_payment", 0))
        self._add_spin(fin_form, "shipping_fee", "运费", self.item.get("shipping_fee", 0))
        self._add_spin(fin_form, "misc_fee", "杂费", self.item.get("misc_fee", 0))
        layout.addLayout(fin_form)

        # 包装规格
        layout.addWidget(QLabel("<b>包装规格</b>"))
        pack_form = QFormLayout()
        self._add_combo(pack_form, "packaging", "包装方式", ["1件/箱", "多件/箱", "1件多箱"], self.item.get("packaging", ""), editable=False)

        # 包装参数：随包装方式切换显示不同输入项
        self._packaging_stack = QStackedWidget()
        # 0: 1件/箱（无需额外输入，显示提示文字）
        no_input_page = QWidget()
        no_input_layout = QHBoxLayout(no_input_page)
        no_input_layout.setContentsMargins(0, 0, 0, 0)
        no_input_layout.addWidget(QLabel("件数固定为1，箱数=数量"))
        self._packaging_stack.addWidget(no_input_page)
        # 1: 多件/箱（每箱件数）
        multi_page = QWidget()
        multi_layout = QHBoxLayout(multi_page)
        multi_layout.setContentsMargins(0, 0, 0, 0)
        self._add_inline_spin(multi_layout, "units_per_carton", "每箱件数", self.item.get("units_per_carton", 0))
        multi_layout.addWidget(QLabel("件/箱"))
        multi_layout.addSpacing(20)
        self._add_inline_spin(multi_layout, "carton_count", "箱数", self.item.get("carton_count", 0))
        multi_layout.addWidget(QLabel("箱"))
        self._packaging_stack.addWidget(multi_page)
        # 2: 1件多箱（每件箱数）
        multi_box_page = QWidget()
        multi_box_layout = QHBoxLayout(multi_box_page)
        multi_box_layout.setContentsMargins(0, 0, 0, 0)
        multi_box_layout.addWidget(QLabel("件数固定为1，"))
        self._add_inline_spin(multi_box_layout, "cartons_per_unit", "每件箱数", self.item.get("cartons_per_unit", 0))
        multi_box_layout.addWidget(QLabel("箱/件"))
        self._packaging_stack.addWidget(multi_box_page)
        pack_form.addRow("包装参数:", self._packaging_stack)

        self._add_line_edit(pack_form, "purchase_option_name", "采购选项/名称", self.item.get("purchase_option_name", ""))
        self._add_line_edit(pack_form, "product_detail", "产品细节", self.item.get("product_detail", ""))

        # 纸箱尺寸：长/宽/高三个输入
        size_layout = QHBoxLayout()
        size_layout.setSpacing(5)
        l, w, h = self._parse_carton_size(self.item.get("carton_size", ""))
        self._add_inline_spin(size_layout, "carton_length_cm", "长", l)
        self._add_inline_spin(size_layout, "carton_width_cm", "宽", w)
        self._add_inline_spin(size_layout, "carton_height_cm", "高", h)
        size_layout.addWidget(QLabel("cm"))
        pack_form.addRow("纸箱尺寸:", size_layout)

        # 体积显示
        self.volume_label = QLabel("单箱体积: -  预估总体积: -")
        pack_form.addRow("体积:", self.volume_label)

        self._add_line_edit(pack_form, "pack_spec", "打包规格", self.item.get("pack_spec", ""))
        self._editors["pack_spec"].setReadOnly(True)
        self._editors["pack_spec"].setToolTip("打包规格根据包装方式、件数、箱数自动回填")
        self._add_spin(pack_form, "carton_gross_weight", "整箱毛重", self.item.get("carton_gross_weight", 0))
        layout.addLayout(pack_form)

        # 纸箱尺寸变化时自动计算体积
        for key in ("carton_length_cm", "carton_width_cm", "carton_height_cm"):
            self._editors[key].valueChanged.connect(self._update_volume_display)

        # 包装方式变化时自动调整箱数/件数/打包规格
        self._editors["packaging"].currentTextChanged.connect(self._on_packaging_changed)
        self._editors["units_per_carton"].valueChanged.connect(self._on_units_per_carton_changed)
        self._editors["carton_count"].valueChanged.connect(self._update_pack_spec_and_volume)
        self._editors["cartons_per_unit"].valueChanged.connect(self._on_cartons_per_unit_changed)
        self._editors["quantity"].valueChanged.connect(self._on_quantity_changed)
        # 初始化时设置包装参数页，不覆盖已有值
        self._init_packaging_stack()
        self._update_pack_spec_and_volume()
        self._update_volume_display()

        # 采购/供应商 Area（锁定显示）
        layout.addWidget(QLabel("<b>采购/供应商信息</b>"))
        supplier_form = QFormLayout()
        self._add_readonly_line(supplier_form, "supplier_name", "工厂简称", self.item.get("supplier_name", ""))
        self._add_readonly_line(supplier_form, "shop_url", "店铺链接", self.item.get("shop_url", ""))
        self._add_readonly_line(supplier_form, "factory_code", "工厂编号", self.item.get("factory_code", ""))
        self._add_readonly_line(supplier_form, "brand", "品牌", self.item.get("brand", ""))
        self._add_readonly_spin(supplier_form, "purchase_price", "采购价格", self.item.get("purchase_price", 0))
        self._add_readonly_spin(supplier_form, "factory_deposit", "工厂订金", self.item.get("factory_deposit", 0))
        self._add_readonly_spin(supplier_form, "factory_balance", "工厂尾款", self.item.get("factory_balance", 0))
        self._add_readonly_line(supplier_form, "invoice_status", "开票情况", self.item.get("invoice_status", ""))
        layout.addLayout(supplier_form)

        # 采购/供应商操作按钮
        btn_layout = QHBoxLayout()
        purchase_btn = QPushButton("采购 Dialog")
        purchase_btn.clicked.connect(self._open_purchase_dialog)
        btn_layout.addWidget(purchase_btn)

        self.change_supplier_btn = QPushButton("更换供应商 Dialog")
        self.change_supplier_btn.setEnabled(self.is_purchased)
        self.change_supplier_btn.setToolTip("尚未生成采购单" if not self.is_purchased else "更换供应商将重新生成采购单")
        self.change_supplier_btn.clicked.connect(self._on_change_supplier)
        btn_layout.addWidget(self.change_supplier_btn)
        layout.addLayout(btn_layout)

        # 客户回复 Area（预留接口）
        layout.addWidget(QLabel("<b>客户回复</b>"))
        self.reply_input = QTextEdit()
        self.reply_input.setPlaceholderText("输入新回复（当前仅本地记录）...")
        self.reply_input.setMaximumHeight(80)
        layout.addWidget(self.reply_input)
        add_reply_btn = QPushButton("添加回复")
        add_reply_btn.clicked.connect(self._add_reply)
        layout.addWidget(add_reply_btn)

        # 保存/取消
        btn_layout2 = QHBoxLayout()
        btn_layout2.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout2.addWidget(cancel_btn)
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
        btn_layout2.addWidget(save_btn)
        layout.addLayout(btn_layout2)

        scroll.setWidget(container)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

    # ------------------------------------------------------------------
    # 字段辅助方法
    # ------------------------------------------------------------------
    def _add_line_edit(self, form, key, label, value):
        edit = QLineEdit(str(value if value is not None else ""))
        edit.setObjectName(key + "_edit")
        form.addRow(f"{label}:", edit)
        self._editors[key] = edit

    def _add_spin(self, form, key, label, value):
        spin = QDoubleSpinBox()
        spin.setRange(0, 99999999)
        spin.setDecimals(4)
        spin.setValue(float(value or 0))
        spin.setObjectName(key + "_spin")
        form.addRow(f"{label}:", spin)
        self._editors[key] = spin

    def _add_inline_spin(self, layout, key, label, value):
        """在水平布局中添加带标签的数字输入框"""
        layout.addWidget(QLabel(f"{label}:"))
        spin = QDoubleSpinBox()
        spin.setRange(0, 99999999)
        spin.setDecimals(2)
        spin.setValue(float(value or 0))
        spin.setObjectName(key + "_spin")
        spin.setMaximumWidth(140)
        spin.setMinimumWidth(100)
        layout.addWidget(spin)
        self._editors[key] = spin

    def _parse_carton_size(self, size_str: str):
        """解析纸箱尺寸字符串，如 '50x40x30cm' -> (50, 40, 30)"""
        import re
        if not size_str:
            return 0, 0, 0
        nums = re.findall(r"\d+(?:\.\d+)?", str(size_str))
        if len(nums) >= 3:
            try:
                return float(nums[0]), float(nums[1]), float(nums[2])
            except (ValueError, TypeError):
                pass
        return 0, 0, 0

    def _add_date(self, form, key, label, value):
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("yyyy-MM-dd")
        if value:
            from datetime import datetime
            if isinstance(value, str):
                value = datetime.strptime(value[:10], "%Y-%m-%d")
            date_edit.setDate(QDate(value.year, value.month, value.day))
        else:
            date_edit.setDate(QDate.currentDate())
        date_edit.setObjectName(key + "_edit")
        form.addRow(f"{label}:", date_edit)
        self._editors[key] = date_edit

    def _add_combo(self, form, key, label, options, value, editable=True):
        combo = QComboBox()
        combo.addItems(options)
        combo.setEditable(editable)
        combo.blockSignals(True)  # 阻止 setCurrentIndex 触发 currentTextChanged
        idx = combo.findText(str(value or ""))
        if idx >= 0:
            combo.setCurrentIndex(idx)
        elif editable:
            combo.setCurrentText(str(value or ""))
        combo.blockSignals(False)
        combo.setObjectName(key + "_combo")
        form.addRow(f"{label}:", combo)
        self._editors[key] = combo

    def _add_category_field(self, form):
        """添加两级产品类目编辑字段（大类/子类，两个字段都有内容则锁定）"""
        self.category_widget = QWidget()
        category_layout = QHBoxLayout(self.category_widget)
        category_layout.setContentsMargins(0, 0, 0, 0)

        self.category_level1 = QComboBox()
        self.category_level1.setMinimumWidth(120)
        self.category_level1.addItem("-- 请选择大类 --", 0)
        for code, name in get_parent_category_options():
            self.category_level1.addItem(name, code)
        self.category_level1.currentIndexChanged.connect(self._on_category_level1_changed)
        category_layout.addWidget(self.category_level1)

        self.category_level2 = QComboBox()
        self.category_level2.setMinimumWidth(120)
        self.category_level2.addItem("-- 请选择子类 --", 0)
        category_layout.addWidget(self.category_level2)

        # 编辑模式下回填类目
        if self.customer_product:
            current_category_id = self.customer_product.get("category_id")
            if current_category_id:
                parent_code = None
                for cat in CATEGORIES:
                    if cat.get("code") == current_category_id:
                        parent_code = cat.get("parent_code")
                        break
                if parent_code:
                    # 设置大类（断开信号避免级联清空）
                    self.category_level1.currentIndexChanged.disconnect()
                    for i in range(self.category_level1.count()):
                        if self.category_level1.itemData(i) == parent_code:
                            self.category_level1.setCurrentIndex(i)
                            break
                    self.category_level1.currentIndexChanged.connect(self._on_category_level1_changed)
                    # 填充子类
                    self.category_level2.clear()
                    self.category_level2.addItem("-- 请选择子类 --", 0)
                    for code, name in get_child_category_options(parent_code):
                        self.category_level2.addItem(name, code)
                    # 设置子类
                    for i in range(self.category_level2.count()):
                        if self.category_level2.itemData(i) == current_category_id:
                            self.category_level2.setCurrentIndex(i)
                            break

        # 应用锁定规则
        self._apply_category_lock()

        form.addRow("产品类目:", self.category_widget)

    def _on_category_level1_changed(self, index: int):
        """大类变化时级联更新子类选项"""
        parent_code = self.category_level1.currentData()
        self.category_level2.clear()
        self.category_level2.addItem("-- 请选择子类 --", 0)
        if parent_code and parent_code != 0:
            for code, name in get_child_category_options(parent_code):
                self.category_level2.addItem(name, code)

    def _apply_category_lock(self):
        """大类、子类都有实际内容时锁定，不可再次编辑"""
        level1_code = self.category_level1.currentData()
        level2_code = self.category_level2.currentData()
        has_content = bool(level1_code and level1_code != 0 and level2_code and level2_code != 0)
        if has_content:
            self.category_level1.setEnabled(False)
            self.category_level2.setEnabled(False)
            tooltip = "产品类目已设置，不可再次修改"
            self.category_level1.setToolTip(tooltip)
            self.category_level2.setToolTip(tooltip)


    def _add_image_field(self, layout):
        img_layout = QHBoxLayout()
        img_layout.addWidget(QLabel("主图:"))

        self.image_path_label = QLabel()
        '''self.image_path_label.setWordWrap(True)'''
        self.image_path_label.setStyleSheet("border: 2px dashed #d1d5db; background-color: #f9fafb;")
        self.image_path_label.setAlignment(Qt.AlignCenter)
        self.image_path_label.setFixedSize(100, 100)
        
        # 2026-07-03 新增：右键菜单查看大图
        self.image_path_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.image_path_label.customContextMenuRequested.connect(self._show_image_context_menu)
        
        if self.image_path:
            self._load_image_async(self.image_path)
        else:
            self.image_path_label.setText("无图片")
        img_layout.addWidget(self.image_path_label)
        upload_btn = QPushButton("上传主图")
        upload_btn.clicked.connect(self._upload_image)
        img_layout.addWidget(upload_btn)
        clear_btn = QPushButton("清除主图")
        clear_btn.clicked.connect(self._clear_image)
        img_layout.addWidget(clear_btn)
        layout.addLayout(img_layout)
    def _load_image_async(self, url):
        """异步加载主图"""
        if not hasattr(self, 'image_path_label') or not self.image_path_label:
            return
        try:
            if url.startswith("http"):
                import urllib.request
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = response.read()
                pixmap = QPixmap()
                pixmap.loadFromData(data)
            else:
                pixmap = QPixmap(url)
            
            if not pixmap.isNull():
                scaled = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_path_label.setPixmap(scaled)
                self.image_path_label.setText("")
            else:
                self.image_path_label.setText("加载失败")
        except Exception as e:
            print(f"[ERROR] 加载主图失败: {e}")
            self.image_path_label.setText("加载失败")

    def _show_image_context_menu(self, pos):
        """图片右键菜单：查看大图"""
        if not self.image_path:
            return
        
        menu = QMenu(self)
        view_action = menu.addAction("查看大图")
        action = menu.exec(self.image_path_label.mapToGlobal(pos))
        if action == view_action:
            self._show_full_size_image()

    def _show_full_size_image(self):
        """在新窗口中显示大图"""
        if not self.image_path:
            return
        
        try:
            # 加载原图
            if self.image_path.startswith("http"):
                import urllib.request
                req = urllib.request.Request(self.image_path, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = response.read()
                pixmap = QPixmap()
                pixmap.loadFromData(data)
            else:
                pixmap = QPixmap(self.image_path)
            
            if pixmap.isNull():
                QMessageBox.warning(self, "错误", "无法加载图片")
                return
            
            # 创建大图窗口
            dialog = QDialog(self)
            dialog.setWindowTitle("查看大图")
            layout = QVBoxLayout(dialog)
            
            # 计算适应屏幕的尺寸
            screen = QApplication.primaryScreen()
            screen_rect = screen.availableGeometry()
            max_w = min(pixmap.width(), screen_rect.width() - 100)
            max_h = min(pixmap.height(), screen_rect.height() - 100)
            scaled = pixmap.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            label = QLabel()
            label.setPixmap(scaled)
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
            
            # 关闭按钮
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)
            
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载图片失败: {e}")

    def _add_sub_images_field(self, layout):
        """添加附图（副图）编辑区域"""
        layout.addWidget(QLabel("<b>附图</b>"))
        self.sub_images_list = QListWidget()
        self.sub_images_list.setViewMode(QListWidget.IconMode)
        self.sub_images_list.setIconSize(QSize(80, 80))
        self.sub_images_list.setSpacing(10)
        self.sub_images_list.setMaximumHeight(140)
        self._refresh_sub_images_list()
        layout.addWidget(self.sub_images_list)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ 添加附图")
        add_btn.clicked.connect(self._upload_sub_image)
        btn_layout.addWidget(add_btn)
        remove_btn = QPushButton("- 删除选中附图")
        remove_btn.clicked.connect(self._remove_selected_sub_image)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _refresh_sub_images_list(self):
        """刷新附图列表显示"""
        self.sub_images_list.clear()
        for url in self.sub_images:
            item = QListWidgetItem()
            # 尝试加载缩略图
            pixmap = QPixmap()
            try:
                if url.startswith("http"):
                    import urllib.request
                    data = urllib.request.urlopen(url, timeout=5).read()
                    pixmap.loadFromData(data)
                else:
                    pixmap.load(url)
            except Exception:
                pass
            if not pixmap.isNull():
                item.setIcon(QIcon(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            else:
                item.setText("[图片]")
            item.setToolTip(url)
            item.setData(Qt.UserRole, url)
            item.setSizeHint(QSize(90, 90))
            self.sub_images_list.addItem(item)

    def _add_readonly_line(self, form, key, label, value):
        edit = QLineEdit(str(value if value is not None else ""))
        edit.setReadOnly(True)
        edit.setStyleSheet("background-color: #f3f4f6;")
        edit.setObjectName(key + "_display")
        form.addRow(f"{label}:", edit)
        self._editors[key] = edit

    def _add_readonly_spin(self, form, key, label, value):
        spin = QDoubleSpinBox()
        spin.setRange(0, 99999999)
        spin.setDecimals(4)
        spin.setValue(float(value or 0))
        spin.setReadOnly(True)
        spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        spin.setStyleSheet("background-color: #f3f4f6;")
        spin.setObjectName(key + "_display")
        form.addRow(f"{label}:", spin)
        self._editors[key] = spin

    # ------------------------------------------------------------------
    # 锁定与高亮
    # ------------------------------------------------------------------
    def _apply_locks(self):
        """根据正式 PI / 采购状态锁定字段"""
        if self.has_formal:
            for key in ["customer_code", "oe_number", "remark", "product_name",
                        "customer_model", "product_feature", "quantity"]:
                editor = self._editors.get(key)
                if editor:
                    editor.setEnabled(False)
        if self.is_purchased:
            for key in ["quantity", "delivery_date", "packaging",
                        "purchase_option_name", "product_detail",
                        "carton_length_cm", "carton_width_cm", "carton_height_cm",
                        "pack_spec", "carton_gross_weight",
                        "units_per_carton", "carton_count", "cartons_per_unit"]:
                editor = self._editors.get(key)
                if editor:
                    editor.setEnabled(False)

    def _apply_focus(self):
        """根据触发列高亮对应字段"""
        if self.focus_column is None:
            return
        widget_name = self.COLUMN_TO_FIELD.get(self.focus_column)
        if not widget_name:
            return
        # image_path_label 是 QLabel，setFocus/setStyleSheet 可用
        editor = getattr(self, widget_name, None)
        if not editor:
            return
        editor.setStyleSheet("border: 2px solid #f59e0b; background-color: #fffbeb;")
        editor.setFocus()
        if isinstance(editor, QComboBox):
            editor.showPopup()
        elif isinstance(editor, QDateEdit):
            editor.calendarWidget().showSelectedDate()

    # ------------------------------------------------------------------
    # 事件处理
    # ------------------------------------------------------------------
    def _update_packaging_stack(self, packaging: str):
        """切换包装参数页：根据包装方式显示/隐藏不同的输入框"""
        import math
        qty = self._editors.get("quantity", QDoubleSpinBox()).value()
        upc_spin = self._editors.get("units_per_carton")
        carton_spin = self._editors.get("carton_count")
        if not upc_spin or not carton_spin:
            return

        if packaging == "1件/箱":
            # 件数固定1，箱数=数量（由数量变化驱动）
            self._packaging_stack.setCurrentIndex(0)
            upc_spin.setValue(1)
            carton_spin.setValue(int(qty) if qty > 0 else 0)
        elif packaging == "多件/箱":
            # 切换到"多件/箱"：保留 units_per_carton 原值，箱数=ceil(数量/件数)
            self._packaging_stack.setCurrentIndex(1)
            if qty > 0 and upc_spin.value() > 0:
                carton_spin.setValue(math.ceil(qty / upc_spin.value()))
            elif qty > 0:
                carton_spin.setValue(math.ceil(qty))
        elif packaging == "1件多箱":
            # 切换到"1件多箱"：显示第2页，units_per_carton固定1，总箱数=数量×每件箱数
            self._packaging_stack.setCurrentIndex(2)
            upc_spin.setValue(1)
            cpu_spin = self._editors.get("cartons_per_unit")
            cpu = int(cpu_spin.value()) if cpu_spin and cpu_spin.value() > 0 else 1
            carton_spin.setValue(int(qty * cpu) if qty > 0 else 0)

        self._update_pack_spec_and_volume()

    def _on_packaging_changed(self, text: str):
        """用户切换包装方式：重置并切换参数输入页"""
        self._update_packaging_stack(text)

    def _init_packaging_stack(self):
        """初始化包装参数页：根据当前包装方式显示对应页面"""
        packaging = self._editors.get("packaging", QComboBox()).currentText()
        if not packaging:
            return
        if packaging == "1件/箱":
            self._packaging_stack.setCurrentIndex(0)
        elif packaging == "多件/箱":
            self._packaging_stack.setCurrentIndex(1)
        elif packaging == "1件多箱":
            self._packaging_stack.setCurrentIndex(2)
            # 打开已有数据时，按数量×每件箱数重新校准总箱数，避免旧脏数据导致显示/保存错误
            qty = self._editors.get("quantity", QDoubleSpinBox()).value()
            cpu_spin = self._editors.get("cartons_per_unit")
            carton_spin = self._editors.get("carton_count")
            if cpu_spin and carton_spin and qty > 0 and cpu_spin.value() > 0:
                carton_spin.blockSignals(True)
                carton_spin.setValue(int(qty * cpu_spin.value()))
                carton_spin.blockSignals(False)

    def _on_units_per_carton_changed(self, value: float):
        """多件/箱模式下，件数变化时自动计算箱数并回填打包规格"""
        import math
        packaging = self._editors.get("packaging", QComboBox()).currentText()
        if packaging != "多件/箱":
            return
        qty = self._editors.get("quantity", QDoubleSpinBox()).value()
        carton_spin = self._editors.get("carton_count")
        if not carton_spin:
            return
        if qty > 0 and value > 0:
            carton_spin.blockSignals(True)
            carton_spin.setValue(math.ceil(qty / value))
            carton_spin.blockSignals(False)
        self._update_pack_spec_and_volume()

    def _on_quantity_changed(self, value: float):
        """数量变化时，同步各包装方式下的总箱数"""
        import math
        packaging = self._editors.get("packaging", QComboBox()).currentText()
        carton_spin = self._editors.get("carton_count")
        upc_spin = self._editors.get("units_per_carton")
        cpu_spin = self._editors.get("cartons_per_unit")
        if not carton_spin:
            return
        if packaging == "1件/箱":
            carton_spin.blockSignals(True)
            carton_spin.setValue(int(value) if value > 0 else 0)
            carton_spin.blockSignals(False)
        elif packaging == "多件/箱" and upc_spin and upc_spin.value() > 0 and value > 0:
            carton_spin.blockSignals(True)
            carton_spin.setValue(math.ceil(value / upc_spin.value()))
            carton_spin.blockSignals(False)
        elif packaging == "1件多箱" and cpu_spin and cpu_spin.value() > 0 and value > 0:
            carton_spin.blockSignals(True)
            carton_spin.setValue(int(value * cpu_spin.value()))
            carton_spin.blockSignals(False)
        self._update_pack_spec_and_volume()

    def _update_pack_spec_and_volume(self):
        """根据包装方式回填打包规格，并触发体积显示刷新"""
        packaging = self._editors.get("packaging", QComboBox()).currentText()
        upc_spin = self._editors.get("units_per_carton")
        carton_spin = self._editors.get("carton_count")
        pack_spec_edit = self._editors.get("pack_spec")
        if not upc_spin or not carton_spin or not pack_spec_edit:
            return

        upc = int(upc_spin.value()) if upc_spin.value() > 0 else 1
        carton = int(carton_spin.value()) if carton_spin.value() > 0 else 1

        if packaging == "1件/箱":
            pack_spec_edit.setText("1pcs/ctn")
        elif packaging == "多件/箱":
            pack_spec_edit.setText(f"{upc}pcs/ctn")
        elif packaging == "1件多箱":
            cpu_spin = self._editors.get("cartons_per_unit")
            cpu = int(cpu_spin.value()) if cpu_spin and cpu_spin.value() > 0 else 1
            pack_spec_edit.setText(f"1pcs/{cpu}ctn")

        self._update_volume_display()

    def _on_cartons_per_unit_changed(self, value: float):
        """1件多箱模式下，每件箱数变化时同步总箱数并刷新体积"""
        packaging = self._editors.get("packaging", QComboBox()).currentText()
        if packaging == "1件多箱":
            qty = self._editors.get("quantity", QDoubleSpinBox()).value()
            carton_spin = self._editors.get("carton_count")
            if carton_spin and qty > 0:
                carton_spin.blockSignals(True)
                carton_spin.setValue(int(qty * value) if value > 0 else 0)
                carton_spin.blockSignals(False)
        self._update_pack_spec_and_volume()
        self._update_volume_display()

    def _update_volume_display(self):
        """根据纸箱尺寸与总箱数计算并显示体积"""
        import math
        l_spin = self._editors.get("carton_length_cm")
        w_spin = self._editors.get("carton_width_cm")
        h_spin = self._editors.get("carton_height_cm")
        carton_spin = self._editors.get("carton_count")
        cpu_spin = self._editors.get("cartons_per_unit")
        qty_spin = self._editors.get("quantity")
        packaging_combo = self._editors.get("packaging")
        if not l_spin or not w_spin or not h_spin:
            return

        l = l_spin.value()
        w = w_spin.value()
        h = h_spin.value()
        qty = int(qty_spin.value()) if qty_spin and qty_spin.value() > 0 else 0
        packaging = packaging_combo.currentText() if packaging_combo else ""

        # 根据不同包装方式计算总箱数
        if packaging == "1件多箱" and qty > 0:
            cpu = int(cpu_spin.value()) if cpu_spin and cpu_spin.value() > 0 else 1
            total_cartons = cpu * qty
        elif packaging == "多件/箱":
            total_cartons = int(carton_spin.value()) if carton_spin and carton_spin.value() > 0 else 0
        else:
            total_cartons = int(carton_spin.value()) if carton_spin and carton_spin.value() > 0 else 0

        if l > 0 and w > 0 and h > 0:
            single_m3 = (l * w * h) / 1_000_000
            total_m3 = single_m3 * total_cartons
            self.volume_label.setText(
                f"单箱体积: {single_m3:.4f} m³  预估总体积: {total_m3:.4f} m³"
            )
        else:
            self.volume_label.setText("单箱体积: -  预估总体积: -")

    def _on_product_selected(self, index):
        """选择产品后自动填充字段"""
        product_id = self.product_combo.currentData()
        if not product_id:
            return
        for p in self.products:
            if p.get('id') == product_id:
                if not self._editors['customer_code'].text():
                    self._editors['customer_code'].setText(p.get('product_code', ''))
                if not self._editors['oe_number'].text():
                    try:
                        api_client = self.api_client or getattr(self.parent(), 'api_client', None)
                        if api_client:
                            oe_list = api_client.get_product_oes(product_id) or []
                            primary_oe = next((oe for oe in oe_list if oe.get('is_primary')), None)
                            if primary_oe:
                                self._editors['oe_number'].setText(primary_oe.get('oe_number', ''))
                    except Exception as e:
                        print(f"[WARN] ProductItemEditDialog: 获取OE号失败: {e}")
                if not self._editors['product_name'].text():
                    self._editors['product_name'].setText(p.get('detail_desc', '') or p.get('name', ''))
                break

    def _get_order_customer_code(self) -> str:
        """获取当前订单的客户编号：优先使用传入参数，否则从父窗口订单详情取"""
        if self.customer_code:
            return self.customer_code.strip()
        parent = self.parent()
        if parent and hasattr(parent, "_current_order"):
            order = getattr(parent, "_current_order") or {}
            return (order.get("customer_code") or "").strip()
        return ""

    def _auto_generate_customer_code(self):
        """自动生成客户产品编号：客户编号 + 客户型号"""
        customer_code = self._get_order_customer_code()
        model = self._editors["customer_model"].text().strip()
        if not customer_code:
            QMessageBox.warning(self, "警告", "无法获取当前订单的客户编号，请从订单详情入口打开编辑")
            return
        if not model:
            QMessageBox.warning(self, "警告", "请输入客户型号")
            return
        new_code = f"{customer_code}{model}"
        self._editors["customer_code"].setText(new_code)
        QMessageBox.information(self, "成功", f"已生成客户产品编号：{new_code}")

    def _upload_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return
        if self.api_client:
            self.image_path_label.setText("上传中...")
            self._main_upload_worker = ImageUploadWorker(self.api_client, path, self)
            self._main_upload_worker.finished.connect(self._on_main_image_uploaded)
            self._main_upload_worker.start()
        else:
            self.image_path = path
            self.image_path_label.setText(path)

    def _on_main_image_uploaded(self, url: str, success: bool, message: str):
        if success and url:
            self.image_path = url
            self.image_path_label.setText(url)
        else:
            self.image_path_label.setText(self.image_path or "无图片")
            QMessageBox.warning(self, "上传失败", message)

    def _clear_image(self):
        self.image_path = ""
        self.image_path_label.setText("无图片")

    def _upload_sub_image(self):
        """上传附图（异步，不阻塞其他字段编辑）"""
        path, _ = QFileDialog.getOpenFileName(self, "选择附图", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return
        if self.api_client:
            # 先显示占位，上传完成后再替换为真实 URL
            placeholder = "[上传中...]"
            self.sub_images.append(placeholder)
            self._refresh_sub_images_list()
            self._sub_upload_worker = ImageUploadWorker(self.api_client, path, self)
            self._sub_upload_worker.finished.connect(
                lambda u, s, m, ph=placeholder: self._on_sub_image_uploaded(u, s, m, ph)
            )
            self._sub_upload_worker.start()
        else:
            self.sub_images.append(path)
            self._refresh_sub_images_list()

    def _on_sub_image_uploaded(self, url: str, success: bool, message: str, placeholder: str):
        if placeholder in self.sub_images:
            self.sub_images.remove(placeholder)
        if success and url:
            self.sub_images.append(url)
        else:
            QMessageBox.warning(self, "上传失败", message)
        self._refresh_sub_images_list()

    def _remove_selected_sub_image(self):
        """删除选中的附图"""
        item = self.sub_images_list.currentItem()
        if not item:
            QMessageBox.information(self, "提示", "请先选择要删除的附图")
            return
        url = item.data(Qt.UserRole)
        if url in self.sub_images:
            self.sub_images.remove(url)
        self._refresh_sub_images_list()

    def _open_purchase_dialog(self):
        """通过父窗口打开采购 Dialog"""
        parent = self.parent()
        if parent and hasattr(parent, "open_purchase_dialog_for_item"):
            parent.open_purchase_dialog_for_item(self.item)

    def _on_change_supplier(self):
        """打开更换供应商 Dialog"""
        reply = QMessageBox.question(
            self,
            "确认更换供应商",
            "确定要更换供应商吗？当前采购单将被取消并重新生成。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from widgets.supplier_change_dialog import SupplierChangeDialog
        dlg = SupplierChangeDialog(self.item, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if self.api_client and self.item.get("id"):
                try:
                    self.api_client.change_supplier(self.item["id"], data)
                    QMessageBox.information(self, "成功", "供应商已更换，采购单已重新生成")
                    self.accept()
                except Exception as e:
                    QMessageBox.warning(self, "失败", str(e))

    def _add_reply(self):
        text = self.reply_input.toPlainText().strip()
        if not text:
            return
        self.item.setdefault("customer_replies", []).append(text)
        self.reply_input.clear()
        QMessageBox.information(self, "提示", "回复已记录（客户回复接口尚未接入后端）")

    def _on_save(self):
        """保存编辑结果并提交后端"""
        print("[DEBUG] ProductItemEditDialog._on_save: 开始保存")
        result = {}
        # 类目从两级下拉框取值
        result["category_id"] = self.category_level2.currentData() if self.category_level2.currentData() != 0 else None
        print(f"[DEBUG] 字段 category_id: {result['category_id']}")

        # 2026-07-03 新增：首次设置类目时给出确认机会
        new_category_id = result.get("category_id")
        previous_category_id = self.customer_product.get("category_id") if self.customer_product else None
        if new_category_id and not previous_category_id:
            reply = QMessageBox.question(
                self,
                "确认产品类目",
                f"产品类目设置为 {self.category_level2.currentText()} 后将无法再次修改，是否确认？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        for key, editor in self._editors.items():
            if isinstance(editor, QLineEdit):
                result[key] = editor.text()
                print(f"[DEBUG] 字段 {key}: {editor.text()}")
            elif isinstance(editor, QDoubleSpinBox):
                result[key] = editor.value()
                print(f"[DEBUG] 字段 {key}: {editor.value()}")
            elif isinstance(editor, QComboBox):
                result[key] = editor.currentText()
                print(f"[DEBUG] 字段 {key}: {editor.currentText()}")
            elif isinstance(editor, QDateEdit):
                result[key] = editor.date().toString("yyyy-MM-dd")
                print(f"[DEBUG] 字段 {key}: {result[key]}")
        result["image_url"] = self.image_path
        self.item.update(result)
        self.result_data = result

        if self.api_client and self.item.get("id"):
            try:
                # 1. 更新 PI item
                self.api_client.update_pi_item(self.item["id"], result)
                # 2. 更新关联客户产品（类目、主图、附图）
                self._update_customer_product(result)
                self.accept()
            except Exception as e:
                QMessageBox.warning(self, "保存失败", str(e))
        else:
            self.accept()

    def _update_customer_product(self, item_result: dict):
        """同步更新关联客户产品的类目、图片、客户型号、OE号"""
        product_id = self.item.get("product_id")
        if not product_id or not self.api_client:
            return
        cp_data = {}
        # 类目：仅当本次有变更且原本未设置时才允许更新（只能编辑一次）
        new_category_id = item_result.get("category_id")
        current_category_id = None
        if self.customer_product:
            current_category_id = self.customer_product.get("category_id")
        if new_category_id and not current_category_id:
            cp_data["category_id"] = new_category_id
        # 图片
        if self.image_path:
            cp_data["image_url"] = self.image_path
        # 副图：始终同步，保证新增/删除都能反映到客户产品
        cp_data["sub_images"] = self.sub_images or []
        # 客户型号
        new_customer_model = item_result.get("customer_model")
        if new_customer_model:
            current_customer_model = (self.customer_product or {}).get("customer_model") or ""
            if new_customer_model != current_customer_model:
                cp_data["customer_model"] = new_customer_model

        if cp_data:
            try:
                self.api_client.update_customer_product(product_id, cp_data)
                print(f"[DEBUG] 客户产品 {product_id} 已更新: {cp_data.keys()}")
            except Exception as e:
                print(f"[WARN] 更新客户产品失败: {e}")

        # OE号：PI item 中的 oe_number 同步到客户产品 OE 列表
        new_oe_number = item_result.get("oe_number")
        if new_oe_number:
            existing_oes = (self.customer_product or {}).get("oes") or []
            existing_numbers = {oe.get("oe_number") for oe in existing_oes}
            if new_oe_number not in existing_numbers:
                try:
                    self.api_client.post(
                        f"/customer-products/{product_id}/oes",
                        {"oe_number": new_oe_number, "is_primary": len(existing_oes) == 0},
                    )
                    print(f"[DEBUG] 客户产品 {product_id} 已新增 OE: {new_oe_number}")
                except Exception as e:
                    print(f"[WARN] 同步客户产品 OE 失败: {e}")
            # 不阻断 PI item 的保存

    def get_item(self):
        """兼容旧接口，返回编辑后的 item 字典"""
        return self.item

    def get_data(self):
        """返回要提交到后端的字段字典"""
        return getattr(self, "result_data", {})
