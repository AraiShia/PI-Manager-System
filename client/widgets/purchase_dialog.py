# ============================================================
# 采购对话框 - Qt前端实现
# 文件：client/widgets/purchase_dialog.py
# 创建日期：2026-06-03
# 用途：订单采购UI组件（线上/线下采购）
# 参考规格：docs/superpowers/specs/功能迭代/采购Dialog设计.md
# ============================================================

from typing import List, Dict, Optional, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTabWidget, QWidget, QGroupBox, QLineEdit, QTextEdit,
    QComboBox, QCheckBox, QRadioButton, QFileDialog, QMessageBox,
    QFormLayout, QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QDate, QSettings
from PySide6.QtGui import QFont


# 2026-06-23：列宽持久化用 QSettings key
_PRODUCT_TABLE_COL_WIDTHS_KEY = "purchase_dialog/product_table_column_widths"


# 2026-06-09 任务 7：商品单价并入产品信息 - 9 列合一产品信息表格
# 2026-06-12 需求 #44：每条产品独立 1688 链接（可能来自不同链接），新增第 10 列
# 每行表示一个产品的完整费用：基本信息 + 4 类费用 + 总金额 + 1688 链接
# (列标题, 列宽, 是否可编辑)
PRODUCT_TABLE_COLUMNS = [
    ("产品名称", 140, False),
    ("型号", 110, False),
    ("数量", 60, False),
    ("商品单价", 90, True),
    ("贴标费", 80, True),
    ("税费", 80, True),
    ("发货费", 80, True),
    ("运费", 80, True),
    ("总金额", 100, False),
    ("1688链接", 220, True),
]
COL_IDX_NAME = 0
COL_IDX_MODEL = 1
COL_IDX_QTY = 2
COL_IDX_UNIT_PRICE = 3
COL_IDX_LABELING = 4
COL_IDX_TAX = 5
COL_IDX_SHIPPING = 6
COL_IDX_FREIGHT = 7
COL_IDX_TOTAL = 8
COL_IDX_LINK = 9


class PurchaseDialog(QDialog):
    """
    采购订单对话框
    
    功能：
    - Tab切换：线上采购 / 线下采购
    - 线上采购：1688平台 / 微信平台选择
    - 最近采购费用自动填充
    - 发票上传
    - 线下采购：供应商选择、合同生成
    """
    
    # 信号定义
    purchase_completed = Signal(dict)  # 采购完成，返回采购数据
    error_occurred = Signal(str)       # 错误信号

    def __init__(self, api_client, items=None, parent=None, dept_id=None, pi_id=None, prefill_urls=None):
        super().__init__(parent)
        self.api_client = api_client
        self.items = items or []  # [{'product_id': 1, 'product_name': 'XXX', 'model': 'ABC', 'quantity': 100, ...}]

        # 必填字段（由调用方传入）
        self.dept_id = dept_id
        self.pi_id = pi_id

        # 2026-06-11 任务 3：每个产品的 1688 历史链接预填 {product_id: [url, ...]}
        self._prefill_urls = prefill_urls or {}

        # 数据状态
        self.current_item = self.items[0] if self.items else None  # 当前选中产品
        self.platform = '1688'        # 当前平台：'1688' | 'wechat'
        self.purchase_type = 'online' # 采购类型：'online' | 'offline'
        # 2026-06-09 任务 12：移除 latest_purchase（费用已并入产品行，不再有"全 dialog 共用最近记录"的概念）

        # 文件路径
        self.screenshot_path = None
        self.invoice_path = None

        # 2026-06-23：每行独立存储 1688 凭证路径 / 备注
        # 行选变化时把对应行的值装载到顶层表单；顶层编辑时写回当前行
        self._row_screenshots: dict = {}  # {row: file_path}
        self._row_remarks: dict = {}      # {row: text}
        self._row_contacts: dict = {}     # {row: wechat_contact}
        self._loading_top_form = False    # 防止 textChanged 递归写回

        # 2026-06-23：采购币种（USD / RMB），根据 items/订单预选
        # 优先级：items[0].currency > pi.currency > USD
        self.purchase_currency = 'USD'
        # 2026-06-23：人民币→美元汇率（仅 RMB 模式使用，1 USD = X RMB）
        self.exchange_rate = 6.8
        try:
            if self.items:
                cur = self.items[0].get('currency') or self.items[0].get('order_currency')
                if cur and str(cur).upper() in ('USD', 'RMB', 'CNY', '人民币', '美元'):
                    if str(cur).upper() in ('RMB', 'CNY', '人民币'):
                        self.purchase_currency = 'RMB'
                # 也可从 items 携带的 rate 字段预填
                rate = self.items[0].get('exchange_rate')
                if rate and float(rate) > 0:
                    self.exchange_rate = float(rate)
        except Exception:
            pass

        item_count = len(self.items)
        title = f"采购订单 ({item_count} 个产品)" if item_count > 1 else "采购订单"
        self.setWindowTitle(title)
        # 2026-06-09 任务 13：dialog 增宽至 1200 容纳 9 列合一表格
        self.setMinimumSize(1200, 750)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)

        # 滚动区域：包裹所有内容，避免空间挤占
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(12)

        # 2026-06-23：采购币种选择（USD / RMB）
        # 切换后刷新产品表总金额、顶层 1688 链接/采购平台单价的币种显示
        currency_bar = QHBoxLayout()
        currency_label = QLabel("采购币种:")
        currency_label.setStyleSheet("font-weight: bold; color: #333;")
        currency_bar.addWidget(currency_label)
        self.currency_radio_usd = QRadioButton("美元 (USD)")
        self.currency_radio_rmb = QRadioButton("人民币 (RMB)")
        # 根据 self.purchase_currency 预选（__init__ 已从订单币种推断）
        if getattr(self, 'purchase_currency', 'USD') == 'RMB':
            self.currency_radio_rmb.setChecked(True)
        else:
            self.currency_radio_usd.setChecked(True)
        self.currency_radio_usd.toggled.connect(self._on_currency_changed)
        self.currency_radio_rmb.toggled.connect(self._on_currency_changed)
        currency_bar.addWidget(self.currency_radio_usd)
        currency_bar.addWidget(self.currency_radio_rmb)

        # 2026-06-23：汇率输入（仅 RMB 模式可见）
        rate_label = QLabel("汇率 (1 USD = ? RMB):")
        rate_label.setStyleSheet("color: #555;")
        self.exchange_rate_input = QDoubleSpinBox()
        self.exchange_rate_input.setRange(0.01, 50.0)
        self.exchange_rate_input.setDecimals(4)
        self.exchange_rate_input.setSingleStep(0.1)
        self.exchange_rate_input.setValue(getattr(self, 'exchange_rate', 6.8))
        self.exchange_rate_input.setFixedWidth(110)
        self.exchange_rate_input.setToolTip("选 RMB 时使用：1 美元 = X 人民币\n总金额会自动计算等值美元")
        self.exchange_rate_input.valueChanged.connect(self._on_exchange_rate_changed)
        self._rate_label = rate_label  # 引用，便于显示/隐藏
        currency_bar.addSpacing(20)
        currency_bar.addWidget(rate_label)
        currency_bar.addWidget(self.exchange_rate_input)

        currency_bar.addStretch()
        # 提示：采购币种决定商品单价等金额的显示币种
        currency_hint = QLabel("采购前请选择币种（影响所有金额显示）")
        currency_hint.setStyleSheet("color: #888; font-size: 11px;")
        currency_bar.addWidget(currency_hint)
        container_layout.addLayout(currency_bar)

        # 初始化汇率输入框的可见性（根据当前币种）
        self._update_rate_input_visibility()

        # Tab容器（只包含平台/供应商等差异内容）
        self.tab_widget = QTabWidget()

        # 创建各Tab
        online_tab = self._create_online_tab()
        offline_tab = self._create_offline_tab()

        self.tab_widget.addTab(online_tab, "线上采购")
        self.tab_widget.addTab(offline_tab, "线下采购")
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # 2026-06-26 对调位置：产品信息移到Tab上方
        # 产品信息区（含 9 列合一表格，2026-06-09 任务 8）
        product_group = self._create_product_info_group()
        container_layout.addWidget(product_group)

        # 发票上传
        invoice_group = self._create_invoice_group()
        container_layout.addWidget(invoice_group)

        # Tab容器（包含线上采购/线下采购）
        container_layout.addWidget(self.tab_widget)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setFixedWidth(100)
        button_layout.addWidget(cancel_btn)

        submit_btn = QPushButton("确认采购")
        submit_btn.clicked.connect(self._submit)
        submit_btn.setFixedWidth(100)
        submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        button_layout.addWidget(submit_btn)

        main_layout.addLayout(button_layout)

        # 2026-06-09 任务 9/12：初始化时加载所有产品行的最近采购记录
        QTimer.singleShot(100, self._load_latest_for_all_rows)
    
    def _create_online_tab(self) -> QWidget:
        """创建线上采购Tab（只包含平台相关差异内容，公共Group已提取到init_ui）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        # 平台选择区
        platform_group = self._create_platform_group()
        layout.addWidget(platform_group)

        # 1688采购区
        self.platform_1688_group = self._create_1688_group()
        layout.addWidget(self.platform_1688_group)

        # 微信采购区（初始隐藏）
        self.platform_wechat_group = self._create_wechat_group()
        self.platform_wechat_group.hide()
        layout.addWidget(self.platform_wechat_group)

        layout.addStretch()
        return widget
    
    def _create_offline_tab(self) -> QWidget:
        """创建线下采购Tab（只包含供应商相关差异内容，公共Group已提取到init_ui）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        # 合同选项
        contract_group = self._create_contract_group()
        layout.addWidget(contract_group)

        # 供应商信息
        supplier_group = self._create_supplier_group()
        layout.addWidget(supplier_group)

        layout.addStretch()
        return widget
    
    def _create_product_info_group(self) -> QGroupBox:
        """2026-06-09 任务 8：9 列合一产品信息表格
        - 每行一个产品
        - 列：产品名称 / 型号 / 数量 / 商品单价 / 贴标费 / 税费 / 发货费 / 运费 / 总金额
        - 单产品时也使用同一表格（仅 1 行），方便统一处理
        """
        item_count = len(self.items)
        group = QGroupBox(f"产品信息 ({item_count} 个)" if item_count > 1 else "产品信息")
        layout = QVBoxLayout()

        if not self.items:
            layout.addWidget(QLabel("无可采购产品"))
        else:
            self.product_table = QTableWidget()
            self.product_table.setColumnCount(len(PRODUCT_TABLE_COLUMNS))
            self.product_table.setHorizontalHeaderLabels(
                [c[0] for c in PRODUCT_TABLE_COLUMNS]
            )
            self.product_table.setRowCount(item_count)
            # 动态高度：每行约 36px + 表头约 30px + 边距
            table_height = min(item_count * 36 + 40, 400)
            self.product_table.setMinimumHeight(table_height)
            self.product_table.setMaximumHeight(table_height)
            # 第 0 列（产品名称）固定宽度，其它按内容
            self.product_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            self.product_table.setColumnWidth(0, PRODUCT_TABLE_COLUMNS[0][1])
            for c_idx in range(1, len(PRODUCT_TABLE_COLUMNS)):
                self.product_table.horizontalHeader().setSectionResizeMode(
                    c_idx, QHeaderView.ResizeMode.ResizeToContents
                )
            self.product_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)

            # 2026-06-23：所有列允许拖动宽度（之前除第 0 列外是 ResizeToContents，无法拖）
            for c_idx in range(len(PRODUCT_TABLE_COLUMNS)):
                self.product_table.horizontalHeader().setSectionResizeMode(
                    c_idx, QHeaderView.ResizeMode.Interactive
                )
                # 用 PRODUCT_TABLE_COLUMNS 里的默认宽度
                self.product_table.setColumnWidth(c_idx, PRODUCT_TABLE_COLUMNS[c_idx][1])

            # 加载用户保存的列宽（如有）
            self._load_product_table_column_widths()

            # 监听列宽变化：用户拖动后保存
            self.product_table.horizontalHeader().sectionResized.connect(
                self._on_product_table_column_resized
            )

            for i, item in enumerate(self.items):
                # 第 0 列：产品名称
                name_item = QTableWidgetItem(item.get('product_name', item.get('detail_desc', '临时产品')))
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.product_table.setItem(i, COL_IDX_NAME, name_item)

                # 第 1 列：型号
                model_item = QTableWidgetItem(item.get('customer_model', item.get('model', 'N/A')))
                model_item.setFlags(model_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.product_table.setItem(i, COL_IDX_MODEL, model_item)

                # 第 2 列：数量
                qty_item = QTableWidgetItem(str(item.get('quantity', 0)))
                qty_item.setFlags(qty_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.product_table.setItem(i, COL_IDX_QTY, qty_item)

                # 第 3-7 列：费用（4 类费用 + 运费）
                for c_idx in (COL_IDX_UNIT_PRICE, COL_IDX_LABELING, COL_IDX_TAX, COL_IDX_SHIPPING, COL_IDX_FREIGHT):
                    cell = QTableWidgetItem("")
                    self.product_table.setItem(i, c_idx, cell)

                # 第 8 列：总金额（只读，公式自动算）
                total_item = QTableWidgetItem("")
                total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.product_table.setItem(i, COL_IDX_TOTAL, total_item)

                # 第 9 列：1688 链接（每条产品独立，可能来自不同链接）
                product_id = item.get('product_id')
                initial_link = ""
                if product_id and product_id in self._prefill_urls:
                    urls = self._prefill_urls[product_id]
                    if urls:
                        initial_link = urls[0]
                link_item = QTableWidgetItem(initial_link)
                link_item.setToolTip(
                    "每个产品的 1688 链接，独立编辑\n"
                    "可双击修改；不同产品可能来自不同供应商的链接"
                )
                self.product_table.setItem(i, COL_IDX_LINK, link_item)

            # 监听单元格编辑：触发总金额重算
            self.product_table.cellChanged.connect(self._on_product_cell_changed)
            # 2026-06-23：监听行选变化 → 联动更新顶层链接/凭证/备注
            self.product_table.itemSelectionChanged.connect(self._on_product_selection_changed)
            # 监听 1688 链接列直接编辑：写回 self.screenshot_path 行级存储
            # 默认选中第一行
            if item_count > 0:
                self.product_table.selectRow(0)

            layout.addWidget(self.product_table)

        group.setLayout(layout)
        return group
    
    def _update_product_display(self):
        """更新产品显示信息"""
        if not self.current_item:
            return
        
        info_text = f"当前产品: {self.current_item.get('product_name', '临时产品')} | 型号: {self.current_item.get('model', 'N/A')} | 数量: {self.current_item.get('quantity', 0)}"
        
        # 如果存在产品信息标签则更新，不存在则创建
        if hasattr(self, 'product_info_label'):
            self.product_info_label.setText(info_text)
        else:
            self.product_info_label = QLabel(info_text)
            # 找到qty_layout并在其前面插入
            product_group = self._find_product_group()
            if product_group:
                layout = product_group.layout()
                # 在下拉框后面插入产品信息标签
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item.widget() == self.purchase_quantity_input:
                        layout.insertWidget(i, self.product_info_label)
                        break
    
    def _find_product_group(self) -> QGroupBox:
        """查找产品信息Group"""
        for child in self.findChildren(QGroupBox):
            if child.title() == "产品信息":
                return child
        return None
    
    def _on_product_changed(self, index):
        """产品切换处理"""
        if not hasattr(self, 'product_combo'):
            return
        
        item_index = self.product_combo.currentData()
        if item_index is None:
            return
        
        # 更新当前产品
        self.current_item = self.items[item_index]
        
        # 重置费用字段
        self._reset_fee_fields()
        
        # 重置发票信息
        self._reset_invoice_fields()
        
        # 2026-06-12 需求 #44：为当前产品填充 1688 历史链接下拉
        product_id = self.current_item.get('product_id')
        self._fill_link_combo(product_id)
        
        # 更新采购数量
        self.purchase_quantity_input.setText(str(self.current_item.get('quantity', '')))
        
        # 更新产品显示
        self._update_product_display()
        
        print(f"[PurchaseDialog] 产品切换: {self.current_item.get('product_name', '临时产品')}")
    
    def _reset_fee_fields(self):
        """重置费用字段"""
        self.price_input.clear()
        self.labeling_fee_input.clear()
        self.tax_fee_input.clear()
        self.shipping_fee_input.clear()
        
        # 重置最近费用标签
        self.price_latest_label.setText("最近: --")
        self.labeling_fee_latest_label.setText("最近: --")
        self.tax_fee_latest_label.setText("最近: --")
        self.shipping_fee_latest_label.setText("最近: --")
        
        # 重置最近采购信息
        self.recent_info_label.setText("最近采购: 暂无记录")
        self.recent_link_input.clear()
        self.recent_link_btn.hide()
        self.recent_wechat_label.hide()
        
        # 重置费用输入框样式
        self._reset_input_style(self.price_input)
        self._reset_input_style(self.labeling_fee_input)
        self._reset_input_style(self.tax_fee_input)
        self._reset_input_style(self.shipping_fee_input)
    
    def _reset_input_style(self, input_widget):
        """重置输入框样式"""
        input_widget.setStyleSheet("")
    
    def _reset_invoice_fields(self):
        """重置发票字段"""
        self.invoice_path = None
        self.invoice_label.setText("当前文件: 无")
        self.invoice_amount_input.clear()
        self.invoice_currency_combo.setCurrentIndex(0)
    
    def _create_platform_group(self) -> QGroupBox:
        """创建平台选择区"""
        group = QGroupBox("采购平台")
        layout = QHBoxLayout()
        
        self.platform_1688_radio = QRadioButton("1688")
        self.platform_1688_radio.setChecked(True)
        self.platform_1688_radio.toggled.connect(lambda: self._on_platform_changed('1688'))
        layout.addWidget(self.platform_1688_radio)
        
        self.platform_wechat_radio = QRadioButton("微信")
        self.platform_wechat_radio.toggled.connect(lambda: self._on_platform_changed('wechat'))
        layout.addWidget(self.platform_wechat_radio)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def _create_1688_group(self) -> QGroupBox:
        """创建1688采购表单"""
        group = QGroupBox("1688采购")
        layout = QFormLayout()
        layout.setSpacing(10)

        # 2026-06-23：1688 店铺名称（作为 supplier 标识，提交时自动 find-or-create）
        self.shop_name_input = QLineEdit()
        self.shop_name_input.setPlaceholderText("1688 店铺名称，例如：深圳市XX贸易有限公司")
        self.shop_name_input.setToolTip("必填，提交时自动用店铺名称作为 supplier_id")
        layout.addRow("1688 店铺名称 *:", self.shop_name_input)

        # 1688链接（2026-06-11 任务 3：改为可编辑 QComboBox 以支持下拉历史链接）
        # 2026-06-12 需求 #44：每条产品独立 1688 链接，下拉 = 当前产品行历史链接的快捷选择
        link_layout = QHBoxLayout()
        self.link_combo = QComboBox()
        self.link_combo.setEditable(True)
        self.link_combo.setMinimumWidth(300)
        self.link_combo.lineEdit().setPlaceholderText("https://detail.1688.com/...")
        # 选择变化时写回当前产品行的第 10 列
        self.link_combo.currentTextChanged.connect(self._on_link_combo_changed)
        link_layout.addWidget(self.link_combo)

        visit_btn = QPushButton("访问")
        visit_btn.setFixedWidth(60)
        visit_btn.clicked.connect(self._open_link_in_browser)
        link_layout.addWidget(visit_btn)
        layout.addRow("1688链接:", link_layout)

        # 微信联系方式（可选）
        self.contact_wechat_input = QLineEdit()
        self.contact_wechat_input.setPlaceholderText("可选，其他联系方式")
        # 2026-06-23：变化时写回当前行
        self.contact_wechat_input.textChanged.connect(self._on_top_form_contact_changed)
        layout.addRow("微信联系方式:", self.contact_wechat_input)

        # 采购凭证
        screenshot_layout = QHBoxLayout()
        self.screenshot_label = QLabel("当前: 无")
        screenshot_layout.addWidget(self.screenshot_label)

        select_screenshot_btn = QPushButton("选择截图")
        select_screenshot_btn.clicked.connect(self._select_screenshot)
        screenshot_layout.addWidget(select_screenshot_btn)

        screenshot_layout.addStretch()
        layout.addRow("采购凭证（可选）:", screenshot_layout)

        # 备注
        self.online_remark_input = QTextEdit()
        self.online_remark_input.setMaximumHeight(60)
        self.online_remark_input.setPlaceholderText("可选填写备注")
        # 2026-06-23：变化时写回当前行
        self.online_remark_input.textChanged.connect(self._on_top_form_remark_changed)
        layout.addRow("备注:", self.online_remark_input)

        group.setLayout(layout)
        return group
    
    def _create_wechat_group(self) -> QGroupBox:
        """创建微信采购表单"""
        group = QGroupBox("微信采购")
        layout = QFormLayout()
        layout.setSpacing(10)
        
        # 微信号（必填）
        self.wechat_id_input = QLineEdit()
        self.wechat_id_input.setPlaceholderText("卖家微信号")
        layout.addRow("微信号 *:", self.wechat_id_input)
        
        # 微信昵称（必填）
        self.wechat_nickname_input = QLineEdit()
        self.wechat_nickname_input.setPlaceholderText("卖家微信昵称")
        layout.addRow("微信昵称 *:", self.wechat_nickname_input)
        
        # 1688链接（可选）
        wechat_link_layout = QHBoxLayout()
        self.wechat_link_input = QLineEdit()
        self.wechat_link_input.setPlaceholderText("可选，关联的1688链接")
        self.wechat_link_input.setMinimumWidth(300)
        wechat_link_layout.addWidget(self.wechat_link_input)
        
        visit_btn = QPushButton("访问")
        visit_btn.setFixedWidth(60)
        visit_btn.clicked.connect(self._open_wechat_link)
        wechat_link_layout.addWidget(visit_btn)
        layout.addRow("1688链接（可选）:", wechat_link_layout)
        
        # 采购凭证
        wechat_screenshot_layout = QHBoxLayout()
        self.wechat_screenshot_label = QLabel("当前: 无")
        wechat_screenshot_layout.addWidget(self.wechat_screenshot_label)
        
        select_screenshot_btn = QPushButton("选择截图")
        select_screenshot_btn.clicked.connect(self._select_screenshot)
        wechat_screenshot_layout.addWidget(select_screenshot_btn)
        
        wechat_screenshot_layout.addStretch()
        layout.addRow("采购凭证（可选）:", wechat_screenshot_layout)
        
        # 备注
        self.wechat_remark_input = QTextEdit()
        self.wechat_remark_input.setMaximumHeight(60)
        self.wechat_remark_input.setPlaceholderText("可选填写备注")
        layout.addRow("备注:", self.wechat_remark_input)
        
        group.setLayout(layout)
        return group
    
    # 2026-06-09 任务 12：移除 _create_recent_purchase_group
    # 9 列合一表格内已包含"商品单价 / 贴标费 / 税费 / 发货费 / 运费"五列费用
    # 不再需要独立的"最近采购费用" QGroupBox。原方法（376-453 行）已删除。


    def _create_contract_group(self) -> QGroupBox:
        """创建合同选项区"""
        group = QGroupBox("合同选项")
        layout = QVBoxLayout()
        
        self.generate_contract_checkbox = QCheckBox("生成采购合同")
        self.generate_contract_checkbox.setChecked(True)
        self.generate_contract_checkbox.stateChanged.connect(self._on_contract_generate_changed)
        layout.addWidget(self.generate_contract_checkbox)
        
        # 模板选择
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("合同模板:"))
        self.template_combo = QComboBox()
        self.template_combo.addItem("标准采购合同", 1)
        self.template_combo.addItem("简易合同", 2)
        self.template_combo.addItem("定制合同", 3)
        self.template_combo.setFixedWidth(200)
        template_layout.addWidget(self.template_combo)
        template_layout.addStretch()
        layout.addLayout(template_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_supplier_group(self) -> QGroupBox:
        """创建供应商信息区"""
        group = QGroupBox("供应商信息")
        layout = QFormLayout()
        layout.setSpacing(10)
        
        # 供应商选择
        supplier_layout = QHBoxLayout()
        self.supplier_combo = QComboBox()
        self.supplier_combo.setMinimumWidth(200)
        self.supplier_combo.currentIndexChanged.connect(self._on_supplier_changed)
        supplier_layout.addWidget(self.supplier_combo)
        
        add_supplier_btn = QPushButton("+ 新增供应商")
        add_supplier_btn.setFixedWidth(100)
        add_supplier_btn.clicked.connect(self._add_supplier)
        supplier_layout.addWidget(add_supplier_btn)
        
        supplier_layout.addStretch()
        layout.addRow("供应商:", supplier_layout)
        
        # 交货期限
        self.delivery_date_input = QDateEdit()
        self.delivery_date_input.setCalendarPopup(True)
        self.delivery_date_input.setDate(QDate.currentDate().addDays(7))
        layout.addRow("交货期限:", self.delivery_date_input)
        
        # 联系人
        self.supplier_contact_input = QLineEdit()
        self.supplier_contact_input.setPlaceholderText("供应商联系人")
        layout.addRow("联系人:", self.supplier_contact_input)
        
        # 电话
        self.supplier_phone_input = QLineEdit()
        self.supplier_phone_input.setPlaceholderText("供应商联系电话")
        layout.addRow("电话:", self.supplier_phone_input)
        
        # 备注
        self.offline_remark_input = QTextEdit()
        self.offline_remark_input.setMaximumHeight(60)
        self.offline_remark_input.setPlaceholderText("可选填写备注")
        layout.addRow("备注:", self.offline_remark_input)
        
        # 合同备注
        self.contract_remark_input = QTextEdit()
        self.contract_remark_input.setMaximumHeight(60)
        self.contract_remark_input.setPlaceholderText("合同特殊条款")
        layout.addRow("合同备注:", self.contract_remark_input)
        
        group.setLayout(layout)
        return group
    
    def _create_invoice_group(self) -> QGroupBox:
        """创建发票上传区

        2026-06-23：线上采购可能不需要发票，加"需要发票"checkbox 控制整个发票区显隐
        """
        group = QGroupBox("发票信息")
        layout = QFormLayout()
        layout.setSpacing(10)

        # 2026-06-23：是否需要发票（线上采购不强制，线下采购默认需要）
        self.need_invoice_checkbox = QCheckBox("需要发票")
        self.need_invoice_checkbox.setChecked(True)  # 默认勾选（兼容线下采购场景）
        self.need_invoice_checkbox.toggled.connect(self._toggle_invoice_fields)
        layout.addRow("", self.need_invoice_checkbox)

        # 2026-06-23：发票内容容器（用于整体显隐切换）
        self.invoice_content = QWidget()
        content_layout = QFormLayout()
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 发票文件
        invoice_layout = QHBoxLayout()
        self.invoice_label = QLabel("当前文件: 无")
        invoice_layout.addWidget(self.invoice_label)

        select_invoice_btn = QPushButton("选择文件")
        select_invoice_btn.clicked.connect(self._select_invoice)
        invoice_layout.addWidget(select_invoice_btn)

        upload_invoice_btn = QPushButton("上传")
        upload_invoice_btn.clicked.connect(self._upload_invoice)
        invoice_layout.addWidget(upload_invoice_btn)

        invoice_layout.addStretch()
        content_layout.addRow("发票文件:", invoice_layout)

        # 发票金额
        amount_layout = QHBoxLayout()
        self.invoice_amount_input = QLineEdit()
        self.invoice_amount_input.setPlaceholderText("0.00")
        self.invoice_amount_input.setFixedWidth(100)
        amount_layout.addWidget(self.invoice_amount_input)

        self.invoice_currency_combo = QComboBox()
        self.invoice_currency_combo.addItems(["CNY", "USD", "EUR"])
        self.invoice_currency_combo.setFixedWidth(80)
        amount_layout.addWidget(self.invoice_currency_combo)

        amount_layout.addStretch()
        content_layout.addRow("发票金额:", amount_layout)

        self.invoice_content.setLayout(content_layout)
        layout.addRow(self.invoice_content)

        group.setLayout(layout)
        return group

    def _toggle_invoice_fields(self, checked: bool):
        """2026-06-23：是否需要发票 切换"""
        if hasattr(self, 'invoice_content'):
            self.invoice_content.setVisible(checked)

    # ==================== 列宽持久化（2026-06-23） ====================

    def _load_product_table_column_widths(self):
        """从 QSettings 加载用户上次保存的列宽"""
        if not hasattr(self, 'product_table'):
            return
        try:
            settings = QSettings("PI-Manager", "PurchaseDialog")
            saved = settings.value(_PRODUCT_TABLE_COL_WIDTHS_KEY, None)
            if not saved:
                return
            # QSettings 读 dict/list 回来是字符串，分两种情况兼容
            widths = None
            if isinstance(saved, dict):
                widths = {int(k): int(v) for k, v in saved.items()}
            elif isinstance(saved, str) and saved.startswith('{'):
                import ast
                parsed = ast.literal_eval(saved)
                if isinstance(parsed, dict):
                    widths = {int(k): int(v) for k, v in parsed.items()}
            if not widths:
                return
            for col, w in widths.items():
                if 0 <= col < self.product_table.columnCount() and w > 10:
                    self.product_table.setColumnWidth(col, w)
        except Exception as e:
            print(f"[PurchaseDialog] 加载列宽失败: {e}")

    def _on_product_table_column_resized(self, logical_index: int, old_size: int, new_size: int):
        """2026-06-23：列宽拖动后保存（用 QTimer 合并多次 resize 事件）"""
        if not hasattr(self, '_save_col_width_timer'):
            self._save_col_width_timer = QTimer(self)
            self._save_col_width_timer.setSingleShot(True)
            self._save_col_width_timer.setInterval(500)
            self._save_col_width_timer.timeout.connect(self._save_product_table_column_widths)
        self._save_col_width_timer.start()

    def _save_product_table_column_widths(self):
        """保存当前列宽到 QSettings"""
        if not hasattr(self, 'product_table'):
            return
        try:
            widths = {
                col: self.product_table.columnWidth(col)
                for col in range(self.product_table.columnCount())
            }
            settings = QSettings("PI-Manager", "PurchaseDialog")
            settings.setValue(_PRODUCT_TABLE_COL_WIDTHS_KEY, widths)
        except Exception as e:
            print(f"[PurchaseDialog] 保存列宽失败: {e}")

    # ==================== 事件处理方法 ====================

    def _on_product_cell_changed(self, row: int, col: int):
        """2026-06-09 任务 10：单元格变化触发总金额重算 + 标记最近值"""
        if col in (COL_IDX_UNIT_PRICE, COL_IDX_LABELING, COL_IDX_TAX, COL_IDX_SHIPPING, COL_IDX_FREIGHT):
            self._recalc_total(row)

    def _get_current_product_row(self) -> int | None:
        """2026-06-23：获取当前选中的产品行索引（用于写回 _row_screenshots / _row_remarks 等行级存储）"""
        if not hasattr(self, 'product_table') or not self.current_item:
            return None
        if self.current_item not in self.items:
            return None
        try:
            return self.items.index(self.current_item)
        except ValueError:
            return None

    def _recalc_total(self, row: int):
        """2026-06-09 任务 10：重算并刷新总金额单元格
        总金额 = 单价 × 数量 + 贴标 + 税 + 发货 + 运费
        """
        try:
            qty_str = self.product_table.item(row, COL_IDX_QTY).text() if self.product_table.item(row, COL_IDX_QTY) else "0"
            unit_str = self.product_table.item(row, COL_IDX_UNIT_PRICE).text() if self.product_table.item(row, COL_IDX_UNIT_PRICE) else ""
            lab_str = self.product_table.item(row, COL_IDX_LABELING).text() if self.product_table.item(row, COL_IDX_LABELING) else ""
            tax_str = self.product_table.item(row, COL_IDX_TAX).text() if self.product_table.item(row, COL_IDX_TAX) else ""
            ship_str = self.product_table.item(row, COL_IDX_SHIPPING).text() if self.product_table.item(row, COL_IDX_SHIPPING) else ""
            fgt_str = self.product_table.item(row, COL_IDX_FREIGHT).text() if self.product_table.item(row, COL_IDX_FREIGHT) else ""

            def _to_float(s):
                try:
                    return float(s)
                except (ValueError, TypeError):
                    return 0.0

            qty = _to_float(qty_str)
            total = (
                _to_float(unit_str) * qty
                + _to_float(lab_str)
                + _to_float(tax_str)
                + _to_float(ship_str)
                + _to_float(fgt_str)
            )
            total_item = self.product_table.item(row, COL_IDX_TOTAL)
            if total_item is None:
                total_item = QTableWidgetItem("")
                total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.product_table.setItem(row, COL_IDX_TOTAL, total_item)
            total_item.setText(self._format_money(total))
        except Exception as e:
            print(f"[PurchaseDialog] 重算总金额失败 row={row}: {e}")

    def _format_money(self, amount: float) -> str:
        """2026-06-23：按采购币种格式化金额

        RMB 模式：附加"等值 USD"参考（按 exchange_rate 换算）
        """
        cur = getattr(self, 'purchase_currency', 'USD') or 'USD'
        base = f"{float(amount):.2f} {cur}"
        if cur == 'RMB':
            rate = getattr(self, 'exchange_rate', 6.8) or 6.8
            try:
                usd_eq = float(amount) / float(rate)
                return f"{base}\n≈ ${usd_eq:.2f} USD"
            except Exception:
                return base
        return base

    def _on_currency_changed(self):
        """2026-06-23：采购币种切换 → 刷新所有行的总金额显示

        商品单价/贴标/税费/发货/运费列保持原值（用户已输入或 fallback 的数值），
        仅总金额列的币种后缀改变。提交时把 purchase_currency 带给后端。
        """
        if hasattr(self, 'currency_radio_usd') and self.currency_radio_usd.isChecked():
            self.purchase_currency = 'USD'
        elif hasattr(self, 'currency_radio_rmb') and self.currency_radio_rmb.isChecked():
            self.purchase_currency = 'RMB'
        # 汇率输入框只在 RMB 模式可见
        self._update_rate_input_visibility()
        # 重算所有行（让总金额列带新币种后缀）
        if hasattr(self, 'product_table'):
            for row in range(self.product_table.rowCount()):
                self._recalc_total(row)
        print(f"[PurchaseDialog] 采购币种切换为: {self.purchase_currency}")

    def _update_rate_input_visibility(self):
        """2026-06-23：汇率输入框仅在 RMB 模式可见"""
        if not hasattr(self, 'exchange_rate_input'):
            return
        is_rmb = self.purchase_currency == 'RMB'
        self.exchange_rate_input.setVisible(is_rmb)
        if hasattr(self, '_rate_label'):
            self._rate_label.setVisible(is_rmb)

    def _on_exchange_rate_changed(self, value: float):
        """2026-06-23：汇率变化 → 更新 self.exchange_rate 并刷新总金额"""
        self.exchange_rate = float(value) if value else 6.8
        # 重算所有行（让总金额列 RMB 等值 USD 实时更新）
        if hasattr(self, 'product_table') and self.purchase_currency == 'RMB':
            for row in range(self.product_table.rowCount()):
                self._recalc_total(row)

    def _on_product_selection_changed(self):
        """2026-06-23：行选变化 → 把该行的 1688 链接/凭证/备注装载到顶层表单

        多产品场景下，每个产品独立维护：
        - 1688 链接（产品表 col 9）
        - 采购凭证（self._row_screenshots[row]）
        - 备注（self._row_remarks[row]）
        - 微信联系方式（self._row_contacts[row]）

        行选变化时，把当前行的值同步显示到顶层表单，方便用户修改。
        顶层表单编辑时，通过 _on_top_form_xxx_changed 写回当前行。
        """
        if not hasattr(self, 'product_table') or not self.items:
            return
        selected_rows = self.product_table.selectedItems()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if not (0 <= row < len(self.items)):
            return
        self.current_item = self.items[row]

        # 同步刷新 1688 历史链接下拉到当前行产品
        product_id = self.current_item.get('product_id')
        self._fill_link_combo(product_id)

        # 同步顶层表单的链接（与产品表 col 9 一致）
        self._loading_top_form = True
        try:
            # 1688 链接：与产品表 col 9 同步
            if hasattr(self, 'link_combo'):
                cell = self.product_table.item(row, COL_IDX_LINK)
                link_text = cell.text().strip() if cell else ''
                if self.link_combo.currentText().strip() != link_text:
                    self.link_combo.setCurrentText(link_text)

            # 微信联系方式
            if hasattr(self, 'contact_wechat_input'):
                contact = self._row_contacts.get(row, '')
                if self.contact_wechat_input.text() != contact:
                    self.contact_wechat_input.setText(contact)

            # 凭证
            if hasattr(self, 'screenshot_label'):
                shot = self._row_screenshots.get(row)
                if shot:
                    filename = shot.split('/')[-1].split('\\')[-1]
                    self.screenshot_label.setText(f"当前: {filename}")
                    self.screenshot_path = shot
                else:
                    self.screenshot_label.setText("当前: 无")
                    self.screenshot_path = None
            if hasattr(self, 'wechat_screenshot_label'):
                shot = self._row_screenshots.get(row)
                if shot:
                    filename = shot.split('/')[-1].split('\\')[-1]
                    self.wechat_screenshot_label.setText(f"当前: {filename}")
                else:
                    self.wechat_screenshot_label.setText("当前: 无")

            # 备注
            if hasattr(self, 'online_remark_input'):
                remark = self._row_remarks.get(row, '')
                if self.online_remark_input.toPlainText() != remark:
                    self.online_remark_input.setPlainText(remark)
        finally:
            self._loading_top_form = False

        print(f"[PurchaseDialog] 产品切换到 row={row}: {self.current_item.get('product_name', '临时产品')}")

    def _load_latest_for_all_rows(self):
        """2026-06-09 任务 9/15：批量加载所有行的最近采购记录
        逐行异步请求，避免 1 个慢请求阻塞整个表格刷新

        2026-06-23：先同步用产品默认报价兜底（避免异步 API 未返回时单价列为空），
        再异步加载最近采购记录覆盖（采购记录里的单价更准确）
        """
        if not hasattr(self, 'product_table') or not self.items:
            return
        for i, item in enumerate(self.items):
            # 1) 同步：先用产品默认报价（price_rmb/price_usd）填入单价等列
            try:
                self._fill_product_price_fallback(i)
            except Exception as e:
                print(f"[PurchaseDialog] row={i} 同步兜底失败: {e}")
            # 2) 异步：用最近采购记录覆盖（更准确的价格来源）
            self._load_latest_for_row(i, item)
            self._recalc_total(i)

    def _load_latest_for_row(self, row: int, item: dict):
        """2026-06-09 任务 9/15：异步加载单行最近采购（callback 模式）

        2026-06-23：record 存在但关键价格字段为 0/None 时，也回退到产品价格
        """
        product_id = item.get('product_id')
        if not product_id:
            return

        def _on_success(resp, _row=row):
            try:
                if not (resp and isinstance(resp, dict) and resp.get('success') and resp.get('record')):
                    # 2026-06-09 修复：无采购记录时回退到产品报价
                    self._fill_product_price_fallback(_row)
                    return
                record = resp['record']
                for col, key in [
                    # 2026-06-09 修复 2：商品单价并入产品信息后，前端读 record['unit_price']
                    # 旧 record['price'] 来自 po_item 表，可能与新版 1688 unit_price 不同步
                    (COL_IDX_UNIT_PRICE, 'unit_price'),
                    (COL_IDX_LABELING, 'labeling_fee'),
                    (COL_IDX_TAX, 'tax_fee'),
                    (COL_IDX_SHIPPING, 'shipping_fee'),
                    (COL_IDX_FREIGHT, 'freight'),
                ]:
                    cell = self.product_table.item(_row, col)
                    if cell is None:
                        cell = QTableWidgetItem("")
                        self.product_table.setItem(_row, col, cell)
                    if not cell.text().strip():
                        val = record.get(key)
                        if val is not None:
                            cell.setText(f"{val:.2f}" if isinstance(val, (int, float)) else str(val))
                # 2026-06-23：采购记录中商品单价仍为 0 → 触发产品 fallback
                unit_cell = self.product_table.item(_row, COL_IDX_UNIT_PRICE)
                if unit_cell and not unit_cell.text().strip():
                    print(f"[PurchaseDialog] row={_row} 采购记录无单价，触发产品价格 fallback")
                    self._fill_product_price_fallback(_row)
                    return
                self._recalc_total(_row)
            except Exception as e:
                print(f"[PurchaseDialog] 应用 row={_row} 最近采购失败: {e}")

        def _on_error(exc, _row=row):
            print(f"[PurchaseDialog] 加载 row={_row} 最近采购失败: {exc}")
            # 2026-06-09 修复：无采购记录时回退到产品人民币报价
            self._fill_product_price_fallback(_row)

        async_loader = getattr(self.api_client, "get_product_latest_purchase_async", None)
        if callable(async_loader):
            async_loader(product_id, on_success=_on_success, on_error=_on_error)
        else:
            # 降级：同步
            try:
                resp = self.api_client.get_product_latest_purchase(product_id)
                _on_success(resp, row)
            except Exception as e:
                _on_error(e, row)

    def _fill_product_price_fallback(self, row: int):
        """无采购记录时，用产品的价格字段填充对应列

        2026-06-23 修复：正式产品（无采购记录）单价无法自动获取的问题
        - 兼容多种价格字段名（price_rmb/price_usd/exw_price_excl/exw_price_incl）
        - 当单元格里已有值时不覆盖（用户已手动修改优先）
        - 失败时打印详细诊断日志
        """
        item = self.items[row] if row < len(self.items) else None
        if not item:
            return
        product_id = item.get('product_id')
        if not product_id:
            print(f"[PurchaseDialog] row={row} 无 product_id（可能是临时产品），跳过单价回退")
            return
        try:
            product = self.api_client.get_customer_product_by_id(product_id)
            if not product:
                print(f"[PurchaseDialog] row={row} product_id={product_id} 获取产品失败")
                return

            # 列 → 候选价格字段（按优先级排列）
            # 优先 RMB（采购用人民币），fallback 到 USD，最后用其他价格字段
            column_price_keys = {
                COL_IDX_UNIT_PRICE: ('price_rmb', 'price_usd', 'exw_price_excl', 'exw_price_incl', 'fob_price_excl', 'fob_price_incl'),
                COL_IDX_LABELING:   ('labeling_fee', 'label_fee'),
                COL_IDX_TAX:        ('tax_fee', 'tax'),
                COL_IDX_SHIPPING:   ('shipping_fee',),
                COL_IDX_FREIGHT:    ('freight', 'freight_fee'),
            }
            filled_any = False
            for col, keys in column_price_keys.items():
                cell = self.product_table.item(row, col)
                if cell is None:
                    cell = QTableWidgetItem("")
                    self.product_table.setItem(row, col, cell)
                if cell.text().strip():
                    # 已有值不覆盖
                    continue
                for k in keys:
                    val = product.get(k)
                    if val is not None:
                        try:
                            fval = float(val)
                            if fval > 0:
                                cell.setText(f"{fval:.2f}")
                                filled_any = True
                                break
                        except (ValueError, TypeError):
                            continue

            if filled_any:
                print(f"[PurchaseDialog] row={row} product_id={product_id} 单价回退成功")
            else:
                print(f"[PurchaseDialog] row={row} product_id={product_id} 产品无价格字段可用（price_rmb/price_usd/exw_price_*）")

            self._recalc_total(row)
        except Exception as e:
            print(f"[PurchaseDialog] 产品价格回退失败 row={row}: {e}")

    # 2026-06-09 任务 12：移除 _reset_fee_fields / _reset_input_style / _reset_invoice_fields
    # 旧版依赖的 recent_purchase_group 在新设计中已废弃（改为行内 9 列合一）
    # 故删除这些"重置旧版字段"的工具方法，避免对不存在的属性崩溃。

    def _on_tab_changed(self, index):
        """Tab切换处理"""
        self.purchase_type = 'online' if index == 0 else 'offline'
        print(f"[PurchaseDialog] Tab切换: {self.purchase_type}")
    
    def _on_platform_changed(self, platform: str):
        """平台切换处理"""
        self.platform = platform
        
        if platform == '1688':
            self.platform_1688_group.show()
            self.platform_wechat_group.hide()
        else:
            self.platform_1688_group.hide()
            self.platform_wechat_group.show()
        
        print(f"[PurchaseDialog] 平台切换: {platform}")
    
    # 2026-06-09 任务 12：_on_fee_changed 由 cellChanged 取代（见 _on_product_cell_changed）
    # _open_latest_link 由 1688 表单自带的 link_input 取代
    
    def _on_contract_generate_changed(self, state):
        """合同生成选项变化"""
        enabled = state == Qt.CheckState.Checked.value
        self.template_combo.setEnabled(enabled)
        print(f"[PurchaseDialog] 合同生成: {enabled}")
    
    def _on_supplier_changed(self, index):
        """供应商选择变化"""
        supplier_data = self.supplier_combo.currentData()
        if supplier_data:
            print(f"[PurchaseDialog] 选择供应商: {supplier_data}")
    
    def _open_link_in_browser(self):
        """在浏览器打开当前选中行的 1688 链接"""
        import webbrowser
        # 2026-06-12 需求 #44：链接已迁到产品表的第 10 列，从当前选中行读取
        row = self.product_table.currentRow() if hasattr(self, 'product_table') else -1
        link = ""
        if 0 <= row:
            cell = self.product_table.item(row, COL_IDX_LINK)
            if cell:
                link = cell.text().strip()
        # 兜底：尝试从顶层 combo 读取（兼容旧调用）
        if not link and hasattr(self, 'link_combo'):
            link = self.link_combo.currentText().strip()
        if link:
            webbrowser.open(link)

    def _on_link_combo_changed(self, text: str):
        """2026-06-12 需求 #44：1688 下拉选项变化 → 写回当前产品行的第 10 列
        允许用户在历史链接中点选一个不同的链接给当前产品
        （每个产品行独立，可能来自不同链接）
        """
        if self._loading_top_form:
            return
        if not hasattr(self, 'product_table') or not self.current_item:
            return
        if self.current_item not in self.items:
            return
        row = self.items.index(self.current_item)
        cell = self.product_table.item(row, COL_IDX_LINK)
        if cell is None:
            cell = QTableWidgetItem("")
            self.product_table.setItem(row, COL_IDX_LINK, cell)
        if cell.text().strip() != text.strip():
            cell.setText(text.strip())

    def _on_top_form_remark_changed(self):
        """2026-06-23：备注输入变化 → 写回当前行"""
        if self._loading_top_form:
            return
        if not hasattr(self, 'product_table') or not self.current_item:
            return
        if self.current_item not in self.items:
            return
        row = self.items.index(self.current_item)
        if hasattr(self, 'online_remark_input'):
            self._row_remarks[row] = self.online_remark_input.toPlainText()

    def _on_top_form_contact_changed(self):
        """2026-06-23：微信联系方式变化 → 写回当前行"""
        if self._loading_top_form:
            return
        if not hasattr(self, 'product_table') or not self.current_item:
            return
        if self.current_item not in self.items:
            return
        row = self.items.index(self.current_item)
        if hasattr(self, 'contact_wechat_input'):
            self._row_contacts[row] = self.contact_wechat_input.text().strip()
    
    def _open_wechat_link(self):
        """打开微信采购关联的1688链接"""
        import webbrowser
        link = self.wechat_link_input.text().strip()
        if link:
            webbrowser.open(link)
    
    # 2026-06-09 任务 12：_open_latest_link 删除（最近链接功能由 1688 表单自带 link_input 承担）
    
    def _select_screenshot(self):
        """2026-06-23：选择采购凭证截图 → 存到当前行的 _row_screenshots

        多产品场景下，每行独立维护凭证文件路径。
        顶层 _select_screenshot 由 1688 / 微信两个分组共用，所以通过 current_item 找到行。
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择截图", "", "图片文件 (*.png *.jpg *.jpeg *.gif)"
        )
        if file_path:
            self.screenshot_path = file_path
            filename = file_path.split('/')[-1].split('\\')[-1]

            # 2026-06-23：写入当前行级存储
            row = self._get_current_product_row()
            if row is not None:
                self._row_screenshots[row] = file_path

            if hasattr(self, 'screenshot_label'):
                self.screenshot_label.setText(f"当前: {filename}")
            if hasattr(self, 'wechat_screenshot_label'):
                self.wechat_screenshot_label.setText(f"当前: {filename}")
    
    def _select_invoice(self):
        """选择发票文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择发票", "", "PDF文件 (*.pdf);;图片文件 (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.invoice_path = file_path
            filename = file_path.split('/')[-1].split('\\')[-1]
            self.invoice_label.setText(f"当前文件: {filename}")
    
    def _upload_invoice(self):
        """上传发票"""
        if not self.invoice_path:
            QMessageBox.warning(self, "提示", "请先选择发票文件")
            return
        
        try:
            response = self.api_client.upload_purchase_invoice(self.invoice_path)
            if response and response.get('success'):
                self.invoice_path = response.get('file_path', self.invoice_path)
                QMessageBox.information(self, "成功", "发票上传成功")
            else:
                QMessageBox.warning(self, "错误", response.get('message', '上传失败'))
        except Exception as e:
            QMessageBox.warning(self, "错误", f"上传失败: {e}")
    
    def _add_supplier(self):
        """新增供应商"""
        from widgets.supplier_dialog import SupplierDialog
        dialog = SupplierDialog(self.api_client, parent=self)
        if dialog.exec():
            self._reload_suppliers()
    
    def _reload_suppliers(self):
        """重新加载供应商列表"""
        try:
            suppliers = self.api_client.get_suppliers()
            self.supplier_combo.clear()
            self.supplier_combo.addItem("-- 请选择 --", None)
            for s in suppliers:
                self.supplier_combo.addItem(
                    f"{s.get('supplier_code', '')} - {s.get('supplier_name', '')}",
                    s.get('id')
                )
        except Exception as e:
            print(f"[PurchaseDialog] 加载供应商失败: {e}")
    
    def _fill_link_combo(self, product_id: int | None):
        """2026-06-12 需求 #44：为当前产品填充 1688 历史链接下拉
        优先级：self._prefill_urls[product_id] > 当前行已有链接 > 无

        下拉的"当前选中"会通过 currentTextChanged 同步写回当前产品行的第 10 列，
        实现"从历史链接里快速选一个不同的链接给该产品"的效果。
        """
        self.link_combo.blockSignals(True)
        self.link_combo.clear()
        self.link_combo.setEditText("")

        if product_id and product_id in self._prefill_urls:
            urls = self._prefill_urls[product_id]
            if urls:
                self.link_combo.addItems(urls)
                # 优先选当前行已有的链接（如果它就在历史里），否则选第一个
                current_link = ""
                if hasattr(self, 'product_table') and self.current_item:
                    row = self.items.index(self.current_item) if self.current_item in self.items else -1
                    if row >= 0:
                        cell = self.product_table.item(row, COL_IDX_LINK)
                        if cell:
                            current_link = cell.text().strip()
                if current_link and current_link in urls:
                    self.link_combo.setCurrentText(current_link)
                else:
                    self.link_combo.setCurrentIndex(0)
        # else: 用户手动输入，无历史记录

        self.link_combo.blockSignals(False)

    # 2026-06-09 任务 12：移除 _load_latest_purchase / _auto_fill_fees
    # 改为行级 _load_latest_for_row/_load_latest_for_all_rows

    def _submit(self):
        """提交采购"""
        if not self._validate():
            return
        
        try:
            data = self._collect_data()
            
            # 调用API创建采购订单
            response = self.api_client.create_purchase(data)
            
            if response and response.get('success'):
                purchase_id = response.get('purchase_id')
                
                # 上传发票（如有）
                if self.invoice_path and not self.invoice_path.startswith('/uploads/'):
                    self.api_client.upload_purchase_invoice(self.invoice_path, purchase_id)
                
                # 发送完成信号
                result_data = {
                    'purchase_id': purchase_id,
                    'updated_items': response.get('updated_items', []),
                    'contract_url': response.get('contract_url')
                }
                self.purchase_completed.emit(result_data)
                
                QMessageBox.information(self, "成功", f"采购订单创建成功\n订单ID: {purchase_id}")
                self.accept()
            else:
                error_msg = response.get('message', '创建采购订单失败') if response else '无响应'
                QMessageBox.warning(self, "错误", f"创建采购订单失败: {error_msg}")
                self.error_occurred.emit(error_msg)
                
        except Exception as e:
            print(f"[PurchaseDialog] 提交采购失败: {e}")
            QMessageBox.warning(self, "错误", f"提交失败: {e}")
            self.error_occurred.emit(str(e))
    
    def _validate(self) -> bool:
        """验证表单

        [2026-06-17 计划 Task 4] 增强: 检查每行 supplier_id (行级优先, 顶层 fallback)
        2026-06-23：线上采购（1688/微信）提前解析 supplier_id（通过 find-or-create），
                   避免校验时 supplier_id 还没建立导致的"缺少供应商"误报
        """
        if not self.items:
            QMessageBox.warning(self, "提示", "请选择要采购的产品")
            return False

        # 2026-06-23：线上采购（1688/微信）提前解析 supplier_id，灌入 self.items
        # 否则下方的 supplier_id 校验会因为 supplier_id 还没建立而误报
        if self.purchase_type == 'online':
            if self.platform == '1688':
                shop_name = self.shop_name_input.text().strip() if hasattr(self, 'shop_name_input') else ''
                if not shop_name:
                    QMessageBox.warning(self, "提示", "请输入 1688 店铺名称（将作为供应商名称）")
                    if hasattr(self, 'shop_name_input'):
                        self.shop_name_input.setFocus()
                    return False
                # 2026-06-23：缓存已解析的 supplier_id，同一店铺名不重复调 API
                if (not getattr(self, '_resolved_online_supplier_id', None)
                        or getattr(self, '_resolved_online_supplier_name', None) != shop_name):
                    supplier_info = self._resolve_online_supplier(shop_name, contact=self.contact_wechat_input.text().strip() if hasattr(self, 'contact_wechat_input') else None)
                    if supplier_info and supplier_info.get('id'):
                        self._resolved_online_supplier_id = supplier_info['id']
                        self._resolved_online_supplier_name = shop_name
                resolved_id = getattr(self, '_resolved_online_supplier_id', None)
                if resolved_id:
                    for item in self.items:
                        if not item.get('supplier_id'):
                            item['supplier_id'] = resolved_id
            elif self.platform == 'wechat':
                wechat_nick = self.wechat_nickname_input.text().strip() if hasattr(self, 'wechat_nickname_input') else ''
                wechat_id = self.wechat_id_input.text().strip() if hasattr(self, 'wechat_id_input') else ''
                if not wechat_nick:
                    QMessageBox.warning(self, "提示", "请输入微信昵称（将作为供应商名称）")
                    if hasattr(self, 'wechat_nickname_input'):
                        self.wechat_nickname_input.setFocus()
                    return False
                if (not getattr(self, '_resolved_online_supplier_id', None)
                        or getattr(self, '_resolved_online_supplier_name', None) != wechat_nick):
                    supplier_info = self._resolve_online_supplier(wechat_nick, contact=wechat_id)
                    if supplier_info and supplier_info.get('id'):
                        self._resolved_online_supplier_id = supplier_info['id']
                        self._resolved_online_supplier_name = wechat_nick
                resolved_id = getattr(self, '_resolved_online_supplier_id', None)
                if resolved_id:
                    for item in self.items:
                        if not item.get('supplier_id'):
                            item['supplier_id'] = resolved_id

        # 2026-06-17 计划: 检查每行 supplier_id (行级 supplier_id 优先, 顶层 supplier_combo 作为回退)
        top_supplier_id = self.supplier_combo.currentData() if hasattr(self, 'supplier_combo') and self.supplier_combo else None
        for i, item in enumerate(self.items):
            row_supplier_id = item.get('supplier_id') or top_supplier_id
            if not row_supplier_id:
                QMessageBox.warning(self, "提示", f"第 {i+1} 个产品缺少供应商, 请在产品上指定 supplier_id 或在对话框顶部选择供应商")
                return False

        # 多产品时，检查采购数量
        if len(self.items) > 1 and hasattr(self, 'product_table'):
            for i in range(self.product_table.rowCount()):
                qty_text = self.product_table.item(i, 3).text().strip()
                if not qty_text or int(qty_text or 0) <= 0:
                    QMessageBox.warning(self, "提示", f"第 {i+1} 个产品的采购数量必须大于 0")
                    return False

        if self.purchase_type == 'online':
            if self.platform == '1688':
                # 2026-06-23：1688 店铺名称必填（用于建立 supplier_id）
                shop_name = self.shop_name_input.text().strip() if hasattr(self, 'shop_name_input') else ''
                if not shop_name:
                    QMessageBox.warning(self, "提示", "请输入 1688 店铺名称（将作为供应商名称）")
                    if hasattr(self, 'shop_name_input'):
                        self.shop_name_input.setFocus()
                    return False
                # 2026-06-12 需求 #44：1688 链接已迁到产品表的第 10 列，按行校验
                if hasattr(self, 'product_table'):
                    for i in range(self.product_table.rowCount()):
                        cell = self.product_table.item(i, COL_IDX_LINK)
                        link = cell.text().strip() if cell else ""
                        if not link:
                            QMessageBox.warning(self, "提示", f"第 {i+1} 个产品的 1688 链接不能为空")
                            return False
            elif self.platform == 'wechat':
                wechat_id = self.wechat_id_input.text().strip()
                if not wechat_id:
                    QMessageBox.warning(self, "提示", "请输入微信号")
                    return False
                wechat_nickname = self.wechat_nickname_input.text().strip()
                if not wechat_nickname:
                    QMessageBox.warning(self, "提示", "请输入微信昵称（将作为供应商名称）")
                    return False

        return True
    
    def _collect_data(self) -> dict:
        """2026-06-09 任务 14：商品单价并入产品信息 - 收集表单数据
        - 9 列合一表格：每个 item 在自己的行上带 5 项费用
        - 顶层不再保留 price/labeling_fee/tax_fee/shipping_fee 顶层字段
        - 单产品时也走相同的 items 列表（1 条）
        - 2026-06-09 修复 422：添加必填字段 dept_id, pi_id，修正字段名

        [2026-06-17 计划 Task 4] 逐行提交 supplier_id 和快照字段, 服务端 create_grouped_purchase_orders 按 supplier_id 自动分组
        """
        def _cell_text(row, col):
            item = self.product_table.item(row, col) if hasattr(self, 'product_table') else None
            return item.text().strip() if item else ""

        def _cell_float(row, col):
            try:
                return float(_cell_text(row, col) or 0)
            except (ValueError, TypeError):
                return 0.0

        def _cell_int(row, col):
            try:
                return int(float(_cell_text(row, col) or 0))
            except (ValueError, TypeError):
                return 0

        # 顶层供应商选择 (作为行级 supplier_id 的回退)
        top_supplier_id = self.supplier_combo.currentData() if hasattr(self, 'supplier_combo') and self.supplier_combo else None

        # 2026-06-09 修复：构建符合后端 schema 的 items 列表
        # 后端 PurchaseOrderItemCreate 必填字段：product_id, quantity, unit_price
        # 2026-06-17 计划: 逐行携带 supplier_id / product_name / customer_model / pi_item_id / product_image / link 等快照
        enriched_items = []
        for i, item in enumerate(self.items):
            product_id = item.get('product_id')
            if product_id is None:
                continue

            enriched_items.append({
                "product_id": product_id,
                "pi_item_id": item.get('id') or item.get('pi_item_id'),
                # 行级 supplier_id: 优先 item.supplier_id, 其次顶层 supplier_combo
                "supplier_id": item.get('supplier_id') or top_supplier_id,
                # 展示级快照字段 (后端会写入 *_snapshot 列)
                "product_name": item.get('product_name') or item.get('detail_desc'),
                "customer_model": item.get('customer_model') or item.get('model'),
                "factory_code": item.get('factory_code') or item.get('model'),
                "product_image": item.get('product_image') or item.get('pic_url'),
                "color": item.get('color'),
                "detail_requirement": item.get('detail_requirement'),
                # 数量与费用
                "quantity": _cell_int(i, COL_IDX_QTY),
                "unit_price": _cell_float(i, COL_IDX_UNIT_PRICE),
                "labeling_fee": _cell_float(i, COL_IDX_LABELING),
                "tax_fee": _cell_float(i, COL_IDX_TAX),
                "shipping_fee": _cell_float(i, COL_IDX_SHIPPING),
                "freight": _cell_float(i, COL_IDX_FREIGHT),
                # 2026-06-12 需求 #44：每个产品独立 1688 链接, 后端写入 line_1688_url
                "link": _cell_text(i, COL_IDX_LINK),
                # 2026-06-23：每行独立凭证路径 / 备注
                "screenshot_path": self._row_screenshots.get(i),
                "remark": self._row_remarks.get(i, ''),
                "contact": self._row_contacts.get(i, ''),
            })

        # 2026-06-09 修复：添加必填字段 dept_id, pi_id
        data = {
            'dept_id': self.dept_id or 'S',  # 默认使用 'S' 部门
            'pi_id': self.pi_id,
            'supplier_id': top_supplier_id,
            'items': enriched_items,
            # 2026-06-23：采购币种（顶部 radio 选择），后端按此币种写入 PO 单
            'currency': getattr(self, 'purchase_currency', 'USD'),
            # 2026-06-23：人民币→美元汇率（RMB 模式使用），后端换算等值 USD
            'exchange_rate': float(getattr(self, 'exchange_rate', 6.8) or 6.8),
        }

        if self.purchase_type == 'online':
            data['platform'] = self.platform
            # 2026-06-23：supplier_id 已在 _validate 阶段解析并写入 self.items，
            # 这里直接用 _resolved_online_supplier_id 避免重复调 API
            resolved_id = getattr(self, '_resolved_online_supplier_id', None)
            resolved_name = getattr(self, '_resolved_online_supplier_name', None)
            if self.platform == '1688':
                # 2026-06-12 需求 #44：1688 链接已迁到产品表的第 10 列（每行独立），不再使用顶层字段
                data['contact_wechat'] = self.contact_wechat_input.text().strip()
                # 1688 店铺名称（必填）→ supplier_id
                shop_name = self.shop_name_input.text().strip() if hasattr(self, 'shop_name_input') else ''
                if not resolved_id and shop_name:
                    # 兜底：_validate 失败时仍尝试解析一次
                    supplier_info = self._resolve_online_supplier(shop_name, contact=data['contact_wechat'])
                    if supplier_info:
                        resolved_id = supplier_info.get('id')
                        resolved_name = shop_name
                if resolved_id:
                    data['supplier_id'] = resolved_id
                    data['supplier_name'] = resolved_name or shop_name
                    for item in data.get('items', []):
                        if not item.get('supplier_id'):
                            item['supplier_id'] = data['supplier_id']
            else:
                data['wechat_id'] = self.wechat_id_input.text().strip()
                data['wechat_nickname'] = self.wechat_nickname_input.text().strip()
                # 微信采购的 1688 关联链接仍保留在顶层（旧字段）
                data['link'] = self.wechat_link_input.text().strip()
                # 微信昵称（必填）→ supplier_id
                wechat_nick = data['wechat_nickname']
                if not resolved_id and wechat_nick:
                    supplier_info = self._resolve_online_supplier(wechat_nick, contact=data['wechat_id'])
                    if supplier_info:
                        resolved_id = supplier_info.get('id')
                        resolved_name = wechat_nick
                if resolved_id:
                    data['supplier_id'] = resolved_id
                    data['supplier_name'] = resolved_name or wechat_nick
                    for item in data.get('items', []):
                        if not item.get('supplier_id'):
                            item['supplier_id'] = data['supplier_id']
            data['screenshot'] = self.screenshot_path
            data['remark'] = self.online_remark_input.toPlainText().strip()

        # 发票（2026-06-23：未勾选"需要发票"则不传 invoice 字段，后端 invoice_type 留空 = 无发票）
        if hasattr(self, 'need_invoice_checkbox') and not self.need_invoice_checkbox.isChecked():
            data['invoice_path'] = None
            data['invoice_amount'] = 0
            data['invoice_currency'] = None
            data['invoice_type'] = None  # None = 无发票（后端允许）
        else:
            data['invoice_path'] = self.invoice_path
            data['invoice_amount'] = self._parse_float(self.invoice_amount_input.text())
            data['invoice_currency'] = self.invoice_currency_combo.currentText()
        
        # 线下采购
        if self.purchase_type == 'offline':
            data['generate_contract'] = self.generate_contract_checkbox.isChecked()
            data['contract_template_id'] = self.template_combo.currentData()
            data['supplier_id'] = self.supplier_combo.currentData()
            data['supplier_contact'] = self.supplier_contact_input.text().strip()
            data['supplier_phone'] = self.supplier_phone_input.text().strip()
            data['remark'] = self.offline_remark_input.toPlainText().strip()
            data['contract_remark'] = self.contract_remark_input.toPlainText().strip()

        return data

    def _resolve_online_supplier(self, supplier_name: str, contact: str = None) -> Optional[Dict]:
        """2026-06-23：线上采购（1688/微信）按名称解析 supplier_id

        调用 /api/suppliers/find-or-create 端点：
        - 名称匹配 → 复用现有 supplier，返回 id
        - 名称不存在 → 自动创建新 supplier（店铺/微信昵称作为 supplier_name）

        失败时（API 错误/超时）返回 None，由调用方决定是否走 fallback
        """
        if not supplier_name:
            return None
        try:
            res = self.api_client.find_or_create_supplier(
                supplier_name=supplier_name,
                dept_id=self.dept_id or 'S',
                contact_person=contact or '',
            )
            if res and isinstance(res, dict) and res.get('id'):
                created = res.get('created', False)
                action = '新建' if created else '复用'
                print(f"[PurchaseDialog] {action} supplier: id={res['id']}, name={supplier_name}")
                return res
            print(f"[PurchaseDialog] find-or-create 返回异常: {res}")
            return None
        except Exception as e:
            print(f"[PurchaseDialog] find-or-create 失败: {e}")
            return None

    def _parse_float(self, text: str) -> float:
        """解析浮点数"""
        try:
            return float(text.strip()) if text.strip() else 0.0
        except ValueError:
            return 0.0

    def _export_contract_after_purchase(self, purchase_id: int, result: dict):
        """线下采购成功后自动导出合同文件"""
        try:
            import tempfile, os

            # 调用导出API获取Excel字节流
            content = self.api_client.export_contract_excel(purchase_id)

            # 生成文件名（使用采购单号或ID）
            po_no = result.get('po_no', str(purchase_id))
            filename = f"Contract_{po_no}.xlsx"
            filepath = os.path.join(tempfile.gettempdir(), filename)
            with open(filepath, 'wb') as f:
                f.write(content)

            # 询问用户是否打开文件
            reply = QMessageBox.question(
                self,
                "合同已生成",
                f"采购合同已生成：{filename}\n\n是否立即打开？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(filepath)

            print(f"[PurchaseDialog] 合同导出成功: {filename}")
        except Exception as e:
            # 导出失败不阻断采购流程，仅提示
            print(f"[PurchaseDialog] 合同导出失败: {e}")
            QMessageBox.information(
                self,
                "提示",
                f"采购单已创建成功，但合同导出失败：{str(e)}\n\n"
                "您可以在采购列表中手动导出合同。"
            )

    def _submit(self):
        """提交采购订单"""
        # 1. 校验
        if not self._validate():
            return

        # 线下采购额外校验：供应商必选
        if self.purchase_type == 'offline':
            supplier_id = self.supplier_combo.currentData()
            if not supplier_id:
                QMessageBox.warning(self, "提示", "请选择供应商")
                return

        # 2. 收集数据
        data = self._collect_data()

        # 3. 调用 API（根据采购类型选择正确的端点）
        try:
            # 2026-06-09 修复：根据采购类型选择正确的API端点
            if self.purchase_type == 'online':
                # 线上采购（1688/微信）使用 /purchase-orders/1688
                result = self.api_client.post("/purchase-orders/1688", data)
            else:
                # 线下采购使用 /purchase-orders
                result = self.api_client.post("/purchase-orders", data)

            if result and (result.get('success', False) or 'purchase_id' in result or 'id' in result):
                # 采购成功
                purchase_id = result.get('purchase_id') or result.get('id')

                # 线下采购：如果勾选了"生成采购合同"，自动导出合同文件
                if self.purchase_type == 'offline' and self.generate_contract_checkbox.isChecked():
                    self._export_contract_after_purchase(purchase_id, result)

                # 发射信号并关闭对话框
                self.purchase_completed.emit(result)
                self.accept()
            else:
                msg = result.get('message', result.get('error', '采购失败，请重试')) if result else '无响应'
                QMessageBox.warning(self, "提示", f"采购失败: {msg}")
                self.error_occurred.emit(msg)

        except Exception as e:
            error_msg = str(e)
            print(f"[PurchaseDialog] 采购提交异常: {error_msg}")
            QMessageBox.warning(self, "错误", f"采购提交失败: {error_msg}")
            self.error_occurred.emit(error_msg)
