"""
导出客户回复记录对话框（支持多商品）
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QRadioButton, QListWidget, QListWidgetItem,
    QMessageBox, QAbstractItemView, QScrollArea, QWidget
)
from PySide6.QtCore import Qt


class ReplyExportDialog(QDialog):
    def __init__(self, items: list, api_client, parent=None):
        """
        多商品回复记录导出对话框

        Args:
            items: 已选商品列表，每项格式:
                   {
                       "pi_id": int,
                       "pi_item_id": int 或 None,
                       "product_name": str,
                       "pi_no": str,
                   }
            api_client: API 客户端实例
            parent: 父窗口
        """
        super().__init__(parent)
        self.items = items or []
        self.api_client = api_client
        self.replies = []
        self.setWindowTitle("导出客户回复记录")
        self.setMinimumSize(600, 500)
        self._setup_ui()
        self._load_replies()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)

        # ===== 信息区 =====
        info_layout = QFormLayout()
        info_layout.setSpacing(8)

        customer_name = "-"
        if self.items:
            first = self.items[0]
            customer_name = first.get('customer_name', '-')

        product_count = len(self.items)
        pi_nos = sorted(set(item.get('pi_no', '') for item in self.items))
        pi_str = ", ".join(pi_nos[:3])
        if len(pi_nos) > 3:
            pi_str += f"... (共{len(pi_nos)}个PI)"

        info_layout.addRow(QLabel("<b>客户：</b>"), QLabel(customer_name))
        info_layout.addRow(QLabel("<b>PI 单号：</b>"), QLabel(pi_str))
        info_layout.addRow(QLabel("<b>已选商品：</b>"), QLabel(f"{product_count} 个"))
        main_layout.addLayout(info_layout)

        # ===== 商品列表 =====
        product_label = QLabel("已选商品")
        product_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #374151;")
        main_layout.addWidget(product_label)

        scroll = QScrollArea()
        scroll.setMaximumHeight(130)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        product_container = QWidget()
        product_list_layout = QVBoxLayout(product_container)
        product_list_layout.setContentsMargins(4, 4, 4, 4)
        product_list_layout.setSpacing(2)

        for item in self.items:
            pname = item.get('product_name', '未知产品')
            pino = item.get('pi_no', '-')
            row = QLabel(f"  \u25cf {pname}  ({pino})")
            row.setStyleSheet("font-size: 12px; padding: 2px 0;")
            product_list_layout.addWidget(row)

        product_list_layout.addStretch()
        scroll.setWidget(product_container)
        main_layout.addWidget(scroll)

        # ===== 导出范围 =====
        scope_label = QLabel("导出范围")
        scope_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #374151;")
        main_layout.addWidget(scope_label)

        self.scope_all = QRadioButton("全部记录")
        self.scope_select = QRadioButton("选择性导出")
        self.scope_all.setChecked(True)
        main_layout.addWidget(self.scope_all)
        main_layout.addWidget(self.scope_select)

        # 回复记录列表（选择性模式）
        self.reply_list = QListWidget()
        self.reply_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.reply_list.setVisible(False)
        main_layout.addWidget(self.reply_list)

        # 范围切换联动
        self.scope_select.toggled.connect(lambda checked: self.reply_list.setVisible(checked))

        # ===== 底部按钮 =====
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

        export_btn = QPushButton("导出 Excel")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(export_btn)
        main_layout.addLayout(btn_layout)

    def _load_replies(self):
        """加载所选商品的回复记录"""
        try:
            data = self.api_client.batch_get_replies(self.items)
            self.replies = data.get('replies', []) if data else []

            for r in self.replies:
                pname = r.get('product_name', '')
                seq = r.get('sequence_label', '')
                submitter = r.get('submitter_name', '')
                rdate = r.get('reply_date', '')[:10]
                label = f"{seq} - {submitter} - {rdate}"
                if pname:
                    label += f" [{pname}]"

                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, r.get('id'))
                item.setSelected(True)
                self.reply_list.addItem(item)

            count_text = f"导出所有 {len(self.replies)} 条回复记录"
            self.scope_all.setText(count_text)

        except Exception as e:
            print(f"[ERROR] 加载回复记录失败: {e}")

    def _on_export(self):
        """执行导出"""
        selected_ids = None
        if self.scope_select.isChecked():
            selected_ids = [item.data(Qt.UserRole) for item in self.reply_list.selectedItems()]
            if not selected_ids:
                QMessageBox.warning(self, "提示", "请选择要导出的记录")
                return

        try:
            content = self.api_client.export_batch_replies(
                self.items,
                selected_ids=selected_ids
            )

            from PySide6.QtWidgets import QFileDialog
            default_name = "客户回复记录.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存 Excel", default_name, "Excel文件 (*.xlsx)"
            )
            if file_path:
                with open(file_path, 'wb') as f:
                    f.write(content)
                QMessageBox.information(self, "成功", "导出成功")
                self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导出失败: {e}")
