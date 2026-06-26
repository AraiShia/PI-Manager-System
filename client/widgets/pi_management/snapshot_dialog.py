# 2026-06-12 需求#42：保存快照对话框
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QHBoxLayout


class SnapshotDialog(QDialog):
    """保存快照对话框 - 输入变更说明"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("保存快照")
        self.setMinimumWidth(400)
        layout = QFormLayout(self)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("简要说明本次变更（可选）")
        layout.addRow("变更说明:", self.desc_input)

        btns = QHBoxLayout()
        ok = QPushButton("保存")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addRow("", btns)

        self.setLayout(layout)

    def get_change_desc(self) -> str:
        return self.desc_input.text().strip()
