"""
订单总表编辑对话框 - Area 分区布局
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                              QTextEdit, QComboBox, QPushButton, QWidget,
                              QFormLayout, QGroupBox, QScrollArea, QDoubleSpinBox,
                              QSpinBox, QCheckBox, QMessageBox, QRadioButton, QButtonGroup)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont


class OrderSummaryEditDialog(QDialog):
    """订单总表编辑对话框 - 单页面 Area 分区布局"""

    saved = Signal(dict)
    _history_loaded = Signal(object)
    _product_loaded = Signal(object)  # 2026-06-09: 产品详情异步加载完成信号

    def __init__(self, order_item, api_client, parent=None, order=None):
        super().__init__(parent)
        self.order_item = order_item  # 订单行item（用于编辑）
        self.order = order  # 订单主对象（用于获取pi_id）
        self.api_client = api_client
        self.new_records = {}
        self._full_product = {}
        self._load_full_product_async()
        self._product_loaded.connect(self._on_full_product_loaded)

        customer_code = order_item.get('customer_product_code', '')
        self.setWindowTitle(f"编辑订单产品信息 - 客户产品编号: {customer_code}")
        self.setMinimumSize(700, 600)
        self._setup_ui()
        self._load_history_package_async()
        self._history_loaded.connect(self._on_history_package_loaded)
    
    @property
    def order_data(self):
        """兼容属性：优先使用order_item，回退到order"""
        return self.order_item if self.order_item else self.order or {}

    def _load_full_product_async(self):
        """异步加载完整客户产品数据（优先级: product_id → customer_product_id）"""
        import threading

        product_id = self.order_item.get('product_id')
        if not product_id:
            return

        def fetch():
            try:
                result = self.api_client.get_customer_product_by_id(product_id)
                if result:
                    self._full_product = result
                    print(f"[DEBUG] 产品详情加载成功: id={product_id}")
                    # 2026-06-09: 异步加载完成后通知主线程刷新UI
                    self._product_loaded.emit(result)
            except Exception as e:
                print(f"[WARN] 加载产品详情失败: {e}")

        thread = threading.Thread(target=fetch, daemon=True)
        thread.start()

    def _on_full_product_loaded(self, product):
        """2026-06-09: 产品详情异步加载完成后回填空字段（不覆盖用户已输入的内容）"""
        if not product:
            return
        # 仅当产品名称为空或 placeholder 时，用产品详情填充
        if hasattr(self, 'product_name_edit') and not self.product_name_edit.text().strip():
            name = product.get('product_name') or ''
            if name:
                self.product_name_edit.setText(name)
        # 仅当单价为 0 时，用产品价格填充（DB 中 unit_price 可能为 NULL）
        if hasattr(self, 'unit_price_edit') and self.unit_price_edit.value() == 0:
            # 2026-06-09 修复：优先取人民币报价
            rmb = product.get('price_rmb')
            usd = product.get('price_usd')
            price = None
            if rmb and float(rmb) > 0:
                price = float(rmb)
            elif usd and float(usd) > 0:
                price = float(usd)
            if price:
                self.unit_price_edit.blockSignals(True)
                self.unit_price_edit.setValue(price)
                self.unit_price_edit.blockSignals(False)
                self._update_total_amount()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        scroll_layout.addWidget(self._create_product_area())
        scroll_layout.addWidget(self._create_reply_area())
        scroll_layout.addWidget(self._create_package_area())
        scroll_layout.addWidget(self._create_payment_area())

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

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

    def _create_product_area(self):
        group = QGroupBox("📦 产品信息")
        layout = QFormLayout()
        layout.setSpacing(12)

        # 2026-06-09 修复回填：PI item 用 detail_desc/remark，不是 product_name/customer_requirement
        # 优先级：_full_product.product_name > order_data.detail_desc > order_data.product_name
        product_name = (
            self._full_product.get('product_name')
            or self.order_data.get('detail_desc')
            or self.order_data.get('product_name')
            or ''
        )
        self.product_name_edit = QLineEdit(product_name)
        self.product_name_edit.setPlaceholderText("请输入产品名称")
        layout.addRow("产品名称:", self.product_name_edit)

        self.oe_number_edit = QLineEdit(self.order_data.get('oe_number', ''))
        self.oe_number_edit.setPlaceholderText("请输入OE号")
        layout.addRow("OE号:", self.oe_number_edit)

        self.quantity_edit = QSpinBox()
        self.quantity_edit.setRange(0, 999999)
        self.quantity_edit.setValue(int(self.order_data.get('quantity') or 0))
        self.quantity_edit.valueChanged.connect(self._update_total_amount)
        layout.addRow("数量:", self.quantity_edit)

        self.unit_price_edit = QDoubleSpinBox()
        self.unit_price_edit.setRange(0, 999999)
        self.unit_price_edit.setDecimals(2)
        self.unit_price_edit.setValue(self._resolve_initial_price())
        self.unit_price_edit.valueChanged.connect(self._update_total_amount)
        layout.addRow("单价:", self.unit_price_edit)

        self.total_amount_label = QLabel("0.00")
        self.total_amount_label.setStyleSheet("font-weight: bold; color: #10b981; font-size: 14px;")
        layout.addRow("合计金额:", self.total_amount_label)
        self._update_total_amount()

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["USD", "RMB", "EUR"])
        self.currency_combo.setCurrentText(self._resolve_initial_currency())
        self.currency_combo.currentTextChanged.connect(self._on_currency_changed)
        layout.addRow("币种:", self.currency_combo)

        self.remark_edit = QTextEdit()
        self.remark_edit.setMaximumHeight(60)
        self.remark_edit.setPlaceholderText("输入客户需求备注...")
        # 2026-06-09 修复回填：PI item 用 remark，不是 customer_requirement
        current_remark = (
            self.order_data.get('remark')
            or self.order_data.get('customer_requirement')
            or ''
        )
        if current_remark:
            self.remark_edit.setText(current_remark)
        layout.addRow("客户需求备注:", self.remark_edit)

        group.setLayout(layout)
        return group

    def _create_package_area(self):
        group = QGroupBox("📦 包装规格")
        layout = QFormLayout()
        layout.setSpacing(12)

        self.packing_mode_group = QButtonGroup()

        radio_widget = QWidget()
        radio_layout = QHBoxLayout(radio_widget)
        radio_layout.setContentsMargins(0, 0, 0, 0)
        radio_layout.setSpacing(16)

        self.radio_single = QRadioButton("1件/箱")
        self.radio_multi = QRadioButton("多件/箱")
        self.radio_box = QRadioButton("1件多箱")
        self.packing_mode_group.addButton(self.radio_single)
        self.packing_mode_group.addButton(self.radio_multi)
        self.packing_mode_group.addButton(self.radio_box)
        self.radio_single.setChecked(True)

        # 根据后端数据设置包装方式（多级优先级策略）
        # 优先级1: packing_type（直接字段）
        # 解析包装方式
        # 2026-06-23 修复：DB 模型没有 packing_type 字段，统一存到 packaging 字段
        # 所以读取顺序要包含 packaging 兜底
        packing_type = (
            self.order_data.get('packing_type') or
            self.order_data.get('packaging') or
            self.order_data.get('pack_type') or
            ''
        )
        units_per_carton = self.order_data.get('units_per_carton')
        packing_spec = self.order_data.get('packing_spec') or self.order_data.get('pack_spec') or ''

        # 解析包装方式
        if packing_type:
            pt_str = str(packing_type).lower()
            if 'multi' in pt_str or '多件' in pt_str or 'multi' in str(packing_type):
                self.radio_multi.setChecked(True)
                print(f"[DEBUG] 包装方式回填: 多件/箱 (from packing_type={packing_type})")
            elif 'box' in pt_str or '多箱' in pt_str or '1件多箱' in str(packing_type) or 'perbox' in pt_str:
                self.radio_box.setChecked(True)
                print(f"[DEBUG] 包装方式回填: 1件多箱 (from packing_type={packing_type})")
            else:
                self.radio_single.setChecked(True)
                print(f"[DEBUG] 包装方式回填: 1件/箱 (from packing_type={packing_type})")
        elif units_per_carton:
            try:
                upc_val = int(units_per_carton)
                if upc_val > 1:
                    self.radio_multi.setChecked(True)
                    print(f"[DEBUG] 包装方式推断: 多件/箱 (units_per_carton={upc_val} > 1)")
                else:
                    self.radio_single.setChecked(True)
                    print(f"[DEBUG] 包装方式推断: 1件/箱 (units_per_carton={upc_val})")
            except (ValueError, TypeError):
                self.radio_single.setChecked(True)
        elif packing_spec:
            # 从 packing_spec 推断：如 "100 pcs/ctn" → 多件/箱
            import re
            match = re.match(r'(\d+)\s*(pcs|pieces)?\s*/\s*(ctn|carton|box)', str(packing_spec), re.I)
            if match and int(match.group(1)) > 1:
                self.radio_multi.setChecked(True)
                print(f"[DEBUG] 包装方式推断: 多件/箱 (from packing_spec={packing_spec})")
            else:
                self.radio_single.setChecked(True)
                print(f"[DEBUG] 包装方式默认: 1件/箱 (无法推断)")

        # ✅ 关键修复：初始化时必须手动触发显示对应的件数输入框
        # 因为 setChecked() 不会触发 toggled 信号
        # 注意：此处的调用已移至 units_widget 创建之后（第320行附近）
        _pending_packing_init = None
        if self.radio_multi.isChecked():
            _pending_packing_init = "multi"
        elif self.radio_box.isChecked():
            _pending_packing_init = "box"
        else:
            _pending_packing_init = None  # 1件/箱模式：默认隐藏

        self.radio_multi.toggled.connect(lambda checked: self._on_packing_mode_changed("multi", checked))
        self.radio_box.toggled.connect(lambda checked: self._on_packing_mode_changed("box", checked))

        radio_layout.addWidget(self.radio_single)
        radio_layout.addWidget(self.radio_multi)
        radio_layout.addWidget(self.radio_box)
        radio_layout.addStretch()
        layout.addRow("包装方式:", radio_widget)

        self.units_widget = QWidget()
        units_layout = QHBoxLayout(self.units_widget)
        units_layout.setContentsMargins(0, 0, 0, 0)
        units_layout.setSpacing(12)

        self.units_per_box_spin = QSpinBox()
        self.units_per_box_spin.setRange(1, 9999)
        self.units_per_box_spin.setSuffix(" 件/箱")
        # 回填每箱数量（优先级：units_per_carton > packing_spec 解析 > 1）
        units_value = (
            self.order_data.get('units_per_carton') or
            self.order_data.get('pieces_per_carton') or
            1
        )
        # 尝试从 packing_spec 格式化字符串解析（如 "100 pcs/ctn"）
        if not units_value or int(units_value) <= 1:
            pack_spec = self.order_data.get('packing_spec') or self.order_data.get('pack_spec') or ''
            import re
            match = re.match(r'(\d+)', str(pack_spec))
            if match and int(match.group(1)) > 1:
                units_value = int(match.group(1))
        self.units_per_box_spin.setValue(int(units_value or 1))
        self.units_per_box_spin.setVisible(False)
        units_layout.addWidget(self.units_per_box_spin)

        self.boxes_count_spin = QSpinBox()
        self.boxes_count_spin.setRange(1, 9999)
        self.boxes_count_spin.setSuffix(" 箱")
        # 2026-06-26 修复：在 "1件多箱" 模式下，正确的回填值是 "每件箱数"（boxes_count / boxes_per_piece），
        # 而不是 "总箱数"（carton_count）。后端 _build_item_detail_v11 已分别返回两个字段：
        #   detail["boxes_count"]   = 每件箱数（boxes_per_piece）
        #   detail["carton_count"]  = "1件多箱"模式=总箱数，其它模式=箱数
        # 之前回填逻辑直接 fallback 到 carton_count，导致 spinbox 显示总箱数（如 600），
        # 看起来像"件数回填了箱数"。
        #
        # 优先级策略：
        #   1. boxes_count（每件箱数，最准确，最新写入）
        #   2. box_count（兼容历史字段名）
        #   3. 由 total_boxes / quantity 反推（处理 schema 未返回 boxes_count 的旧数据）
        #   4. 默认 1
        boxes_value = self.order_data.get('boxes_count')
        if not boxes_value:
            boxes_value = self.order_data.get('box_count')
        if not boxes_value:
            # 反推：boxes_per_piece = carton_count(total) / quantity
            try:
                total_boxes = int(self.order_data.get('carton_count') or 0)
                qty = int(self.order_data.get('quantity') or 0)
                if total_boxes > 0 and qty > 0:
                    derived = round(total_boxes / qty)
                    if derived >= 1:
                        boxes_value = derived
            except (TypeError, ValueError):
                pass
        if not boxes_value:
            boxes_value = 1
        self.boxes_count_spin.setValue(int(boxes_value))
        self.boxes_count_spin.setVisible(False)
        units_layout.addWidget(self.boxes_count_spin)

        units_layout.addStretch()
        self.units_widget.setVisible(False)
        layout.addRow("件数设置:", self.units_widget)

        # ✅ 执行延迟初始化：在 units_widget 创建后触发显示
        if _pending_packing_init:
            self._on_packing_mode_changed(_pending_packing_init, True)
            print(f"[DEBUG] 延迟初始化包装方式: {_pending_packing_init}")
        # else: 1件/箱模式，units_widget 已经默认隐藏

        # 2026-06-23：保留产品编辑 Dialog 中的"采购选项"输入框
        # 该字段的入口只能从产品编辑 Dialog 写入（其他途径如采购 Dialog 不应改此字段），
        # 作用是 1688 采购时一个链接对应一个产品多个选项（颜色、尺码等），
        # 提示用户应该选择哪些选项，并展示在 PI 总表 Col 30。
        self.purchase_channel_edit = QTextEdit()
        self.purchase_channel_edit.setMaximumHeight(40)
        self.purchase_channel_edit.setPlaceholderText("直接复写")

        # 回填采购选项（多级优先级策略）
        # 2026-06-23 修复：order_data 来自后端 PI item，实际字段名是 purchase_option_name，
        # 不是 purchase_channel。原来的 purchase_channel 永远取不到 → 落到 fallback
        # （supplier_name+shop_url 组合）→ 误显示为"店铺名 (链接)"。
        # 优先级1: purchase_option_name（PI item 实际字段，对应 DB 列）
        # 优先级2: purchase_channel（老数据/兼容）
        # 优先级3: channel（别名）
        # 优先级4: supplier_name + shop_url 组合（仅为首次新增时兜底）
        current_channel = (
            self.order_data.get('purchase_option_name')
            or self.order_data.get('purchase_channel')
            or self.order_data.get('channel')
            or ''
        )

        # 如果仍然为空，尝试从供应商信息组合（仅作为空数据兜底，不覆盖已有值）
        if not current_channel:
            supplier_name = self.order_data.get('supplier_name') or ''
            shop_url = self.order_data.get('shop_url') or ''
            if supplier_name:
                current_channel = supplier_name
                if shop_url:
                    current_channel += f" ({shop_url})"
                print(f"[DEBUG] 采购选项回填: 从供应商信息组合 (supplier={supplier_name})")

        if current_channel:
            self.purchase_channel_edit.setText(str(current_channel))
            print(f"[DEBUG] 采购选项回填成功: {current_channel[:50]}...")
        else:
            print(f"[DEBUG] 采购选项为空，等待用户输入或历史数据回填")
        layout.addRow("采购选项:", self.purchase_channel_edit)

        carton_row = QWidget()
        carton_layout = QHBoxLayout(carton_row)
        carton_layout.setContentsMargins(0, 0, 0, 0)
        carton_layout.setSpacing(8)

        # 解析纸箱尺寸：优先使用原始字段，其次从 carton_size 格式化字符串解析
        def parse_carton_size(size_str):
            """从 '40x30x20cm' 格式解析出 (length, width, height)"""
            if not size_str:
                return None, None, None
            import re
            match = re.match(r'(\d+\.?\d*)[xX×](\d+\.?\d*)[xX×](\d+\.?\d*)', str(size_str))
            if match:
                return float(match.group(1)), float(match.group(2)), float(match.group(3))
            return None, None, None

        # 获取纸箱尺寸值（优先级：原始字段 > carton_size 解析 > 0）
        carton_length = self.order_data.get('carton_length_cm')
        carton_width = self.order_data.get('carton_width_cm')
        carton_height = self.order_data.get('carton_height_cm')

        # 如果原始字段为空，尝试从 carton_size 格式化字符串解析
        if not carton_length or not carton_width or not carton_height:
            carton_size_str = self.order_data.get('carton_size') or self.order_data.get('box_size')
            parsed_l, parsed_w, parsed_h = parse_carton_size(carton_size_str)
            if parsed_l and parsed_w and parsed_h:
                carton_length = carton_length or parsed_l
                carton_width = carton_width or parsed_w
                carton_height = carton_height or parsed_h

        self.carton_length_edit = QDoubleSpinBox()
        self.carton_length_edit.setRange(0, 9999)
        self.carton_length_edit.setDecimals(1)
        self.carton_length_edit.setSuffix(" cm")
        self.carton_length_edit.setValue(float(carton_length or 0))
        self.carton_length_edit.valueChanged.connect(self._update_volume)
        carton_layout.addWidget(QLabel("长:"))
        carton_layout.addWidget(self.carton_length_edit)

        self.carton_width_edit = QDoubleSpinBox()
        self.carton_width_edit.setRange(0, 9999)
        self.carton_width_edit.setDecimals(1)
        self.carton_width_edit.setSuffix(" cm")
        self.carton_width_edit.setValue(float(carton_width or 0))
        self.carton_width_edit.valueChanged.connect(self._update_volume)
        carton_layout.addWidget(QLabel("宽:"))
        carton_layout.addWidget(self.carton_width_edit)

        self.carton_height_edit = QDoubleSpinBox()
        self.carton_height_edit.setRange(0, 9999)
        self.carton_height_edit.setDecimals(1)
        self.carton_height_edit.setSuffix(" cm")
        self.carton_height_edit.setValue(float(carton_height or 0))
        self.carton_height_edit.valueChanged.connect(self._update_volume)
        carton_layout.addWidget(QLabel("高:"))
        carton_layout.addWidget(self.carton_height_edit)

        carton_layout.addStretch()
        layout.addRow("纸箱尺寸:", carton_row)

        self.volume_label = QLabel("0.0000 m³")
        self.volume_label.setStyleSheet("color: #6b7280; font-weight: bold;")
        layout.addRow("体积:", self.volume_label)
        self._update_volume()

        # 获取重量值（优先级：gross_weight_kg > carton_gross_weight > box_gw > 0）
        gross_weight = (
            self.order_data.get('gross_weight_kg') or
            self.order_data.get('carton_gross_weight') or
            self.order_data.get('box_gw') or
            0
        )
        self.gross_weight_edit = QDoubleSpinBox()
        self.gross_weight_edit.setRange(0, 99999)
        self.gross_weight_edit.setDecimals(2)
        self.gross_weight_edit.setSuffix(" kg")
        self.gross_weight_edit.setValue(float(gross_weight or 0))
        layout.addRow("重量:", self.gross_weight_edit)

        refill_btn = QPushButton("🔄 智能回填历史数据")
        refill_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #7c3aed; }
        """)
        refill_btn.clicked.connect(self._load_history_package_async)
        layout.addRow("", refill_btn)

        group.setLayout(layout)
        return group

    def _create_payment_area(self):
        group = QGroupBox("💰 付款信息")
        layout = QFormLayout()
        layout.setSpacing(12)

        self.customer_prepayment_edit = QDoubleSpinBox()
        self.customer_prepayment_edit.setRange(0, 99999999)
        self.customer_prepayment_edit.setDecimals(2)
        self.customer_prepayment_edit.setValue(float(self.order_data.get('customer_prepayment') or 0))
        self.customer_prepayment_edit.valueChanged.connect(self._update_remaining_payment)
        layout.addRow("客户预付款:", self.customer_prepayment_edit)

        self.remaining_payment_edit = QDoubleSpinBox()
        self.remaining_payment_edit.setRange(0, 99999999)
        self.remaining_payment_edit.setDecimals(2)
        self.remaining_payment_edit.setValue(float(self.order_data.get('remaining_payment') or 0))
        layout.addRow("待收尾款:", self.remaining_payment_edit)

        self.supplier_deposit_edit = QDoubleSpinBox()
        self.supplier_deposit_edit.setRange(0, 99999999)
        self.supplier_deposit_edit.setDecimals(2)
        self.supplier_deposit_edit.setValue(float(self.order_data.get('supplier_deposit') or 0))
        layout.addRow("工厂订金:", self.supplier_deposit_edit)

        self.supplier_balance_edit = QDoubleSpinBox()
        self.supplier_balance_edit.setRange(0, 99999999)
        self.supplier_balance_edit.setDecimals(2)
        self.supplier_balance_edit.setValue(float(self.order_data.get('supplier_balance') or 0))
        layout.addRow("工厂尾款:", self.supplier_balance_edit)

        group.setLayout(layout)
        return group

    def _create_reply_area(self):
        """创建客户回复区域"""
        group = QGroupBox("💬 客户回复记录")
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # 回复预览标签
        self.reply_preview_label = QLabel("暂无回复记录")
        self.reply_preview_label.setStyleSheet("color: #6b7280; font-size: 12px; padding: 8px;")
        layout.addWidget(self.reply_preview_label)

        # 打开回复对话框按钮
        open_reply_btn = QPushButton("📝 打开客户回复管理")
        open_reply_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        open_reply_btn.clicked.connect(self._open_customer_reply)
        layout.addWidget(open_reply_btn)

        # 异步加载最新回复
        QTimer.singleShot(100, self._load_latest_reply)

        group.setLayout(layout)
        return group

    def _load_latest_reply(self):
        """异步加载最新回复预览"""
        import threading

        pi_id = None
        if self.order:
            pi_id = self.order.get('pi_id') or self.order.get('id')
        if not pi_id:
            pi_id = self.order_item.get('pi_id') or self.order_item.get('pi_item_id')

        if not pi_id:
            return

        def fetch():
            try:
                # 获取该PI的最新回复
                resp = self.api_client.get(f"/customer-replies/pi/{pi_id}/latest")
                if resp:
                    content = resp.get('reply_content', '')[:100]
                    submitter = resp.get('submitter_name', '未知')
                    reply_date = resp.get('reply_date', '')
                    preview = f"最新回复 by {submitter} ({reply_date}):\n{content}..."
                    self.reply_preview_label.setText(preview)
                    self.reply_preview_label.setStyleSheet("color: #374151; font-size: 12px; padding: 8px; background: #f3f4f6; border-radius: 4px;")
            except Exception as e:
                print(f"[WARN] 加载最新回复失败: {e}")

        thread = threading.Thread(target=fetch, daemon=True)
        thread.start()

    def _open_customer_reply(self):
        """打开客户回复对话框"""
        from widgets.order_summary_dialogs import CustomerReplyDialog

        # 优先使用订单主对象的 pi_id
        pi_id = None
        pi_no = 'N/A'
        
        if self.order:
            pi_id = self.order.get('pi_id') or self.order.get('id')
            pi_no = self.order.get('pi_no', 'N/A')
        
        if not pi_id:
            # 如果没有传入 order，尝试从 order_item 获取
            pi_id = self.order_item.get('pi_id') or self.order_item.get('pi_item_id')
            pi_no = self.order_item.get('pi_no', pi_no)
        
        if not pi_id:
            QMessageBox.warning(self, "错误", "无法获取PI订单ID，请确保已保存订单")
            return

        dialog = CustomerReplyDialog(
            pi_id=pi_id,
            pi_no=pi_no,
            api_client=self.api_client,
            current_reply=""
        )
        dialog.exec()

    def _on_packing_mode_changed(self, mode, checked):
        if not checked:
            self.units_widget.setVisible(False)
            return
        if mode == "multi":
            self.units_widget.setVisible(True)
            self.units_per_box_spin.setVisible(True)
            self.units_per_box_spin.setEnabled(True)
            self.boxes_count_spin.setVisible(False)
            self.boxes_count_spin.setEnabled(False)
        elif mode == "box":
            self.units_widget.setVisible(True)
            self.units_per_box_spin.setVisible(False)
            self.units_per_box_spin.setEnabled(False)
            self.boxes_count_spin.setVisible(True)
            self.boxes_count_spin.setEnabled(True)

    def _update_total_amount(self):
        qty = self.quantity_edit.value()
        price = self.unit_price_edit.value()
        total = qty * price
        self.total_amount_label.setText(f"{total:.2f}")

    def _resolve_initial_price(self) -> float:
        """解析初始单价：优先 PrdCustomerProduct 价格"""
        if self._full_product:
            usd = self._full_product.get('price_usd')
            rmb = self._full_product.get('price_rmb')
            if usd and float(usd) > 0:
                return float(usd)
            if rmb and float(rmb) > 0:
                return float(rmb)
        return float(self.order_data.get('unit_price') or 0)

    def _resolve_initial_currency(self) -> str:
        """解析初始币种：优先根据产品价格字段推断"""
        if self._full_product:
            usd = self._full_product.get('price_usd')
            rmb = self._full_product.get('price_rmb')
            if usd and float(usd) > 0:
                return 'USD'
            if rmb and float(rmb) > 0:
                return 'RMB'
        currency = self.order_data.get('currency', 'USD')
        return currency if currency in ('USD', 'RMB', 'EUR') else 'USD'

    def _on_currency_changed(self, new_currency: str):
        """币种切换时联动更新单价"""
        if not self._full_product or not new_currency:
            return
        if new_currency == 'USD':
            val = self._full_product.get('price_usd')
        elif new_currency == 'RMB':
            val = self._full_product.get('price_rmb')
        else:
            return
        if val and float(val) > 0:
            self.unit_price_edit.blockSignals(True)
            self.unit_price_edit.setValue(float(val))
            self.unit_price_edit.blockSignals(False)
            self._update_total_amount()

    def _update_volume(self):
        l = self.carton_length_edit.value()
        w = self.carton_width_edit.value()
        h = self.carton_height_edit.value()
        volume = l * w * h / 1000000
        self.volume_label.setText(f"{volume:.4f} m³")

    def _update_remaining_payment(self):
        total = self.quantity_edit.value() * self.unit_price_edit.value()
        prepayment = self.customer_prepayment_edit.value()
        remaining = total - prepayment
        self.remaining_payment_edit.setValue(max(0, remaining))

    def _load_history_package_async(self):
        import threading

        customer_id = self.order_data.get('customer_id')
        product_id = self.order_data.get('product_id')

        if not customer_id or not product_id:
            print(f"[INFO] 智能回填: 缺少客户ID或产品ID，跳过")
            return

        if hasattr(self, '_loading_history') and self._loading_history:
            print("[INFO] 智能回填: 正在加载中，请稍候")
            return

        self._loading_history = True
        print(f"[INFO] 智能回填: 查询客户{customer_id}+产品{product_id}的历史包装数据...")

        def fetch_history():
            try:
                result = self.api_client.get_history_package(customer_id, product_id)
                self._history_loaded.emit(result)
            except Exception as e:
                print(f"[ERROR] 智能回填失败: {e}")
            finally:
                self._loading_history = False

        thread = threading.Thread(target=fetch_history, daemon=True)
        thread.start()

        QTimer.singleShot(5000, self._on_history_load_timeout)

    def _on_history_load_timeout(self):
        if not hasattr(self, '_loading_history'):
            return
        if self._loading_history:
            self._loading_history = False
            print("[WARN] 智能回填: 请求超时（5秒）")
            if self.isVisible():
                QMessageBox.warning(
                    self, "请求超时",
                    "历史包装数据加载超时，请检查网络连接后重试。"
                )

    def _on_history_package_loaded(self, result):
        if not result or not result.get('found'):
            print(f"[INFO] 智能回填: 未找到历史包装数据")
            QMessageBox.information(
                self, "智能回填",
                "未找到该客户+产品的历史包装数据\n\n可能原因：\n• 这是首次订单\n• 历史订单未填写包装规格\n\n请手动填写包装规格"
            )
            return

        package = result.get('package', {})
        source = result.get('source', '未知')
        created_at = result.get('created_at', '')

        print(f"[INFO] 智能回填: 找到历史数据，来源={source}")

        if package.get('packing_type'):
            pt = str(package['packing_type'])
            if pt == '1件/箱':
                self.radio_single.setChecked(True)
            elif pt == '多件/箱':
                self.radio_multi.setChecked(True)
                if package.get('units_per_carton'):
                    self.units_per_box_spin.setValue(int(package['units_per_carton']))
            elif pt == '1件多箱':
                self.radio_box.setChecked(True)
                if package.get('boxes_count'):
                    self.boxes_count_spin.setValue(int(package['boxes_count']))

        if package.get('purchase_channel'):
            self.purchase_channel_edit.setText(str(package['purchase_channel']))

        if package.get('carton_length_cm') is not None:
            self.carton_length_edit.setValue(float(package['carton_length_cm']))
        if package.get('carton_width_cm') is not None:
            self.carton_width_edit.setValue(float(package['carton_width_cm']))
        if package.get('carton_height_cm') is not None:
            self.carton_height_edit.setValue(float(package['carton_height_cm']))
        if package.get('gross_weight_kg') is not None:
            self.gross_weight_edit.setValue(float(package['gross_weight_kg']))

        msg = f"✅ 已从历史订单回填包装规格\n\n来源: {source}\n"
        if created_at:
            msg += f"创建时间: {created_at}\n"
        msg += f"\n请核对数据是否正确，必要时可手动修改"

        QMessageBox.information(self, "智能回填成功", msg)

    def _save(self):
        data = {
            'product_name': self.product_name_edit.text().strip(),
            'oe_number': self.oe_number_edit.text().strip(),
            'quantity': self.quantity_edit.value(),
            'unit_price': self.unit_price_edit.value(),
            'total_amount': self.quantity_edit.value() * self.unit_price_edit.value(),
            'currency': self.currency_combo.currentText(),
            'customer_requirement': self.remark_edit.toPlainText().strip(),
            'purchase_channel': self.purchase_channel_edit.toPlainText().strip(),
            'carton_length_cm': self.carton_length_edit.value() if self.carton_length_edit.value() > 0 else None,
            'carton_width_cm': self.carton_width_edit.value() if self.carton_width_edit.value() > 0 else None,
            'carton_height_cm': self.carton_height_edit.value() if self.carton_height_edit.value() > 0 else None,
            'gross_weight_kg': self.gross_weight_edit.value() if self.gross_weight_edit.value() > 0 else None,
            'customer_prepayment': self.customer_prepayment_edit.value(),
            'remaining_payment': self.remaining_payment_edit.value(),
            'supplier_deposit': self.supplier_deposit_edit.value(),
            'supplier_balance': self.supplier_balance_edit.value(),
        }

        # ✅ 第一步：先计算包装方式和件数设置（必须在 core_data 之前）
        packing_mode = ""
        if self.radio_single.isChecked():
            packing_mode = "1件/箱"
        elif self.radio_multi.isChecked():
            packing_mode = "多件/箱"
            units = self.units_per_box_spin.value()
            if units > 0:
                data['units_per_carton'] = units
        elif self.radio_box.isChecked():
            packing_mode = "1件多箱"
            boxes = self.boxes_count_spin.value()
            if boxes > 0:
                data['boxes_count'] = boxes

        if packing_mode:
            # 2026-06-23 修复：DB 模型没有 packing_type 字段，统一写到 packaging 字段
            # packing_type 也保留（向后兼容老的 update_pi_item 逻辑）
            data['packing_type'] = packing_mode
            data['packaging'] = packing_mode

        # 2026-06-09 修复：保存核心字段（产品名称/单价/数量/备注/OE号）到 PI item
        # 原问题：_save 只保存了 package_data，product_name/unit_price/remark 等从未写回数据库
        # 2026-06-22 增强：确保所有41列字段都正确存储到 pi_proforma_invoice_item 表
        # 注意：_build_item_detail_v11 返回的 key 是 "id" 不是 "pi_item_id"
        pi_item_id = self.order_data.get('pi_item_id') or self.order_data.get('id')
        if pi_item_id:
            core_data = {
                # === A组: 基础信息 (Col 2-9) ===
                'detail_desc': data['product_name'],       # Col 5: 产品名称 → detail_desc
                'oe_number': data['oe_number'],            # Col 3: OE号
                'quantity': data['quantity'],              # Col 9: 数量
                'unit_price': data['unit_price'],          # Col 10: 报价
                'remark': data['customer_requirement'],    # Col 4: 客户需求备注 → remark

                # === B组: 价格与财务 (Col 13-14, 25-26) ===
                'customer_prepayment': data.get('customer_prepayment'),   # Col 13: 客户预付款
                'remaining_payment': data.get('remaining_payment'),       # Col 14: 待收尾款
                'factory_deposit': data.get('supplier_deposit'),         # Col 25: 工厂订金 (UI字段名supplier_deposit)
                'factory_balance': data.get('supplier_balance'),         # Col 26: 工厂尾款 (UI字段名supplier_balance)

                # === D组: 包装方式 (Col 29) ===
                'packaging': packing_mode if packing_mode else None,      # Col 29: 包装方式

                # === E组: 采购选项 (Col 30) ===
                'purchase_option_name': data.get('purchase_channel') if data.get('purchase_channel') else None,  # Col 30

                # === E组: 纸箱尺寸 (Col 33) ===
                # 2026-06-23 修复：core_data 漏传 carton_l/w/h，导致总表 Col 33 永远空；
                # 后端 update_pi_item 已支持写入 pi_item.carton_length_cm/width_cm/height_cm
                'carton_length_cm': data.get('carton_length_cm'),
                'carton_width_cm': data.get('carton_width_cm'),
                'carton_height_cm': data.get('carton_height_cm'),

                # === E组: 打包规格与箱数 (Col 34-35, 37) ===
                'pack_spec': f"{int(data.get('units_per_carton', 0))} pcs/ctn" if data.get('units_per_carton') else None,  # Col 34
                'carton_count': data.get('boxes_count'),     # Col 35: 箱数（1件多箱模式）
                'carton_gross_weight': data.get('gross_weight_kg'),  # Col 37: 整箱毛重
            }

            # 过滤掉空值和None，避免覆盖已有数据
            core_data = {k: v for k, v in core_data.items() if v is not None and v != ''}

            # 🔍 DEBUG: 详细记录前端发送的数据（2026-06-22 调试用）
            print(f"\n{'='*60}")
            print(f"[DEBUG-FRONTEND] === 准备保存到 PI item ===")
            print(f"[DEBUG-FRONTEND] pi_item_id: {pi_item_id}")
            print(f"[DEBUG-FRONTEND] 字段数量: {len(core_data)}")
            print(f"[DEBUG-FRONTEND] 完整字段列表:")
            for key, value in core_data.items():
                display_value = str(value)[:50] + '...' if len(str(value)) > 50 else value
                print(f"  [DEBUG-FRONTEND]   {key:30s} = {display_value}")
            
            # 检查关键字段
            critical_fields = ['packaging', 'purchase_option_name', 'pack_spec']
            print(f"[DEBUG-FRONTEND] 关键字段检查:")
            for field in critical_fields:
                if field in core_data:
                    print(f"  [DEBUG-FRONTEND] ✓ '{field}' = {core_data[field]}")
                else:
                    print(f"  [DEBUG-FRONTEND] ✗ '{field}' 未包含（可能为空或未设置）")
            print(f"{'='*60}\n")

            try:
                save_result = self.api_client.update_pi_item(pi_item_id, core_data)
                
                # 🔍 DEBUG: 记录API返回结果
                print(f"\n[DEBUG-FRONTEND] API 返回结果:")
                print(f"  [DEBUG-FRONTEND] success: {save_result.get('success') if save_result else 'None'}")
                if save_result and 'debug_fields' in save_result:
                    print(f"  [DEBUG-FRONTEND] debug_fields (数据库实际值):")
                    for key, value in save_result['debug_fields'].items():
                        print(f"    [DEBUG-FRONTEND]     {key}: {value}")
                
                if save_result and save_result.get('success'):
                    print(f"[INFO] PI 核心字段已保存: pi_item_id={pi_item_id}")
                    data['core_saved'] = True
                else:
                    print(f"[WARN] PI 核心字段保存返回异常: {save_result}")
            except Exception as e:
                QMessageBox.critical(
                    self, "保存错误",
                    f"产品名称/单价/备注/包装/采购选项保存失败:\n\n{str(e)}"
                )
                return

        # ✅ 第三步：保存包装规格到 po_purchase_order_item_package 表（用于采购流程）
        po_item_id = self.order_data.get('po_item_id')
        print(f"[DEBUG] 包装规格保存: po_item_id={po_item_id}, order_data={dict(self.order_data)}")
        if po_item_id:
            package_data = {k: v for k, v in data.items() if v is not None and k in [
                'packing_type', 'purchase_channel', 'carton_length_cm', 'carton_width_cm',
                'carton_height_cm', 'units_per_carton', 'gross_weight_kg', 'boxes_count'
            ]}
            print(f"[DEBUG] 包装规格 package_data={package_data}")
            try:
                save_result = self.api_client.save_purchase_item_package(po_item_id, package_data)
                print(f"[DEBUG] 包装规格保存结果: {save_result}")
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
        else:
            print(f"[WARN] po_item_id 为空，跳过包装规格保存")

        self.saved.emit(data)
        self.accept()