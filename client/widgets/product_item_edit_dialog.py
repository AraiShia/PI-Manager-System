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
    QFileDialog
)
from PySide6.QtCore import Qt, QDate


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
        33: "carton_size_edit",
        34: "pack_spec_edit",
        37: "carton_gross_weight_spin",
    }

    def __init__(self, item, products=None, api_client=None,
                 focus_column=None, has_formal=False, is_purchased=False,
                 parent=None):
        super().__init__(parent)
        self.item = item.copy() if item else {}
        self.products = products or []
        self.api_client = api_client
        self.focus_column = focus_column
        self.has_formal = has_formal
        self.is_purchased = is_purchased
        self.setWindowTitle("编辑产品")
        self.resize(768, 1280)
        self._editors = {}
        self.image_path = self.item.get("image_url") or self.item.get("default_image_url", "")
        self.init_ui()
        self._apply_locks()
        self._apply_focus()

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
        self._add_line_edit(base_form, "customer_model", "客户型号", self.item.get("customer_model", ""))
        self._add_line_edit(base_form, "product_feature", "产品特性", self.item.get("product_feature", ""))
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
        self._add_combo(pack_form, "packaging", "包装方式", ["1件/箱", "多件/箱", "1件多箱"], self.item.get("packaging", ""))
        self._add_line_edit(pack_form, "purchase_option_name", "采购选项/名称", self.item.get("purchase_option_name", ""))
        self._add_line_edit(pack_form, "product_detail", "产品细节", self.item.get("product_detail", ""))
        self._add_line_edit(pack_form, "carton_size", "纸箱尺寸", self.item.get("carton_size", ""))
        self._add_line_edit(pack_form, "pack_spec", "打包规格", self.item.get("pack_spec", ""))
        self._add_spin(pack_form, "carton_gross_weight", "整箱毛重", self.item.get("carton_gross_weight", 0))
        layout.addLayout(pack_form)

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

    def _add_combo(self, form, key, label, options, value):
        combo = QComboBox()
        combo.addItems(options)
        combo.setEditable(True)
        idx = combo.findText(str(value or ""))
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            combo.setCurrentText(str(value or ""))
        combo.setObjectName(key + "_combo")
        form.addRow(f"{label}:", combo)
        self._editors[key] = combo

    def _add_image_field(self, layout):
        img_layout = QHBoxLayout()
        img_layout.addWidget(QLabel("图片:"))
        self.image_path_label = QLabel(self.image_path or "无图片")
        self.image_path_label.setWordWrap(True)
        img_layout.addWidget(self.image_path_label)
        upload_btn = QPushButton("上传图片")
        upload_btn.clicked.connect(self._upload_image)
        img_layout.addWidget(upload_btn)
        clear_btn = QPushButton("清除图片")
        clear_btn.clicked.connect(self._clear_image)
        img_layout.addWidget(clear_btn)
        layout.addLayout(img_layout)

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
                        "purchase_option_name", "product_detail", "carton_size",
                        "pack_spec", "carton_gross_weight"]:
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

    def _upload_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return
        if self.api_client:
            try:
                url = self.api_client.upload_image(path, product_id=self.item.get("product_id"))
                self.image_path = url
                self.image_path_label.setText(url)
            except Exception as e:
                QMessageBox.warning(self, "上传失败", str(e))
        else:
            self.image_path = path
            self.image_path_label.setText(path)

    def _clear_image(self):
        self.image_path = ""
        self.image_path_label.setText("无图片")

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
                self.api_client.update_pi_item(self.item["id"], result)
                self.accept()
            except Exception as e:
                QMessageBox.warning(self, "保存失败", str(e))
        else:
            self.accept()

    def get_item(self):
        """兼容旧接口，返回编辑后的 item 字典"""
        return self.item

    def get_data(self):
        """返回要提交到后端的字段字典"""
        return getattr(self, "result_data", {})
