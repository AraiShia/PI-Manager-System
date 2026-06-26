# -*- coding: utf-8 -*-
"""
订单历史记录对话框

文件：client/widgets/order_history_dialog.py
用途：显示订单的所有历史版本

创建日期：2026-06-15
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QAbstractItemView,
    QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
import logging

logger = logging.getLogger(__name__)

# 表头
HISTORY_HEADERS = ["版本", "修改时间", "修改人", "描述"]
HISTORY_COLUMN_COUNT = len(HISTORY_HEADERS)

# 列宽
HISTORY_COLUMN_WIDTHS = [60, 150, 80, 200]


class OrderHistoryDialog(QDialog):
    """订单历史记录对话框"""
    
    # 查看详情信号
    view_version = Signal(dict)  # 传递版本数据
    
    def __init__(self, api_client, pi_id: int, pi_no: str, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.pi_id = pi_id
        self.pi_no = pi_no
        self._versions = []
        
        self._init_ui()
        self._load_versions()
    
    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"历史记录 - {self.pi_no}")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 标题
        title_layout = QHBoxLayout()
        title_label = QLabel(f"订单: {self.pi_no}")
        title_label.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # 历史记录表格
        self.table = QTableWidget()
        self.table.setColumnCount(HISTORY_COLUMN_COUNT)
        self.table.setHorizontalHeaderLabels(HISTORY_HEADERS)
        
        # 设置列宽
        header = self.table.horizontalHeader()
        for i, width in enumerate(HISTORY_COLUMN_WIDTHS):
            self.table.setColumnWidth(i, width)
        header.setStretchLastSection(True)
        
        # 表格属性
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(32)
        
        # 信号连接
        self.table.cellDoubleClicked.connect(self._on_double_click)
        
        layout.addWidget(self.table)
        
        # 状态标签
        self.status_label = QLabel("加载中...")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.status_label)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.view_btn = QPushButton("查看详情")
        self.view_btn.clicked.connect(self._on_view_click)
        btn_layout.addWidget(self.view_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_versions(self):
        """加载历史版本"""
        try:
            import logging
            logger2 = logging.getLogger(__name__)
            
            url = f"/pi/{self.pi_id}/versions"
            logger2.info(f"[历史记录] 加载版本 URL: {url}")
            
            versions = self.api_client.get(url)
            logger2.info(f"[历史记录] API返回类型: {type(versions)}, 数据: {versions}")
            
            if isinstance(versions, dict):
                versions = versions.get('items', [])
            
            self._versions = versions if isinstance(versions, list) else []
            self._populate_table()
            
            if self._versions:
                self.status_label.setText(f"共 {len(self._versions)} 个版本")
            else:
                self.status_label.setText("暂无历史记录")
                
        except Exception as e:
            logger.error(f"加载历史版本失败: {e}")
            self.status_label.setText("加载失败")
            QMessageBox.warning(self, "错误", f"加载历史版本失败:\n{str(e)}")
    
    def _populate_table(self):
        """填充表格"""
        self.table.setRowCount(len(self._versions))
        
        for row, version in enumerate(self._versions):
            # 版本号
            version_no = version.get('version_no', 0)
            self.table.setItem(row, 0, QTableWidgetItem(f"v{version_no}"))
            
            # 修改时间
            created_at = version.get('created_at', '')
            if created_at:
                # 格式化为 YYYY-MM-DD HH:MM
                if 'T' in created_at:
                    created_at = created_at.split('T')[0] + ' ' + created_at.split('T')[1][:5]
            self.table.setItem(row, 1, QTableWidgetItem(created_at))
            
            # 修改人
            created_by = version.get('created_by', 'Admin')
            self.table.setItem(row, 2, QTableWidgetItem(str(created_by)))
            
            # 描述
            change_desc = version.get('change_desc', '')
            self.table.setItem(row, 3, QTableWidgetItem(change_desc or '-'))
    
    def _on_double_click(self, row: int, column: int):
        """双击查看详情"""
        self._view_selected_version()
    
    def _on_view_click(self):
        """查看详情按钮"""
        self._view_selected_version()
    
    def _view_selected_version(self):
        """查看选中的版本"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择要查看的版本")
            return
        
        version = self._versions[current_row]
        self.view_version.emit(version)