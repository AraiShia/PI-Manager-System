# -*- coding: utf-8 -*-
"""
出货单创建对话框

文件：client/widgets/shipment_create_dialog.py
用途：从订单创建出货单

创建日期：2026-06-15

功能：
1. 显示所选PI下的所有产品（可跨PI勾选）
2. 用户输入出货数量
3. 确认后调用后端API创建出货单
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QAbstractItemView,
    QLabel, QMessageBox, QCheckBox, QSpinBox, QDoubleSpinBox, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
import logging

logger = logging.getLogger(__name__)

# 表头
PRODUCT_TABLE_HEADERS = [
    "选择", "PI号", "产品名称", "型号", "客户",
    "订单数量", "已出货", "剩余数量", "出货数量", "出货单价",
    "出货箱数", "出货体积(m³)", "出货重量(kg)"
]

PRODUCT_TABLE_COLUMN_COUNT = len(PRODUCT_TABLE_HEADERS)

# 列宽
PRODUCT_TABLE_WIDTHS = [50, 120, 150, 100, 80, 80, 80, 80, 100, 90, 70, 90, 85]


class ShipmentCreateDialog(QDialog):
    """创建出货单对话框"""
    
    # 创建完成信号
    shipment_created = Signal(dict)  # 传递创建的出货单信息
    
    def __init__(self, api_client, pi_ids: list[int], parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.pi_ids = pi_ids
        self._products = []
        self._selected_items = {}  # {pi_item_id: {"checked": bool, "shipment_qty": float}}
        
        self._init_ui()
        self._load_products()
    
    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("选择出货产品")
        self.setMinimumSize(1000, 500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel(f"已选择 {len(self.pi_ids)} 个PI订单，请选择要出货的产品")
        title_label.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(title_label)
        
        # 产品列表
        self.table = QTableWidget()
        self.table.setColumnCount(PRODUCT_TABLE_COLUMN_COUNT)
        self.table.setHorizontalHeaderLabels(PRODUCT_TABLE_HEADERS)
        
        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for i, width in enumerate(PRODUCT_TABLE_WIDTHS):
            self.table.setColumnWidth(i, width)
        
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.table)
        
        # 汇总信息
        summary_group = QGroupBox("汇总")
        summary_layout = QHBoxLayout(summary_group)
        
        self.summary_label = QLabel("出货数量: 0, 总金额: ¥0.00")
        summary_layout.addWidget(self.summary_label)
        summary_layout.addStretch()
        
        layout.addWidget(summary_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self._select_all)
        btn_layout.addWidget(select_all_btn)
        
        deselect_btn = QPushButton("反选")
        deselect_btn.clicked.connect(self._deselect_all)
        btn_layout.addWidget(deselect_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.confirm_btn = QPushButton("确认创建出货单")
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(self.confirm_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_products(self):
        """加载可出货的产品"""
        try:
            pi_ids_str = ",".join(str(pid) for pid in self.pi_ids)
            self._products = self.api_client.get(f"/shipments/shippable-items?pi_ids={pi_ids_str}") or []
            
            self.table.setRowCount(len(self._products))
            
            for row, product in enumerate(self._products):
                pi_item_id = product.get('pi_item_id')
                
                # 选择复选框
                checkbox = QCheckBox()
                checkbox.stateChanged.connect(lambda state, pid=pi_item_id: self._on_checkbox_changed(pid, state))
                self.table.setCellWidget(row, 0, checkbox)
                
                # PI号
                self.table.setItem(row, 1, QTableWidgetItem(product.get('pi_no', '-')))
                
                # 产品名称
                self.table.setItem(row, 2, QTableWidgetItem(product.get('product_name', '-')))
                
                # 型号：优先显示产品编号（C01260000），其次客户型号
                model_val = product.get('product_code') or product.get('customer_model') or '-'
                self.table.setItem(row, 3, QTableWidgetItem(model_val))
                
                # 客户
                self.table.setItem(row, 4, QTableWidgetItem(product.get('customer_name', '-')))
                
                # 订单数量
                order_qty = product.get('order_quantity', 0)
                self.table.setItem(row, 5, QTableWidgetItem(f"{order_qty:,.2f}"))
                
                # 已出货
                shipped = product.get('shipped_quantity', 0)
                self.table.setItem(row, 6, QTableWidgetItem(f"{shipped:,.2f}"))
                
                # 剩余数量
                remaining = product.get('remaining_quantity', 0)
                item = QTableWidgetItem(f"{remaining:,.2f}")
                item.setForeground(Qt.GlobalColor.darkGreen if remaining > 0 else Qt.GlobalColor.red)
                self.table.setItem(row, 7, item)
                
                # 出货数量输入
                qty_spin = QDoubleSpinBox()
                qty_spin.setRange(0, float(remaining) if remaining > 0 else 0)
                qty_spin.setValue(float(remaining) if remaining > 0 else 0)
                qty_spin.setDecimals(2)
                qty_spin.valueChanged.connect(lambda val, pid=pi_item_id: self._on_qty_changed(pid, val))
                qty_spin.setEnabled(remaining > 0)
                self.table.setCellWidget(row, 8, qty_spin)

                # 出货单价输入（用户自行编辑）
                default_price = product.get('unit_price', 0) or 0
                price_spin = QDoubleSpinBox()
                price_spin.setRange(0, 9999999)
                price_spin.setValue(default_price)
                price_spin.setDecimals(2)
                price_spin.valueChanged.connect(lambda val, pid=pi_item_id: self._on_price_changed(pid, val))
                self.table.setCellWidget(row, 9, price_spin)

                # 自动计算列：出货箱数、出货体积、出货重量（只读显示）
                cartons_item = QTableWidgetItem("0")
                cartons_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, 10, cartons_item)

                vol_item = QTableWidgetItem("0.000")
                vol_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, 11, vol_item)

                weight_item = QTableWidgetItem("0.00")
                weight_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, 12, weight_item)

                # 初始化选中状态（含包装信息用于自动计算）
                default_qty = float(remaining) if remaining > 0 else 0
                self._selected_items[pi_item_id] = {
                    "checked": False,
                    "shipment_qty": default_qty,
                    "unit_price": default_price,
                    "row": row,
                    # 包装信息
                    "pack_spec": str(product.get('pack_spec', '') or ''),
                    "carton_gross_weight": float(product.get('carton_gross_weight', 0) or 0),
                    "carton_length_cm": float(product.get('carton_length_cm', 0) or 0),
                    "carton_width_cm": float(product.get('carton_width_cm', 0) or 0),
                    "carton_height_cm": float(product.get('carton_height_cm', 0) or 0),
                }
                # 初始计算
                self._update_packaging_row(pi_item_id)
            
            self._update_summary()
            
        except Exception as e:
            logger.error(f"加载产品失败: {e}")
            QMessageBox.warning(self, "错误", f"加载产品失败:\n{str(e)}")
    
    def _on_checkbox_changed(self, pi_item_id: int, state: int):
        """复选框状态改变"""
        if pi_item_id in self._selected_items:
            self._selected_items[pi_item_id]["checked"] = (state == Qt.CheckState.Checked.value)
        self._update_summary()
    
    def _on_qty_changed(self, pi_item_id: int, value: float):
        """出货数量改变 → 自动重算箱数/体积/重量"""
        if pi_item_id in self._selected_items:
            self._selected_items[pi_item_id]["shipment_qty"] = value
        self._update_packaging_row(pi_item_id)
        self._update_summary()

    def _on_price_changed(self, pi_item_id: int, value: float):
        """出货单价改变"""
        if pi_item_id in self._selected_items:
            self._selected_items[pi_item_id]["unit_price"] = value
        self._update_summary()

    def _update_packaging_row(self, pi_item_id: int):
        """根据出货数量自动计算箱数/体积/重量并更新表格显示"""
        data = self._selected_items.get(pi_item_id)
        if not data:
            return
        row = data.get("row")
        qty = data.get("shipment_qty", 0)
        if row is None or qty <= 0:
            return

        # 解析装箱规格 (units per carton)
        units_per_carton = 0
        pack_spec = data.get('pack_spec', '')
        if pack_spec:
            import re
            m = re.match(r'(\d+)', str(pack_spec).strip())
            if m:
                units_per_carton = int(m.group(1))

        # 计算箱数
        cartons = 0
        if units_per_carton and units_per_carton > 0:
            cartons = int(qty / units_per_carton)
            if qty % units_per_carton > 0:
                cartons += 1

        # 计算重量 (单箱毛重 × 箱数)
        single_weight = data.get('carton_gross_weight', 0) or 0
        weight = round(single_weight * max(cartons, 1), 2)

        # 计算体积 (外箱尺寸 L×W×H × 箱数 → cm³ → m³)
        l_cm = data.get('carton_length_cm', 0) or 0
        w_cm = data.get('carton_width_cm', 0) or 0
        h_cm = data.get('carton_height_cm', 0) or 0
        vol_m3 = 0.0
        if l_cm > 0 and w_cm > 0 and h_cm > 0:
            vol_m3 = round(l_cm * w_cm * h_cm * max(cartons, 1) / 1_000_000, 3)

        # 存储计算结果
        data["cartons"] = cartons
        data["volume"] = vol_m3
        data["weight"] = weight

        # 更新表格显示（只读列）
        if self.table.item(row, 10):
            self.table.item(row, 10).setText(str(cartons))
        if self.table.item(row, 11):
            self.table.item(row, 11).setText(f"{vol_m3:.3f}")
        if self.table.item(row, 12):
            self.table.item(row, 12).setText(f"{weight:.2f}")
    
    def _update_summary(self):
        """更新汇总"""
        total_qty = 0
        total_amount = 0
        
        for pi_item_id, data in self._selected_items.items():
            if data["checked"]:
                total_qty += data["shipment_qty"]
                total_amount += data["shipment_qty"] * data["unit_price"]
        
        self.summary_label.setText(f"出货数量: {total_qty:,.2f}, 总金额: ¥{total_amount:,.2f}")
    
    def _select_all(self):
        """全选"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
    
    def _deselect_all(self):
        """反选"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(not checkbox.isChecked())
    
    def _on_confirm(self):
        """确认创建出货单"""
        # 收集选中的产品
        selected_items = []
        for product in self._products:
            pi_item_id = product.get('pi_item_id')
            data = self._selected_items.get(pi_item_id, {})
            
            if data.get("checked") and data.get("shipment_qty", 0) > 0:
                selected_items.append({
                    "pi_item_id": pi_item_id,
                    "product_id": product.get('product_id'),
                    "shipment_quantity": data["shipment_qty"],
                    "unit_price": data["unit_price"],
                    # 自动计算的包装信息
                    "cartons": data.get("cartons", 0),
                    "volume_m3": data.get("volume", 0),
                    "weight_kg": data.get("weight", 0),
                })
        
        if not selected_items:
            QMessageBox.warning(self, "提示", "请选择要出货的产品")
            return
        
        # 验证出货数量
        for product in self._products:
            pi_item_id = product.get('pi_item_id')
            data = self._selected_items.get(pi_item_id, {})
            
            if data.get("checked"):
                remaining = product.get('remaining_quantity', 0)
                shipment_qty = data.get("shipment_qty", 0)
                if shipment_qty > remaining:
                    QMessageBox.warning(self, "提示", 
                        f"产品 {product.get('product_name')} 的出货数量不能超过剩余数量 ({remaining:,.2f})")
                    return
        
        # 调用API创建出货单
        try:
            result = self.api_client.post("/shipments/from-orders", {
                "dept_id": "S",
                "pi_ids": self.pi_ids,
                "items": selected_items
            })
            
            if result.get("success"):
                shipment_no = result.get("shipment_no", "")
                QMessageBox.information(self, "成功", f"出货单已创建:\n{shipment_no}")
                self.shipment_created.emit(result)
                self.accept()
            else:
                QMessageBox.warning(self, "错误", f"创建失败: {result.get('message', '未知错误')}")
                
        except Exception as e:
            logger.error(f"创建出货单失败: {e}")
            QMessageBox.warning(self, "错误", f"创建出货单失败:\n{str(e)}")