# ============================================================
# 单条订单对话框 - Qt前端实现
# 文件：client/widgets/single_order_dialog.py
# 创建日期：2026-06-01
# 用途：单条订单快速创建（使用搜索模式筛选产品）
# ============================================================

from typing import List, Dict, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton, 
    QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QDate, QThread
from PySide6.QtGui import QFont

import os


class CustomerLoader(QThread):
    """客户列表加载线程"""
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
    
    def run(self):
        try:
            response = self.api_client.get("/customers/")
            if response and isinstance(response, list):
                self.finished.emit(response)
            else:
                self.error.emit("加载客户列表失败")
        except Exception as e:
            self.error.emit(str(e))


class SingleOrderDialog(QDialog):
    """
    单条订单快速创建对话框
    
    功能：
    - 选择客户
    - 搜索并选择产品（输入即搜索模式）
    - 输入数量和单价
    - 自动计算金额
    """
    
    def __init__(self, api_client, parent=None, customer_id=None, mode='import'):
        """
        Args:
            api_client: API 客户端
            parent: 父窗口
            customer_id: 预选客户 ID（补充模式下使用）
            mode: 'import' (默认，下单模式) | 'supplement' (补充单条产品到预览)
        """
        super().__init__(parent)
        self.api_client = api_client
        self.customers = []
        self.search_results = []
        self.selected_product = None
        # 2026-06-11 兼容 order_import_dialog.open_single_order_dialog 调用
        self._preset_customer_id = customer_id
        self._mode = mode
        self._captured_product_data = None  # supplement 模式下保存的产品数据

        self.setWindowTitle("补充单条产品" if mode == 'supplement' else "单条新增订单")
        self.setMinimumSize(500, 400)
        self.init_ui()
        self.load_customers_async()

    def get_product_data(self) -> dict:
        """返回当前录入的产品数据（导入/补充模式都通过预览表统一提交）。"""
        return self._captured_product_data

    def _try_preselect_customer(self):
        """客户列表加载完成后，若传入了 preset customer_id 则预选"""
        if self._preset_customer_id is None:
            return
        for i in range(self.customer_combo.count()):
            if self.customer_combo.itemData(i) == self._preset_customer_id:
                self.customer_combo.setCurrentIndex(i)
                self.customer_combo.setEnabled(False)  # 锁定客户不可改
                break
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        title = QLabel("单条新增订单")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        form_layout = QFormLayout()
        
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumWidth(300)
        self.customer_combo.currentIndexChanged.connect(self.on_customer_changed)
        form_layout.addRow("客户:", self.customer_combo)
        
        self.search_field_combo = QComboBox()
        self.search_field_combo.addItem("OE号 + 名称", "both")
        self.search_field_combo.addItem("仅OE号", "oe")
        self.search_field_combo.addItem("仅名称", "name")
        
        self.product_search_input = QLineEdit()
        self.product_search_input.setPlaceholderText("输入搜索关键词...")
        self.product_search_input.textChanged.connect(self.on_search_text_changed)
        self.product_search_input.returnPressed.connect(self.select_first_result)
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_field_combo)
        search_layout.addWidget(self.product_search_input)
        form_layout.addRow("产品搜索:", search_layout)
        
        self.search_results_combo = QComboBox()
        self.search_results_combo.setPlaceholderText("请选择搜索到的产品")
        self.search_results_combo.currentIndexChanged.connect(self.on_result_selected)
        form_layout.addRow("搜索结果:", self.search_results_combo)
        
        self.selected_product_label = QLabel("未选择产品")
        self.selected_product_label.setStyleSheet("color: #666; font-style: italic;")
        form_layout.addRow("已选产品:", self.selected_product_label)
        
        self.customer_code_input = QLineEdit()
        self.customer_code_input.setPlaceholderText("客户产品编号")
        form_layout.addRow("客户产品编号:", self.customer_code_input)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("Model / 客户型号")
        form_layout.addRow("Model:", self.model_input)
        
        self.oe_number_input = QLineEdit()
        self.oe_number_input.setPlaceholderText("OE号")
        form_layout.addRow("OE号:", self.oe_number_input)
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setMinimum(1)
        self.quantity_spin.setMaximum(999999)
        self.quantity_spin.setValue(1)
        self.quantity_spin.valueChanged.connect(self.calculate_amount)
        form_layout.addRow("数量:", self.quantity_spin)
        
        self.unit_price_spin = QDoubleSpinBox()
        self.unit_price_spin.setMinimum(0.01)
        self.unit_price_spin.setMaximum(999999.99)
        self.unit_price_spin.setDecimals(2)
        self.unit_price_spin.setPrefix("$ ")
        self.unit_price_spin.valueChanged.connect(self.calculate_amount)
        form_layout.addRow("单价(USD):", self.unit_price_spin)
        
        self.amount_label = QLabel("$ 0.00")
        self.amount_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        form_layout.addRow("合计金额:", self.amount_label)
        
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("padding: 8px 16px;")
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setAutoDefault(False)
        save_btn.setDefault(False)
        save_btn.clicked.connect(self.save_order)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)

        # 禁止所有按钮成为默认按钮，避免回车误触保存/取消
        for btn in self.findChildren(QPushButton):
            btn.setAutoDefault(False)
            btn.setDefault(False)

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
    
    def load_customers_async(self):
        """异步加载客户列表"""
        self.customer_combo.addItem("加载中...")
        self.customer_combo.setEnabled(False)
        
        self.customer_loader = CustomerLoader(self.api_client)
        self.customer_loader.finished.connect(self.on_customers_loaded)
        self.customer_loader.error.connect(self.on_customers_error)
        self.customer_loader.start()
    
    def on_customers_loaded(self, customers):
        """客户列表加载完成"""
        self.customers = customers
        self.customer_combo.clear()
        for customer in self.customers:
            display = f"{customer.get('customer_code', '')} - {customer.get('customer_name', '')}"
            self.customer_combo.addItem(display, customer.get('id'))
        self.customer_combo.setEnabled(True)
        # 2026-06-11 补充模式预选客户
        self._try_preselect_customer()
    
    def on_customers_error(self, error_msg):
        """客户列表加载失败"""
        self.customer_combo.clear()
        self.customer_combo.addItem("加载失败")
        QMessageBox.warning(self, "错误", f"加载客户列表失败: {error_msg}")
    
    def on_customer_changed(self, index):
        """客户选择变化时清空搜索"""
        self.product_search_input.clear()
        self.search_results_combo.clear()
        self.selected_product = None
        self.selected_product_label.setText("未选择产品")

    def on_search_text_changed(self, text):
        """搜索文本变化时延迟搜索（防抖）"""
        self.search_timer.stop()
        if len(text) >= 2:
            self.search_timer.start(300)
        else:
            self.search_results_combo.clear()
    
    def perform_search(self):
        """执行产品搜索"""
        keyword = self.product_search_input.text().strip()
        if len(keyword) < 2:
            return
        
        field = self.search_field_combo.currentData()
        
        try:
            response = self.api_client.get(f"/products/search?keyword={keyword}&limit=20&fields={field}")
            if not response:
                return

            if isinstance(response, dict):
                results = response.get("data") or response.get("results") or []
            else:
                results = response

            if isinstance(results, list):
                self.search_results = results
                self.update_search_results_list()
        except Exception as e:
            print(f"[单条新增] 搜索失败: {e}")
    
    def _product_display_text(self, product: dict) -> str:
        """生成搜索结果展示文本"""
        oe = product.get('oe_number', '') or product.get('oe', '')
        name = (
            product.get('product_name', '')
            or product.get('detail_desc', '')
            or product.get('name', '')
            or product.get('customer_model', '')
        )
        if oe and name:
            return f"{oe} - {name}"
        return oe or name or "未命名产品"

    def update_search_results_list(self):
        """更新搜索结果下拉框"""
        self.search_results_combo.blockSignals(True)
        self.search_results_combo.clear()
        for product in self.search_results:
            self.search_results_combo.addItem(self._product_display_text(product), product)
        self.search_results_combo.blockSignals(False)
        if self.search_results_combo.count() > 0:
            self.search_results_combo.showPopup()

    def select_first_result(self):
        """回车键选择第一个结果"""
        if self.search_results_combo.count() > 0:
            self.search_results_combo.setCurrentIndex(0)

    def on_result_selected(self, index: int):
        """选择搜索结果：回填到录入字段"""
        if index < 0:
            return

        product = self.search_results_combo.itemData(index)
        if not product:
            return

        self.selected_product = product
        display_text = self._product_display_text(product)
        self.selected_product_label.setText(display_text)
        self.selected_product_label.setStyleSheet("color: #10b981; font-weight: bold;")

        # 回填字段
        self.customer_code_input.setText(
            product.get('customer_code', '')
            or product.get('customer_product_code', '')
            or product.get('product_code', '')
            or ''
        )
        self.model_input.setText(
            product.get('customer_model', '')
            or product.get('model', '')
            or ''
        )
        self.oe_number_input.setText(
            product.get('oe_number', '')
            or product.get('oe', '')
            or ''
        )
        price = product.get('unit_price') or product.get('price') or product.get('price_usd') or 0
        self.unit_price_spin.setValue(float(price))

    def calculate_amount(self):
        """计算合计金额"""
        quantity = self.quantity_spin.value()
        unit_price = self.unit_price_spin.value()
        amount = quantity * unit_price
        self.amount_label.setText(f"$ {amount:.2f}")
    
    def save_order(self):
        """保存订单 / 补充单条产品"""
        if self.customer_combo.currentIndex() < 0:
            QMessageBox.warning(self, "提示", "请选择客户")
            return

        customer_id = self.customer_combo.currentData()
        product_id = None
        if self.selected_product:
            product_id = self.selected_product.get('product_id') or self.selected_product.get('product', {}).get('id')

        customer_code = self.customer_code_input.text().strip() or self.model_input.text().strip()

        product_data = {
            'customer_id': customer_id,
            'product_id': product_id,
            'customer_code': customer_code,
            'customer_model': self.model_input.text().strip(),
            'oe_number': self.oe_number_input.text().strip(),
            'quantity': self.quantity_spin.value(),
            'unit_price': float(self.unit_price_spin.value()),
        }

        if not product_data['customer_code']:
            QMessageBox.warning(self, "提示", "请输入客户产品编号")
            return
        if not product_data['oe_number']:
            QMessageBox.warning(self, "提示", "请输入OE号")
            return

        # 未匹配到已有产品时二次确认
        if not product_id and (product_data['customer_model'] or product_data['customer_code']):
            reply = QMessageBox.question(
                self,
                "未匹配到产品",
                "未匹配到已有产品，是否继续添加新商品？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # 单条录入统一返回数据，由 OrderImportDialog 的预览表统一提交
        self._captured_product_data = product_data
        self.accept()