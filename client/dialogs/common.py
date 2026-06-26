# -*- coding: utf-8 -*-
"""通用 Dialog"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit, QLineEdit, QHBoxLayout, QFileDialog, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QBrush, QColor
from PySide6.QtWidgets import QTableWidgetItem


class InvoiceUploadDialog(QDialog):
    """发票上传对话框"""
    def __init__(self, order, row, column, parent=None):
        super().__init__(parent)
        self.order = order
        self.row = row
        self.column = column
        self.main_window = parent
        self.setWindowTitle(f"发票上传 - {order.get('order_no', '')}")
        self.setMinimumWidth(500)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        info_label = QLabel(f"订单: {self.order.get('order_no', '')} | 客户: {self.order.get('customer_name', '')}")
        info_label.setStyleSheet("font-size: 14px; padding: 10px; background-color: #f3f4f6; border-radius: 4px;")
        layout.addWidget(info_label)
        
        current_status = self.order.get('invoice_status', '未上传')
        status_label = QLabel(f"当前状态: {current_status if current_status else '未上传'}")
        status_label.setStyleSheet("padding: 5px;")
        layout.addWidget(status_label)
        
        upload_btn = QPushButton("📤 选择发票文件")
        upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        upload_btn.clicked.connect(self._on_select_file)
        layout.addWidget(upload_btn)
        
        self.file_path_label = QLabel("未选择文件")
        self.file_path_label.setStyleSheet("color: #6b7280; padding: 5px;")
        self.file_path_label.setWordWrap(True)
        layout.addWidget(self.file_path_label)
        
        invoice_layout = QHBoxLayout()
        invoice_layout.addWidget(QLabel("发票号:"))
        self.invoice_no_input = QLineEdit()
        self.invoice_no_input.setPlaceholderText("请输入发票号")
        invoice_layout.addWidget(self.invoice_no_input)
        layout.addLayout(invoice_layout)
        
        layout.addWidget(QLabel("备注:"))
        self.invoice_remark = QTextEdit()
        self.invoice_remark.setPlaceholderText("发票备注信息（可选）")
        self.invoice_remark.setMaximumHeight(80)
        layout.addWidget(self.invoice_remark)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("💾 保存并上传")
        save_btn.setFixedWidth(120)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_select_file(self):
        """选择发票文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择发票文件",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.gif *.bmp);;PDF文件 (*.pdf);;所有文件 (*.*)"
        )
        if file_path:
            self.selected_file = file_path
            self.file_path_label.setText(f"已选择: {file_path}")
            self.file_path_label.setStyleSheet("color: #10b981; padding: 5px;")
    
    def _on_save(self):
        """保存发票信息"""
        invoice_no = self.invoice_no_input.text().strip()
        remark = self.invoice_remark.toPlainText().strip()
        
        self.order['invoice_status'] = '已上传'
        self.order['invoice_no'] = invoice_no
        self.order['invoice_remark'] = remark
        if hasattr(self, 'selected_file'):
            self.order['invoice_path'] = self.selected_file
        
        main_window = self.main_window
        item = QTableWidgetItem('已上传')
        item.setForeground(QBrush(QColor("#10b981")))
        main_window.order_detail_table.setItem(self.row, self.column, item)
        
        main_window._order_summary_filtered[main_window._selected_order_index] = self.order
        
        QMessageBox.information(self, "成功", "发票信息已保存，开票状态已更新为已上传")
        self.accept()


class FieldEditDialog(QDialog):
    """字段编辑对话框"""
    def __init__(self, field_name, current_value, parent=None):
        super().__init__(parent)
        self.field_name = field_name
        self.new_value = current_value
        self.setWindowTitle(f"编辑: {field_name}")
        self.setMinimumWidth(400)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        label = QLabel(f"字段: {self.field_name}")
        label.setFont(QFont("", 10, QFont.Weight.Bold))
        layout.addWidget(label)
        
        self.editor = QTextEdit()
        self.editor.setPlainText(str(self.new_value))
        self.editor.setMinimumHeight(100)
        layout.addWidget(self.editor)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(80)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_save(self):
        self.new_value = self.editor.toPlainText()
        self.accept()
    
    def get_value(self):
        return self.new_value