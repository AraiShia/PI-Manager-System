# -*- coding: utf-8 -*-
"""
水单查看器弹窗

用途：查看某个 PI 的所有水单（收款凭证）图片
调用方式：
    from widgets.payment import WaterBillViewer
    
    viewer = WaterBillViewer(parent, pi_no="PISME902606110", payments=[...])
    viewer.exec_()

数据结构示例:
    payments = [
        {
            'receipt_no': 'R001',
            'payment_date': datetime(2026, 6, 10),
            'actual_amount': 3000.00,
            'water_image': 'base64_encoded_string...'
        },
        ...
    ]
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QWidget
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QFont, QColor
import base64
import logging

logger = logging.getLogger(__name__)


class WaterBillViewer(QDialog):
    """
    水单图片查看器弹窗
    
    功能:
    - 左侧列表显示水单编号、日期、金额
    - 右侧预览区显示水单图片（base64 解码）
    - 支持点击切换查看不同水单
    
    信号: 无
    """

    def __init__(self, parent, pi_no: str, payments: list):
        """
        初始化水单查看器
        
        Args:
            parent: 父窗口
            pi_no: PI 号码 (用于标题显示)
            payments: 水单列表，每项包含:
                - receipt_no: str - 水单编号
                - payment_date: datetime - 付款日期
                - actual_amount: float - 实际到账金额
                - water_image: str or None - base64 编码的图片
        """
        super().__init__(parent)
        self.pi_no = pi_no
        self.payments = payments or []
        
        self.setWindowTitle(f"水单查看 - {pi_no}")
        self.setMinimumSize(800, 600)
        self.resize(900, 650)
        
        self._setup_ui()
        self._load_payments()

    def _setup_ui(self):
        """设置 UI 布局"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # ===== 左侧：水单列表 =====
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        list_title = QLabel("📋 水单列表")
        list_title.setFont(QFont("", 11, QFont.Weight.Bold))
        left_layout.addWidget(list_title)

        self.payment_list = QListWidget()
        self.payment_list.setMaximumWidth(320)
        self.payment_list.setMinimumWidth(280)
        self.payment_list.currentRowChanged.connect(self._on_item_changed)
        # 设置列表项高度
        self.payment_list.setIconSize(QSize(24, 24))
        left_layout.addWidget(self.payment_list)

        # 列表底部提示
        list_hint = QLabel(f"共 {len(self.payments)} 张水单")
        list_hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        list_hint.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(list_hint)

        main_layout.addWidget(left_panel, stretch=1)

        # ===== 右侧：图片预览区 =====
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        preview_title = QLabel("🖼️ 图片预览")
        preview_title.setFont(QFont("", 11, QFont.Weight.Bold))
        right_layout.addWidget(preview_title)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(400)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #f9fafb;
                border: 2px dashed #d1d5db;
                border-radius: 8px;
                color: #9ca3af;
                font-size: 14px;
            }
        """)
        self.preview_label.setText("点击左侧水单项查看图片")
        self.preview_label.setWordWrap(True)
        right_layout.addWidget(self.preview_label, stretch=1)

        # 关闭按钮行
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(100)
        close_btn.setFixedHeight(32)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        right_layout.addLayout(btn_layout)

        main_layout.addWidget(right_panel, stretch=2)

    def _load_payments(self):
        """加载水单列表"""
        for idx, p in enumerate(self.payments):
            receipt_no = p.get('receipt_no', f'未知#{idx+1}')
            
            # 格式化日期
            payment_date = p.get('payment_date')
            if payment_date:
                try:
                    date_str = str(payment_date)[:10]
                except Exception:
                    date_str = '-'
            else:
                date_str = '-'
            
            # 格式化金额
            amount = p.get('actual_amount', 0) or 0
            
            # 构建列表项文本
            item_text = f"{receipt_no}"
            sub_text = f"  {date_str}  |  ${amount:.2f}"
            
            item = QListWidgetItem(item_text)
            item.setToolTip(f"水单号: {receipt_no}\n日期: {date_str}\n金额: ${amount:.2f}")
            item.setData(Qt.UserRole, p)  # 存储完整数据
            
            # 检查是否有图片
            has_image = bool(p.get('water_image'))
            if not has_image:
                item.setForeground(QColor("#9ca3af"))  # 灰色表示无图片
            
            self.payment_list.addItem(item)
        
        # 如果有数据，默认选中第一项
        if self.payments:
            self.payment_list.setCurrentRow(0)
        else:
            self.preview_label.setText("该 PI 暂无水单记录")

    def _on_item_changed(self, current_row: int):
        """
        列表项切换事件处理
        
        Args:
            current_row: 当前选中的行索引 (从 0 开始)
        """
        if current_row < 0 or current_row >= len(self.payments):
            return

        payment = self.payments[current_row]
        water_image = payment.get('water_image')

        if not water_image:
            self._show_no_image_state(
                f"该水单无图片\n\n"
                f"水单号: {payment.get('receipt_no', '未知')}\n"
                f"日期: {str(payment.get('payment_date', ''))[:10]}\n"
                f"金额: ${payment.get('actual_amount', 0):.2f}"
            )
            return

        try:
            # 解码 base64 图片
            image_data = base64.b64decode(water_image)
            
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)

            if pixmap.isNull():
                self._show_error_state("图片格式错误或数据损坏")
                return

            # 缩放显示（保持比例，适配预览区）
            preview_size = self.preview_label.size() - QSize(20, 20)
            scaled_pixmap = pixmap.scaled(
                preview_size.width(),
                preview_size.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled_pixmap)
            self.preview_label.setStyleSheet("""
                QLabel {
                    background-color: #ffffff;
                    border: 1px solid #e5e7eb;
                    border-radius: 4px;
                }
            """)
            
            logger.debug(f"[WaterBillViewer] 成功加载水单图片: row={current_row}")
            
        except base64.binascii.Error as e:
            logger.error(f"[WaterBillViewer] Base64 解码失败: {e}")
            self._show_error_state(f"Base64 解码错误\n\n{e}")
        except Exception as e:
            logger.error(f"[WaterBillViewer] 图片加载异常: {e}", exc_info=True)
            self._show_error_state(f"图片加载失败\n\n{e}")

    def _show_no_image_state(self, message: str):
        """显示无图片状态"""
        self.preview_label.setPixmap(None)
        self.preview_label.setText(message)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #fef3c7;
                border: 2px dashed #f59e0b;
                border-radius: 8px;
                color: #92400e;
                font-size: 13px;
                padding: 20px;
            }
        """)
        self.preview_label.setAlignment(Qt.AlignCenter)

    def _show_error_state(self, message: str):
        """显示错误状态"""
        self.preview_label.setPixmap(None)
        self.preview_label.setText(message)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #fee2e2;
                border: 2px solid #ef4444;
                border-radius: 8px;
                color: #dc2626;
                font-size: 13px;
                padding: 20px;
            }
        """)
        self.preview_label.setAlignment(Qt.AlignCenter)

    def keyPressEvent(self, event):
        """
        键盘事件重写
        
        支持:
        - ESC: 关闭弹窗
        - 上/下箭头: 切换水单项
        """
        if event.key() == Qt.Key_Escape:
            self.accept()
        elif event.key() == Qt.Key_Up:
            current = self.payment_list.currentRow()
            if current > 0:
                self.payment_list.setCurrentRow(current - 1)
        elif event.key() == Qt.Key_Down:
            current = self.payment_list.currentRow()
            if current < self.payment_list.count() - 1:
                self.payment_list.setCurrentRow(current + 1)
        else:
            super().keyPressEvent(event)
