from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
    QMessageBox, QFileDialog, QGroupBox, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class FileUploadDialog(QDialog):
    FILE_TYPE_LABELS = {
        "contract": "合同文件",
        "invoice": "发票文件",
        "customs": "报关单"
    }

    def __init__(self, api_client, pi_id, pi_no, file_type=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.pi_id = pi_id
        self.pi_no = pi_no
        self.file_type = file_type
        self.files = []
        self.init_ui()
        self.load_files()

    def init_ui(self):
        title = self.FILE_TYPE_LABELS.get(self.file_type, "文件管理")
        self.setWindowTitle(f"{title} - {self.pi_no}")
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout()

        header = QLabel(f"当前订单: {self.pi_no}")
        header.setFont(QFont("", 10))
        layout.addWidget(header)

        self.tabs = {}
        if not self.file_type:
            for ftype, label in self.FILE_TYPE_LABELS.items():
                group = QGroupBox(label)
                group_layout = QVBoxLayout()
                table = QTableWidget()
                table.setColumnCount(4)
                table.setHorizontalHeaderLabels(["文件名", "上传时间", "大小", "操作"])
                table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                table.verticalHeader().setVisible(False)
                group_layout.addWidget(table)
                group.setLayout(group_layout)
                layout.addWidget(group)
                self.tabs[ftype] = table
        else:
            self.current_group = QGroupBox(title)
            group_layout = QVBoxLayout()
            self.current_table = QTableWidget()
            self.current_table.setColumnCount(4)
            self.current_table.setHorizontalHeaderLabels(["文件名", "上传时间", "大小", "操作"])
            self.current_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.current_table.verticalHeader().setVisible(False)
            group_layout.addWidget(self.current_table)
            self.current_group.setLayout(group_layout)
            layout.addWidget(self.current_group)

        btn_layout = QHBoxLayout()
        if self.file_type:
            upload_btn = QPushButton("上传文件")
            upload_btn.clicked.connect(self.upload_file)
            btn_layout.addWidget(upload_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def load_files(self):
        try:
            if self.file_type:
                self.files = self.api_client.get_order_files(self.pi_id, self.file_type)
                self.populate_table(self.current_table, self.files)
            else:
                for ftype, table in self.tabs.items():
                    files = self.api_client.get_order_files(self.pi_id, ftype)
                    self.populate_table(table, files)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载文件失败: {e}")

    def populate_table(self, table, files):
        table.setRowCount(len(files))
        for i, f in enumerate(files):
            table.setItem(i, 0, QTableWidgetItem(f.get('original_name', '')))
            uploaded_at = f.get('uploaded_at', '')
            if uploaded_at:
                uploaded_at = str(uploaded_at)[:19]
            table.setItem(i, 1, QTableWidgetItem(uploaded_at))
            size = f.get('file_size', 0)
            table.setItem(i, 2, QTableWidgetItem(self._format_size(size)))

            widget = QWidget()
            btn_layout = QHBoxLayout(widget)
            btn_layout.setContentsMargins(0, 0, 0, 0)

            download_btn = QPushButton("下载")
            download_btn.setFixedWidth(60)
            download_btn.clicked.connect(lambda checked, fid=f['id']: self.download_file(fid))
            delete_btn = QPushButton("删除")
            delete_btn.setFixedWidth(60)
            delete_btn.clicked.connect(lambda checked, fid=f['id']: self.delete_file(fid))

            btn_layout.addWidget(download_btn)
            btn_layout.addWidget(delete_btn)
            table.setCellWidget(i, 3, widget)

    def _format_size(self, size):
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f}KB"
        else:
            return f"{size / (1024 * 1024):.1f}MB"

    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择文件",
            "",
            "支持的文件 (*.pdf *.doc *.docx *.jpg *.jpeg *.png *.xls *.xlsx);;所有文件 (*.*)"
        )
        if not file_path:
            return

        try:
            self.api_client.upload_order_file(self.pi_id, self.file_type, file_path)
            QMessageBox.information(self, "成功", "文件上传成功")
            self.load_files()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"上传失败: {e}")

    def download_file(self, file_id):
        try:
            save_path, _ = QFileDialog.getSaveFileName(self, "保存文件", "", "所有文件 (*.*)")
            if save_path:
                self.api_client.download_order_file(file_id, save_path)
                QMessageBox.information(self, "成功", f"文件已保存到: {save_path}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"下载失败: {e}")

    def delete_file(self, file_id):
        reply = QMessageBox.question(
            self, "确认删除", "确定删除这个文件吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.api_client.delete_order_file(file_id)
                self.load_files()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败: {e}")