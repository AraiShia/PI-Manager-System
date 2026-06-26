# -*- coding: utf-8 -*-
"""
订单版本详情对话框

文件：client/widgets/order_version_detail_dialog.py
用途：显示某个历史版本的完整快照数据

创建日期：2026-06-15
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QAbstractItemView,
    QLabel, QGroupBox, QScrollArea, QWidget, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import logging

logger = logging.getLogger(__name__)

# 产品表头
ITEM_HEADERS = ["序号", "产品名称", "型号", "OE号", "数量", "单价", "金额", "备注"]

# 付款表头
PAYMENT_HEADERS = ["序号", "阶段名称", "金额", "状态"]


class OrderVersionDetailDialog(QDialog):
    """订单版本详情对话框"""
    
    def __init__(self, api_client, pi_id: int, version: dict, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.pi_id = pi_id
        self.version = version  # 版本基本信息
        self._snapshot_data = None
        
        self._init_ui()
        self._load_snapshot()
    
    def _init_ui(self):
        """初始化UI"""
        version_no = self.version.get('version_no', 0)
        self.setWindowTitle(f"版本详情 - v{version_no}")
        self.setMinimumSize(900, 600)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 版本信息头部
        header_group = QGroupBox("版本信息")
        header_layout = QVBoxLayout(header_group)
        
        version_no = self.version.get('version_no', 0)
        created_at = self.version.get('created_at', '')
        change_desc = self.version.get('change_desc', '-')
        
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"版本号: v{version_no}"))
        info_layout.addWidget(QLabel(f"修改时间: {created_at}"))
        info_layout.addWidget(QLabel(f"描述: {change_desc}"))
        info_layout.addStretch()
        header_layout.addLayout(info_layout)
        
        layout.addWidget(header_group)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)
        
        # PI 基本信息
        pi_group = QGroupBox("订单基本信息")
        pi_layout = QVBoxLayout(pi_group)
        self.pi_info_label = QLabel("加载中...")
        pi_layout.addWidget(self.pi_info_label)
        scroll_layout.addWidget(pi_group)
        
        # 产品明细
        item_group = QGroupBox("订单产品")
        item_layout = QVBoxLayout(item_group)
        
        self.item_table = QTableWidget()
        self.item_table.setColumnCount(len(ITEM_HEADERS))
        self.item_table.setHorizontalHeaderLabels(ITEM_HEADERS)
        self.item_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.item_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.item_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.item_table.verticalHeader().setDefaultSectionSize(28)
        item_layout.addWidget(self.item_table)
        scroll_layout.addWidget(item_group)
        
        # 付款阶段
        payment_group = QGroupBox("付款阶段")
        payment_layout = QVBoxLayout(payment_group)
        
        self.payment_table = QTableWidget()
        self.payment_table.setColumnCount(len(PAYMENT_HEADERS))
        self.payment_table.setHorizontalHeaderLabels(PAYMENT_HEADERS)
        self.payment_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.payment_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.payment_table.verticalHeader().setDefaultSectionSize(28)
        payment_layout.addWidget(self.payment_table)
        scroll_layout.addWidget(payment_group)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_snapshot(self):
        """加载快照详情"""
        try:
            version_id = self.version.get('id')
            if not version_id:
                logger.error("版本ID不存在")
                return
            
            result = self.api_client.get(f"/pi/{self.pi_id}/versions/{version_id}/snapshot")
            
            if result:
                self._snapshot_data = result.get('snapshot', {})
                self._display_snapshot()
            else:
                QMessageBox.warning(self, "提示", "未找到版本快照数据")
                
        except Exception as e:
            logger.error(f"加载快照详情失败: {e}")
            QMessageBox.warning(self, "错误", f"加载快照详情失败:\n{str(e)}")
    
    def _display_snapshot(self):
        """显示快照数据"""
        if not self._snapshot_data:
            return
        
        # 显示 PI 基本信息
        pi_data = self._snapshot_data.get('pi', {})
        pi_info = f"PI号: {pi_data.get('pi_no', '-')} | 客户ID: {pi_data.get('customer_id', '-')} | 总金额: {pi_data.get('total_amount', 0):.2f} {pi_data.get('currency', 'USD')} | 状态: {pi_data.get('status', 1)}"
        self.pi_info_label.setText(pi_info)
        
        # 显示产品明细
        items = self._snapshot_data.get('items', [])
        self._populate_items_table(items)
        
        # 显示付款阶段
        payment_stages = self._snapshot_data.get('payment_stages', [])
        self._populate_payment_table(payment_stages)
    
    def _populate_items_table(self, items):
        """填充产品表格"""
        self.item_table.setRowCount(len(items))
        
        for row, item in enumerate(items):
            # 序号
            self.item_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            
            # 产品名称
            self.item_table.setItem(row, 1, QTableWidgetItem(item.get('detail_desc', '-')))
            
            # 型号
            self.item_table.setItem(row, 2, QTableWidgetItem(item.get('customer_code', '-')))
            
            # OE号
            self.item_table.setItem(row, 3, QTableWidgetItem(item.get('oe_number', '-')))
            
            # 数量
            quantity = item.get('quantity', 0)
            self.item_table.setItem(row, 4, QTableWidgetItem(f"{quantity:.2f}"))
            
            # 单价
            unit_price = item.get('unit_price', 0)
            self.item_table.setItem(row, 5, QTableWidgetItem(f"{unit_price:.2f}"))
            
            # 金额
            total_price = item.get('total_price', 0)
            self.item_table.setItem(row, 6, QTableWidgetItem(f"{total_price:.2f}"))
            
            # 备注
            self.item_table.setItem(row, 7, QTableWidgetItem(item.get('remark', '-')))
    
    def _populate_payment_table(self, payment_stages):
        """填充付款表格"""
        self.payment_table.setRowCount(len(payment_stages))
        
        if not payment_stages:
            self.payment_table.setItem(0, 0, QTableWidgetItem("(无付款记录)"))
            self.payment_table.setSpan(0, 0, 1, 4)
            return
        
        status_map = {1: "待付款", 2: "部分付款", 3: "已付款"}
        
        for row, stage in enumerate(payment_stages):
            # 序号
            self.payment_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            
            # 阶段名称
            self.payment_table.setItem(row, 1, QTableWidgetItem(stage.get('stage_name', '-')))
            
            # 金额
            amount = stage.get('amount', 0)
            self.payment_table.setItem(row, 2, QTableWidgetItem(f"{amount:.2f}"))
            
            # 状态
            status = stage.get('payment_status', 1)
            status_text = status_map.get(status, "未知")
            self.payment_table.setItem(row, 3, QTableWidgetItem(status_text))