"""
客户需求备注编辑对话框
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QTextEdit, QPushButton, QDialogButtonBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class CustomerRequirementDialog(QDialog):
    """客户需求备注编辑对话框"""
    
    saved = Signal(str)
    
    def __init__(self, current_value: str = "", pi_no: str = "", parent=None):
        super().__init__(parent)
        self.current_value = current_value
        self.pi_no = pi_no
        self.setWindowTitle(f"编辑客户需求备注 - {pi_no}" if pi_no else "编辑客户需求备注")
        self.setMinimumSize(500, 350)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 提示
        hint = QLabel("请输入客户需求备注信息：")
        hint.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(hint)
        
        # 文本编辑器
        self.text_edit = QTextEdit(self.current_value)
        self.text_edit.setPlaceholderText("输入客户需求备注...")
        self.text_edit.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(self.text_edit)
        
        # 按钮
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
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #4b5563; }
        """)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._on_save)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_save(self):
        text = self.text_edit.toPlainText().strip()
        if text:
            self.saved.emit(text)
        self.accept()


class CustomerModelDialog(QDialog):
    """客户型号编辑对话框"""
    
    saved = Signal(str)
    
    def __init__(self, current_value: str = "", pi_no: str = "", parent=None):
        super().__init__(parent)
        self.current_value = current_value
        self.pi_no = pi_no
        self.setWindowTitle(f"编辑客户型号 - {pi_no}" if pi_no else "编辑客户型号")
        self.setMinimumSize(400, 200)
        self._setup_ui()
    
    def _setup_ui(self):
        from PySide6.QtWidgets import QLineEdit
        
        layout = QVBoxLayout(self)
        
        hint = QLabel("请输入客户型号：")
        hint.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(hint)
        
        self.line_edit = QLineEdit(self.current_value)
        self.line_edit.setPlaceholderText("输入客户型号...")
        self.line_edit.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(self.line_edit)
        
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
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #4b5563; }
        """)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._on_save)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_save(self):
        text = self.line_edit.text().strip()
        self.saved.emit(text)
        self.accept()


class CustomerReplyDialog(QDialog):
    """客户最新回复编辑对话框 - 使用客户回复API"""
    
    saved = Signal(dict)  # 发送回复数据
    
    def __init__(self, pi_id: int, pi_no: str, api_client, current_reply: str = "", parent=None):
        super().__init__(parent)
        self.pi_id = pi_id
        self.pi_no = pi_no
        self.api_client = api_client
        self.current_reply = current_reply
        self.all_replies = []  # 存储该PI的所有回复
        self.setWindowTitle(f"客户回复历史 - {pi_no}")
        self.setMinimumSize(600, 500)
        self._setup_ui()
        self._load_replies()
    
    def _setup_ui(self):
        from PySide6.QtWidgets import QScrollArea, QWidget, QFormLayout, QDateEdit, QListWidget
        
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel(f"PI单号: {self.pi_no}")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1f2937;")
        layout.addWidget(title)
        
        # 回复历史列表
        history_label = QLabel("回复历史：")
        history_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(history_label)
        
        self.reply_list = QListWidget()
        self.reply_list.itemClicked.connect(self._on_reply_selected)
        layout.addWidget(self.reply_list)
        
        # 新增回复区域
        add_label = QLabel("添加新回复：")
        add_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(add_label)
        
        # 回复日期
        from PySide6.QtCore import QDate
        self.reply_date_edit = QDateEdit()
        self.reply_date_edit.setDate(QDate.currentDate())
        self.reply_date_edit.setCalendarPopup(True)
        
        # 回复内容
        self.reply_content_edit = QTextEdit()
        self.reply_content_edit.setPlaceholderText("输入客户回复内容...")
        self.reply_content_edit.setMaximumHeight(100)
        
        # 按钮
        btn_layout = QHBoxLayout()
        save_reply_btn = QPushButton("保存回复")
        save_reply_btn.clicked.connect(self._save_reply)
        save_reply_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        btn_layout.addWidget(save_reply_btn)
        btn_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #4b5563; }
        """)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_replies(self):
        """加载该PI的所有回复"""
        try:
            replies = self.api_client.get_customer_replies_by_pi(self.pi_id) or []
            self.all_replies = replies
            self.reply_list.clear()
            
            for reply in replies:
                date_str = reply.get('reply_date', '')
                content = reply.get('reply_content', '')[:50]
                self.reply_list.addItem(f"[{date_str}] {content}...")
        except Exception as e:
            print(f"加载回复历史失败: {e}")
    
    def _on_reply_selected(self, item):
        """选中某条回复时显示详情"""
        index = self.reply_list.row(item)
        if 0 <= index < len(self.all_replies):
            reply = self.all_replies[index]
            # 可以在这里显示更多详情
            pass
    
    def _save_reply(self):
        """保存新回复"""
        try:
            from datetime import date
            reply_date = self.reply_date_edit.date().toString("yyyy-MM-dd")
            reply_content = self.reply_content_edit.toPlainText().strip()
            
            if not reply_content:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "提示", "请输入回复内容")
                return
            
            # 获取customer_id（从PI数据中获取，这里暂时用1）
            # 实际应该从PI详情获取
            pi_detail = self.api_client.get_pi_detail(self.pi_id)
            customer_id = pi_detail.get('customer_id', 1)
            
            data = {
                "pi_id": self.pi_id,
                "customer_id": customer_id,
                "reply_date": reply_date,
                "reply_content": reply_content
            }
            
            result = self.api_client.create_customer_reply(data)
            print(f"回复已保存: {result}")
            
            # 刷新列表
            self._load_replies()
            self.reply_content_edit.clear()
            
            # 发送保存信号
            self.saved.emit(result)
            
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "成功", "回复已保存")
            
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", f"保存失败: {e}")
            print(f"保存回复失败: {e}")