# -*- coding: utf-8 -*-
"""
出货相关 Dialog

文件：client/dialogs/shipment.py
创建日期：2026-06-04
来源：main.py L9478-9733（ShipmentDialog）, L9734-9895（ShipmentStageDialog）（已迁移合并）
包含：
- ShipmentDialog: 出货对话框
- ShipmentStageDialog: 出货阶段对话框

调用方式：
```python
from dialogs import ShipmentDialog, ShipmentStageDialog

# 新建出货
dialog = ShipmentDialog(api_client, dept_id)
if dialog.exec():
    # 保存成功

# 编辑出货
dialog = ShipmentDialog(api_client, dept_id, shipment=shipment_data)
if dialog.exec():
    # 编辑成功

# 添加出货阶段
dialog = ShipmentStageDialog(parent, stage_no)
if dialog.exec():
    stage = dialog.get_stage_data()
```

依赖：
- PySide6.QtWidgets: QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QTableWidget, QTableWidgetItem,
  QPushButton, QLabel, QComboBox, QLineEdit, QDateEdit, QMessageBox
- PySide6.QtCore: Qt, QTimer
- PySide6.QtGui: QFont
- api.client.ApiClient: api_client 实例
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QComboBox,
    QLineEdit, QDateEdit, QMessageBox, QWidget, QHBoxLayout
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.client import ApiClient


class ShipmentDialog(QDialog):
    """
    出货对话框
    
    功能：
    - 新建/编辑出货单
    - 管理出货阶段（阶段名称、出货日期、柜号、提单号、数量）
    - 显示阶段数和总数量汇总
    
    构造参数：
    - api_client: ApiClient, API 客户端
    - dept_id: str, 部门ID
    - shipment: dict, 出货数据（编辑模式），None 表示新建模式
    """
    
    def __init__(self, api_client, dept_id=None, shipment=None):
        super().__init__()
        self.api_client = api_client
        self.dept_id = dept_id or "S"
        self.shipment = shipment
        self.is_edit = shipment is not None
        self.pi_orders = []
        self.stages = []
        self.init_ui()
        QTimer.singleShot(0, self.load_data)

    def load_data(self):
        """加载PI订单数据"""
        try:
            self.pi_orders = self.api_client.get_pi_orders()
            self.pi_combo.clear()
            self.pi_combo.addItem("", "")
            for pi in self.pi_orders:
                customer_name = pi.get('customer_name', '') or ''
                display_text = f"{pi.get('pi_no')} - {customer_name} - ${pi.get('total_amount', 0)}"
                self.pi_combo.addItem(display_text, pi)
            if self.shipment:
                idx = self.pi_combo.findData(self.shipment.get('pi_id'))
                if idx >= 0:
                    self.pi_combo.setCurrentIndex(idx)
                    self.pi_combo.setEnabled(False)
                if 'stages' in self.shipment and self.shipment['stages']:
                    self.stages = self.shipment['stages']
                    self.refresh_stages_table()
        except Exception as e:
            print(f"加载PI订单失败: {e}")

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("编辑出货" if self.is_edit else "新建出货")
        self.setMinimumSize(800, 600)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout()
        basic_layout.setSpacing(10)
        self.pi_combo = QComboBox()
        self.pi_combo.setFixedHeight(35)
        basic_layout.addRow("PI单:", self.pi_combo)
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        stages_group = QGroupBox("出货阶段管理")
        stages_layout = QVBoxLayout()

        self.stages_table = QTableWidget()
        self.stages_table.setColumnCount(6)
        self.stages_table.setHorizontalHeaderLabels(["阶段名称", "出货日期", "柜号", "提单号", "数量", "操作"])
        self.stages_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.stages_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.stages_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.stages_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.stages_table.setMaximumHeight(250)
        stages_layout.addWidget(self.stages_table)

        add_stage_layout = QHBoxLayout()
        add_stage_layout.addStretch()
        add_stage_btn = QPushButton("+ 添加出货阶段")
        add_stage_btn.clicked.connect(self.add_stage)
        add_stage_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        add_stage_layout.addWidget(add_stage_btn)
        stages_layout.addLayout(add_stage_layout)

        summary_layout = QHBoxLayout()
        summary_layout.addStretch()
        self.total_stages_label = QLabel("阶段数: 0")
        self.total_stages_label.setStyleSheet("font-weight: bold; color: #374151;")
        summary_layout.addWidget(self.total_stages_label)
        summary_layout.addSpacing(20)
        self.total_qty_label = QLabel("总数量: 0")
        self.total_qty_label.setStyleSheet("font-weight: bold; color: #10b981;")
        summary_layout.addWidget(self.total_qty_label)
        stages_layout.addLayout(summary_layout)

        stages_group.setLayout(stages_layout)
        layout.addWidget(stages_group)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_shipment)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        buttons_layout.addWidget(save_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def add_stage(self):
        """添加出货阶段"""
        dialog = ShipmentStageDialog(self, len(self.stages))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            stage_data = dialog.get_stage_data()
            self.stages.append(stage_data)
            self.refresh_stages_table()

    def edit_stage(self, index):
        """编辑出货阶段"""
        if index < 0 or index >= len(self.stages):
            return
        dialog = ShipmentStageDialog(self, index, self.stages[index])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.stages[index] = dialog.get_stage_data()
            self.refresh_stages_table()

    def delete_stage(self, index):
        """删除出货阶段"""
        if index < 0 or index >= len(self.stages):
            return
        reply = QMessageBox.question(self, "确认", f"确定要删除阶段 '{self.stages[index].get('stage_name')}' 吗？")
        if reply == QMessageBox.StandardButton.Yes:
            self.stages.pop(index)
            self.refresh_stages_table()

    def refresh_stages_table(self):
        """刷新阶段表格"""
        self.stages_table.setRowCount(len(self.stages))
        total_qty = 0
        for row, stage in enumerate(self.stages):
            self.stages_table.setItem(row, 0, QTableWidgetItem(stage.get('stage_name', '')))
            self.stages_table.setItem(row, 1, QTableWidgetItem(str(stage.get('shipment_date', ''))))
            self.stages_table.setItem(row, 2, QTableWidgetItem(stage.get('container_no', '')))
            self.stages_table.setItem(row, 3, QTableWidgetItem(stage.get('bl_no', '')))
            qty = stage.get('quantity', 0) or 0
            total_qty += float(qty)
            self.stages_table.setItem(row, 4, QTableWidgetItem(str(qty)))
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0, 0, 0, 0)
            edit_btn = QPushButton("编辑")
            edit_btn.setFixedWidth(50)
            edit_btn.clicked.connect(lambda _, r=row: self.edit_stage(r))
            btn_layout.addWidget(edit_btn)
            del_btn = QPushButton("删除")
            del_btn.setFixedWidth(50)
            del_btn.setStyleSheet("color: #ef4444;")
            del_btn.clicked.connect(lambda _, r=row: self.delete_stage(r))
            btn_layout.addWidget(del_btn)
            btn_widget.setLayout(btn_layout)
            self.stages_table.setCellWidget(row, 5, btn_widget)
        self.total_stages_label.setText(f"阶段数: {len(self.stages)}")
        self.total_qty_label.setText(f"总数量: {total_qty}")

    def save_shipment(self):
        """保存出货记录"""
        pi = self.pi_combo.currentData()
        if not pi:
            QMessageBox.warning(self, "警告", "请选择PI单")
            return
        if not self.stages:
            QMessageBox.warning(self, "警告", "请至少添加一个出货阶段")
            return
        stages_data = [
            {
                'id': stage.get('id'),
                'stage_name': stage.get('stage_name'),
                'shipment_date': stage.get('shipment_date'),
                'container_no': stage.get('container_no'),
                'bl_no': stage.get('bl_no'),
                'quantity': stage.get('quantity'),
                'ci_document': stage.get('ci_document'),
                'pl_document': stage.get('pl_document'),
                'storage_location': stage.get('storage_location'),
                'remark': stage.get('remark')
            }
            for stage in self.stages
        ]
        shipment_data = {
            "dept_id": self.dept_id,
            "pi_id": pi.get('id'),
            "stages": stages_data,
            "items": []
        }
        try:
            if self.is_edit:
                self.api_client.update_shipment(self.shipment.get('id'), shipment_data)
            else:
                self.api_client.create_shipment(shipment_data)
            QMessageBox.information(self, "成功", "出货记录已保存")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")


class ShipmentStageDialog(QDialog):
    """
    出货阶段对话框
    
    功能：
    - 添加/编辑出货阶段
    - 配置阶段名称、日期、柜号、提单号、数量等
    
    构造参数：
    - parent: QWidget, 父窗口
    - stage_no: int, 阶段序号（从0开始）
    - stage_data: dict, 阶段数据（编辑模式），None 表示新建模式
    """
    
    def __init__(self, parent, stage_no, stage_data=None):
        super().__init__(parent)
        self.stage_no = stage_no
        self.stage_data = stage_data or {}
        self.is_edit = stage_data is not None
        self.init_ui()
        if self.is_edit:
            self.load_stage_data()

    def init_ui(self):
        """初始化UI"""
        from PySide6.QtCore import QDate
        title = "编辑出货阶段" if self.is_edit else f"添加出货阶段 #{self.stage_no + 1}"
        self.setWindowTitle(title)
        self.setFixedSize(500, 450)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.stage_name_input = QLineEdit()
        self.stage_name_input.setFixedHeight(35)
        self.stage_name_input.setText(f"出货{self.stage_no + 1}")
        form_layout.addRow("阶段名称:", self.stage_name_input)

        self.shipment_date_input = QDateEdit()
        self.shipment_date_input.setCalendarPopup(True)
        self.shipment_date_input.setFixedHeight(35)
        self.shipment_date_input.setDate(QDate.currentDate())
        form_layout.addRow("出货日期:", self.shipment_date_input)

        self.container_no_input = QLineEdit()
        self.container_no_input.setFixedHeight(35)
        self.container_no_input.setPlaceholderText("如: MSKU1234567")
        form_layout.addRow("柜号:", self.container_no_input)

        self.bl_no_input = QLineEdit()
        self.bl_no_input.setFixedHeight(35)
        self.bl_no_input.setPlaceholderText("如: BL123456789")
        form_layout.addRow("提单号:", self.bl_no_input)

        self.quantity_input = QLineEdit()
        self.quantity_input.setFixedHeight(35)
        self.quantity_input.setPlaceholderText("出货数量")
        form_layout.addRow("数量:", self.quantity_input)

        self.storage_location_input = QLineEdit()
        self.storage_location_input.setFixedHeight(35)
        self.storage_location_input.setPlaceholderText("如: 上海港")
        form_layout.addRow("存放位置:", self.storage_location_input)

        self.ci_document_input = QLineEdit()
        self.ci_document_input.setFixedHeight(35)
        self.ci_document_input.setPlaceholderText("CI文件路径或编号")
        form_layout.addRow("CI文件:", self.ci_document_input)

        self.pl_document_input = QLineEdit()
        self.pl_document_input.setFixedHeight(35)
        self.pl_document_input.setPlaceholderText("PL文件路径或编号")
        form_layout.addRow("PL文件:", self.pl_document_input)

        self.remark_input = QLineEdit()
        self.remark_input.setFixedHeight(35)
        form_layout.addRow("备注:", self.remark_input)

        layout.addLayout(form_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        save_btn = QPushButton("确定")
        save_btn.clicked.connect(self.validate_and_accept)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        buttons_layout.addWidget(save_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def load_stage_data(self):
        """加载阶段数据（编辑模式）"""
        from PySide6.QtCore import QDate
        self.stage_name_input.setText(self.stage_data.get('stage_name', ''))
        if self.stage_data.get('shipment_date'):
            date = QDate.fromString(str(self.stage_data['shipment_date'])[:10], "yyyy-MM-dd")
            if date.isValid():
                self.shipment_date_input.setDate(date)
        self.container_no_input.setText(self.stage_data.get('container_no', ''))
        self.bl_no_input.setText(self.stage_data.get('bl_no', ''))
        self.quantity_input.setText(str(self.stage_data.get('quantity', '')))
        self.storage_location_input.setText(self.stage_data.get('storage_location', ''))
        self.ci_document_input.setText(self.stage_data.get('ci_document', ''))
        self.pl_document_input.setText(self.stage_data.get('pl_document', ''))
        self.remark_input.setText(self.stage_data.get('remark', ''))

    def validate_and_accept(self):
        """验证并确认"""
        if not self.stage_name_input.text().strip():
            QMessageBox.warning(self, "警告", "请输入阶段名称")
            return
        try:
            qty = float(self.quantity_input.text() or 0)
            if qty <= 0:
                QMessageBox.warning(self, "警告", "数量必须大于0")
                return
        except ValueError:
            QMessageBox.warning(self, "警告", "数量必须是数字")
            return
        self.accept()

    def get_stage_data(self):
        """获取阶段数据"""
        return {
            'id': self.stage_data.get('id') if self.is_edit else None,
            'stage_name': self.stage_name_input.text().strip(),
            'shipment_date': self.shipment_date_input.date().toString("yyyy-MM-dd"),
            'container_no': self.container_no_input.text().strip(),
            'bl_no': self.bl_no_input.text().strip(),
            'quantity': float(self.quantity_input.text() or 0),
            'storage_location': self.storage_location_input.text().strip(),
            'ci_document': self.ci_document_input.text().strip(),
            'pl_document': self.pl_document_input.text().strip(),
            'remark': self.remark_input.text().strip()
        }