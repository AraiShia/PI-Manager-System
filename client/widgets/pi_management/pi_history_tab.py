# 2026-06-12 需求#42：PI History Tab - 双模式（列表浏览 / 历史浏览）
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QHeaderView,
    QMessageBox, QGroupBox, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class PiHistoryTab(QWidget):
    """PI History Tab - 双模式（列表浏览 / PI 历史浏览）"""

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self._current_pi_id = None
        self._mode = "list"  # "list" | "detail"
        self._layout = QVBoxLayout(self)
        self._setup_ui()

    def _setup_ui(self):
        # 模式一：PI 列表
        self._list_group = QGroupBox("PI 列表")
        list_layout = QVBoxLayout()
        self._pi_table = QTableWidget()
        self._pi_table.setColumnCount(3)
        self._pi_table.setHorizontalHeaderLabels(["PI 编号", "客户", "日期"])
        self._pi_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._pi_table.cellDoubleClicked.connect(self._on_pi_double_clicked)
        list_layout.addWidget(self._pi_table)
        self._list_group.setLayout(list_layout)
        self._layout.addWidget(self._list_group)

        # 模式二：历史浏览（初始隐藏）
        self._detail_group = QGroupBox("PI 历史浏览")
        detail_layout = QHBoxLayout()

        # 左侧版本列表
        left_layout = QVBoxLayout()
        self._version_table = QTableWidget()
        self._version_table.setColumnCount(3)
        self._version_table.setHorizontalHeaderLabels(["版本", "时间", "变更说明"])
        self._version_table.setMaximumWidth(300)
        self._version_table.setAlternatingRowColors(True)
        self._version_table.cellClicked.connect(self._on_version_clicked)
        left_layout.addWidget(QLabel("历史版本"))
        left_layout.addWidget(self._version_table)
        detail_layout.addLayout(left_layout, 1)

        # 右侧详情表格
        right_layout = QVBoxLayout()
        self._detail_table = QTableWidget()
        self._detail_table.setAlternatingRowColors(True)
        right_layout.addWidget(QLabel("详情（只读）"))
        right_layout.addWidget(self._detail_table)
        detail_layout.addLayout(right_layout, 2)

        # 返回按钮
        self._back_btn = QPushButton("← 返回列表")
        self._back_btn.clicked.connect(self._switch_to_list_mode)
        left_layout.addWidget(self._back_btn)

        self._detail_group.setLayout(detail_layout)
        self._layout.addWidget(self._detail_group)
        self._detail_group.hide()

        self._load_pi_list()

    def _load_pi_list(self):
        """加载 PI 列表"""
        try:
            pis = self.api_client.get_pi_orders() or []
            self._pi_table.setRowCount(len(pis))
            for i, pi in enumerate(pis):
                self._pi_table.setItem(i, 0, QTableWidgetItem(pi.get("pi_no", "")))
                self._pi_table.setItem(i, 1, QTableWidgetItem(pi.get("customer_name", "")))
                created_at = pi.get("created_at", "")
                self._pi_table.setItem(i, 2, QTableWidgetItem(created_at[:10] if created_at else ""))
                self._pi_table.setRowHeight(i, 28)
        except Exception as e:
            print(f"[PiHistoryTab] 加载 PI 列表失败: {e}")

    def _on_pi_double_clicked(self, row: int, col: int):
        """进入模式二"""
        pi_no_item = self._pi_table.item(row, 0)
        if not pi_no_item:
            return
        pi_no = pi_no_item.text()
        pis = self.api_client.get_pi_orders() or []
        pi = next((p for p in pis if p.get("pi_no") == pi_no), None)
        if not pi:
            return
        self._current_pi_id = pi.get("id")
        self._switch_to_detail_mode(pi)

    def _switch_to_detail_mode(self, pi: dict):
        """切换到模式二"""
        self._mode = "detail"
        self._list_group.hide()
        self._detail_group.show()
        self._detail_group.setTitle(f"PI 历史浏览 ← {pi.get('pi_no', '')}")
        self._load_versions()

    def _switch_to_list_mode(self):
        """切换到模式一"""
        self._mode = "list"
        self._current_pi_id = None
        self._detail_group.hide()
        self._list_group.show()
        self._detail_table.clear()
        self._version_table.setRowCount(0)

    def _load_versions(self):
        """加载当前 PI 的所有版本"""
        if not self._current_pi_id:
            return
        try:
            versions = self.api_client.get_pi_versions(self._current_pi_id) or []

            has_formal = False
            if self._current_pi_id:
                has_formal = self.api_client.formal_record_exists(self._current_pi_id)

            row_count = len(versions) + (1 if has_formal else 0)
            self._version_table.setRowCount(row_count)
            row = 0

            if has_formal:
                item = QTableWidgetItem("★ 正式纪录")
                item.setData(Qt.UserRole, {"type": "formal"})
                self._version_table.setItem(row, 0, item)
                self._version_table.setItem(row, 1, QTableWidgetItem("—"))
                self._version_table.setItem(row, 2, QTableWidgetItem("[查看]"))
                row += 1

            for v in versions:
                self._version_table.setItem(row, 0, QTableWidgetItem(f"v{v['version_no']}"))
                created_at = v["created_at"] if v.get("created_at") else ""
                self._version_table.setItem(row, 1, QTableWidgetItem(created_at[:16]))
                self._version_table.setItem(row, 2, QTableWidgetItem(v.get("change_desc", "") or ""))
                self._version_table.item(row, 0).setData(Qt.UserRole, {"type": "version", "id": v["id"]})
                row += 1

            self._version_table.resizeColumnsToContents()
        except Exception as e:
            print(f"[PiHistoryTab] 加载版本失败: {e}")

    def _on_version_clicked(self, row: int, col: int):
        """点击版本，加载详情"""
        item = self._version_table.item(row, 0)
        if not item:
            return
        data = item.data(Qt.UserRole)
        try:
            if data.get("type") == "formal":
                detail = self.api_client.get_formal_record(self._current_pi_id)
            else:
                versions = self.api_client.get_pi_versions(self._current_pi_id) or []
                version_id = data.get("id")
                v = next((x for x in versions if x["id"] == version_id), None)
                if not v:
                    return
                detail = self.api_client.get_pi_detail(self._current_pi_id)
            self._show_detail(detail)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载详情失败: {e}")

    def _show_detail(self, data: dict):
        """在右侧表格显示只读详情"""
        items = data.get("items", [])
        self._detail_table.clear()
        self._detail_table.setColumnCount(7)
        self._detail_table.setHorizontalHeaderLabels(["序号", "OE号", "产品类型", "型号", "数量", "单价", "金额"])
        self._detail_table.setRowCount(len(items))
        for i, item in enumerate(items):
            self._detail_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self._detail_table.setItem(i, 1, QTableWidgetItem(item.get("oe_number", "")))
            self._detail_table.setItem(i, 2, QTableWidgetItem(item.get("customer_code", "")))
            self._detail_table.setItem(i, 3, QTableWidgetItem(item.get("detail_desc", "")))
            self._detail_table.setItem(i, 4, QTableWidgetItem(str(item.get("quantity", ""))))
            self._detail_table.setItem(i, 5, QTableWidgetItem(str(item.get("unit_price", ""))))
            self._detail_table.setItem(i, 6, QTableWidgetItem(str(item.get("total_price", ""))))

            for col in range(7):
                cell = self._detail_table.item(i, col)
                cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)

            self._detail_table.setRowHeight(i, 28)

        self._detail_table.resizeColumnsToContents()
