from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTextEdit, QLabel, QListWidget, QListWidgetItem, 
    QMessageBox, QInputDialog, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class MemoDialog(QDialog):
    def __init__(self, api_client, entity_type, entity_id, field_name, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.field_name = field_name
        self.memos = []
        self.init_ui()
        self.load_memos()

    def init_ui(self):
        self.setWindowTitle(f"备忘录 - {self.field_name}")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout()

        title = QLabel(f"备忘录 - {self.field_name}")
        title.setFont(QFont("", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        self.memo_list = QListWidget()
        self.memo_list.itemDoubleClicked.connect(self.edit_memo)
        layout.addWidget(self.memo_list)

        input_layout = QHBoxLayout()
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("添加新记录...")
        self.input_field.setMaximumHeight(80)
        input_layout.addWidget(self.input_field)

        add_btn = QPushButton("添加")
        add_btn.setFixedWidth(80)
        add_btn.clicked.connect(self.add_memo)
        input_layout.addWidget(add_btn)
        layout.addLayout(input_layout)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def load_memos(self):
        try:
            self.memos = self.api_client.get_memos(self.entity_type, self.entity_id, self.field_name)
            self.refresh_list()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载失败: {e}")

    def refresh_list(self):
        self.memo_list.clear()
        for memo in self.memos:
            created_at = memo.get('created_at', '')[:19] if memo.get('created_at') else ''
            content = memo.get('content', '')
            item_text = f"[{created_at}] {content}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, memo.get('id'))
            self.memo_list.addItem(item)

    def add_memo(self):
        content = self.input_field.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "提示", "请输入内容")
            return
        try:
            self.api_client.create_memo({
                "entity_type": self.entity_type,
                "entity_id": self.entity_id,
                "field_name": self.field_name,
                "content": content
            })
            self.input_field.clear()
            self.load_memos()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"添加失败: {e}")

    def edit_memo(self, item):
        memo_id = item.data(Qt.UserRole)
        if not memo_id:
            return

        memo = next((m for m in self.memos if m.get('id') == memo_id), None)
        default_text = memo.get('content', '') if memo else ''

        new_content, ok = QInputDialog.getText(
            self, "编辑", "修改内容:",
            QLineEdit.Normal,
            default_text
        )
        if ok and new_content:
            try:
                self.api_client.update_memo(memo_id, {"content": new_content})
                self.load_memos()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"修改失败: {e}")
