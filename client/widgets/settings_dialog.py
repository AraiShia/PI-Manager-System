# -*- coding: utf-8 -*-
"""
系统设置对话框（增强版 - B.11 双写同步策略）

文件：client/widgets/settings_dialog.py
更新日期：2026-06-18
来源：main.py L302-422（已迁移）
用途：设置系统全局参数（毛利率、汇率）+ 业务员基本信息

增强功能：
- API优先加载配置（数据库 → 本地文件 → 默认值，三级降级）
- 双写保存策略（同时写入数据库和本地文件）
- 扩展业务员基本信息字段（姓名/联系电话）
- 同步状态指示器（成功/降级/失败三种状态）

调用方式：
```python
from widgets import SettingsDialog

dialog = SettingsDialog(api_client, parent=self)
if dialog.exec():
    print("设置已保存并同步")
```

依赖：
- PySide6.QtWidgets: QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
                      QDoubleSpinBox, QLineEdit, QComboBox, QPushButton, QMessageBox
- PySide6.QtCore: Qt, QTimer
- config.local_settings_manager: load_local_settings, save_local_settings
- api.client.ApiClient: api_client 实例（用于API调用）
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QDoubleSpinBox, QLineEdit, QComboBox, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.client import ApiClient


class SettingsDialog(QDialog):
    """
    系统设置对话框（增强版）

    功能增强：
    - 自动从数据库回填最新配置（API优先）
    - 双写策略：同时保存到数据库和本地文件
    - 扩展业务员基本信息字段（姓名/联系电话）
- 支持离线降级模式（网络不可用时使用本地缓存）

    公式：预估美金报价 = 工厂人民币价格 × (1 + 毛利率) / 汇率

    构造参数：
    - api_client: ApiClient, API 客户端实例
    - parent: QWidget, 父窗口
    """

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.setWindowTitle("系统设置")
        self.setMinimumWidth(550)
        self.init_ui()
        # 异步加载设置（不阻塞UI）
        QTimer.singleShot(100, self.load_settings_async)

    def init_ui(self):
        """初始化UI（包含业务参数 + 操作员信息 + 同步状态）"""
        layout = QVBoxLayout(self)

        # ===== 区块1: 业务参数 =====
        profit_group = QGroupBox("业务参数")
        profit_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3b82f6;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                color: #2563eb;
            }
        """)
        profit_layout = QVBoxLayout()

        # 说明
        profit_info = QLabel(
            "毛利率用于自动计算产品报价基准价。\n"
            "公式: 预估美金报价 = 工厂人民币价格 × (1 + 毛利率) / 汇率"
        )
        profit_info.setStyleSheet("color: #64748b; font-size: 12px;")
        profit_layout.addWidget(profit_info)

        # 毛利率输入
        margin_input_layout = QHBoxLayout()
        margin_input_layout.addWidget(QLabel("基础毛利率(%):"))
        self.profit_margin_spin = QDoubleSpinBox()
        self.profit_margin_spin.setRange(0, 100)
        self.profit_margin_spin.setDecimals(2)
        self.profit_margin_spin.setSuffix(" %")
        self.profit_margin_spin.setFixedWidth(120)
        margin_input_layout.addWidget(self.profit_margin_spin)
        margin_input_layout.addStretch()
        profit_layout.addLayout(margin_input_layout)

        # 汇率输入
        rate_input_layout = QHBoxLayout()
        rate_input_layout.addWidget(QLabel("USD/RMB 汇率:"))
        self.exchange_rate_spin = QDoubleSpinBox()
        self.exchange_rate_spin.setRange(0.01, 100)
        self.exchange_rate_spin.setDecimals(4)
        self.exchange_rate_spin.setFixedWidth(120)
        rate_input_layout.addWidget(self.exchange_rate_spin)
        rate_input_layout.addStretch()
        profit_layout.addLayout(rate_input_layout)

        profit_group.setLayout(profit_layout)
        layout.addWidget(profit_group)

        # ===== 区块2: 业务员基本信息（新增）=====
        operator_group = QGroupBox("业务员基本信息")
        operator_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #22c55e;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                color: #16a34a;
            }
        """)
        operator_layout = QVBoxLayout()

        # 业务员姓名
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("业务员姓名:"))
        self.operator_name_edit = QLineEdit()
        self.operator_name_edit.setPlaceholderText("请输入姓名")
        self.operator_name_edit.setFixedWidth(200)
        name_layout.addWidget(self.operator_name_edit)
        name_layout.addStretch()
        operator_layout.addLayout(name_layout)

        # 联系电话
        phone_layout = QHBoxLayout()
        phone_layout.addWidget(QLabel("联系电话:"))
        self.operator_phone_edit = QLineEdit()
        self.operator_phone_edit.setPlaceholderText("如: 13800138000")
        self.operator_phone_edit.setFixedWidth(200)
        phone_layout.addWidget(self.operator_phone_edit)
        phone_layout.addStretch()
        operator_layout.addLayout(phone_layout)

        operator_group.setLayout(operator_layout)
        layout.addWidget(operator_group)

        # ===== 区块3: 同步状态指示器（新增）=====
        self.sync_status_label = QLabel("⏳ 正在加载配置...")
        self.sync_status_label.setStyleSheet("""
            QLabel {
                background: #fefce8;
                color: #854d0e;
                padding: 10px 16px;
                border-radius: 6px;
                border: 1px solid #fde047;
                font-weight: 500;
            }
        """)
        self.sync_status_label.setWordWrap(True)
        layout.addWidget(self.sync_status_label)

        # ===== 按钮 =====
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("💾 保存并同步")
        save_btn.setFixedWidth(120)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:pressed { background-color: #1e40af; }
        """)
        save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def load_settings_async(self):
        """
        异步加载设置（优先API，降级本地）

        加载策略（三级降级）：
        1. Priority: 从API获取最新配置（数据库）
        2. Fallback: 从本地JSON文件读取
        3. Default: 使用硬编码默认值
        """
        try:
            # 尝试从API获取（异步调用，避免阻塞UI）
            response = self.api_client.get("/api/settings/all")

            if response and response.status_code == 200:
                settings = response.json()

                # 回填业务参数
                self.profit_margin_spin.setValue(
                    float(settings.get('default_profit_margin', 25.0))
                )
                self.exchange_rate_spin.setValue(
                    float(settings.get('exchange_rate', 7.24))
                )

                # 回填业务员基本信息（新增）
                self.operator_name_edit.setText(
                    settings.get('operator_name', '')
                )
                self.operator_phone_edit.setText(
                    settings.get('operator_phone', '')
                )

                # 更新状态指示器：成功
                self._update_sync_status("success", f"已从服务器同步 (最后更新: {self._get_current_time()})")

                # 同时缓存到本地文件（保持兼容）
                self._save_to_local(settings)

            else:
                raise Exception(f"API返回异常: {response.status_code if response else '无响应'}")

        except Exception as e:
            print(f"[WARN] 从API加载设置失败: {e}，降级到本地文件")
            self._load_from_local_fallback()

    def _load_from_local_fallback(self):
        """
        降级策略：从本地文件加载配置（支持三级降级）

        数据源优先级：
        1. system_config.json (系统级默认值)
        2. local_settings.json (用户自定义覆盖)
        3. 硬编码默认值 (margin=25.0, rate=7.24)

        当API不可用或失败时，自动调用此方法。
        """
        try:
            from config.local_settings_manager import load_local_settings, SYSTEM_CONFIG_FILE
            settings = load_local_settings()

            # 记录日志：显示数据来源
            if SYSTEM_CONFIG_FILE:
                print(f"[INFO] ConfigDialog: 从 system_config.json + local_settings.json 加载配置")
                print(f"[DEBUG]   - system_config.json 路径: {SYSTEM_CONFIG_FILE}")
                source_info = "本地缓存（含系统配置）"
            else:
                print(f"[INFO] ConfigDialog: 从 local_settings.json 加载配置")
                print(f"[WARN]   - system_config.json 未找到")
                source_info = "本地缓存"

            print(f"[DEBUG]   - 配置项数量: {len(settings)}")
            for key, value in settings.items():
                print(f"     [OK] {key}: {value}")

            # 回填业务参数
            self.profit_margin_spin.setValue(
                float(settings.get('default_profit_margin', 25.0))
            )
            self.exchange_rate_spin.setValue(
                float(settings.get('exchange_rate', 7.24))
            )

            # 回填业务员基本信息（如果有）
            self.operator_name_edit.setText(
                settings.get('operator_name', '')
            )
            self.operator_phone_edit.setText(
                settings.get('operator_phone', '')
            )

            # 更新状态指示器：显示数据来源
            if SYSTEM_CONFIG_FILE:
                self._update_sync_status(
                    "warning",
                    f"✅ 已从 system_config.json 加载系统默认值\n"
                    f"⚠️ 服务器不可用，使用本地缓存（含系统配置）"
                )
            else:
                self._update_sync_status(
                    "warning",
                    f"⚠️ {source_info}（服务器不可用）。\n"
                    f"修改将仅保存在本地。"
                )

        except Exception as e:
            print(f"[ERROR] 从本地文件加载也失败: {e}，使用默认值")
            self._load_defaults()

    def _load_defaults(self):
        """
        最终兜底：使用硬编码默认值

        当API和本地文件都不可用时，使用内置默认值。
        """
        self.profit_margin_spin.setValue(25.0)
        self.exchange_rate_spin.setValue(7.24)
        self.operator_name_edit.clear()
        self.operator_phone_edit.clear()

        # 更新状态指示器：失败
        self._update_sync_status(
            "error",
            "无法加载任何配置，正在使用默认值。请联系管理员检查服务状态。"
        )

    def save_settings(self):
        """
        保存设置（双写策略：数据库 + 本地文件）

        保存流程：
        1. 收集所有配置项（包括新增的用户信息）
        2. 数据校验（合法性检查）
        3. 写入数据库（通过API循环调用PUT）
        4. 写入本地文件（始终执行，保证离线可用）
        5. 结果反馈（差异化提示）
        """
        try:
            # 1. 收集数据
            settings_data = {
                # 业务参数
                'default_profit_margin': self.profit_margin_spin.value(),
                'exchange_rate': self.exchange_rate_spin.value(),

                # 业务员基本信息（新增）
                'operator_name': self.operator_name_edit.text().strip(),
                'operator_phone': self.operator_phone_edit.text().strip(),
            }

            # 2. 数据校验
            margin = settings_data['default_profit_margin']
            if margin < 0 or margin > 100:
                raise ValueError("毛利率必须在 0-100% 之间")

            rate = settings_data['exchange_rate']
            if rate <= 0:
                raise ValueError("汇率必须大于 0")

            # 可选校验：业务员姓名非空
            if not settings_data['operator_name']:
                reply = QMessageBox.question(
                    self, "提示",
                    "业务员姓名为空，是否继续？\n\n"
                    "填写业务员信息有助于记录操作日志和审计追踪。",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return

            # 3. 写入数据库（通过API）
            db_success = False
            try:
                for key, value in settings_data.items():
                    response = self.api_client.put(
                        f"/api/settings/{key}",
                        json={"value": str(value)}
                    )

                    if response and response.status_code not in [200, 201]:
                        raise Exception(f"写入 {key} 失败: {response.status_code}")

                db_success = True

            except Exception as db_error:
                print(f"[WARN] 数据库写入失败: {db_error}")
                # 不阻断流程，继续写本地

            # 4. 写入本地文件（始终执行）
            self._save_to_local(settings_data)

            # 5. 结果反馈
            if db_success:
                QMessageBox.information(
                    self,
                    "✅ 保存成功",
                    f"配置已保存并同步到服务器\n\n"
                    f"📊 业务参数:\n"
                    f"   • 毛利率: {margin}%\n"
                    f"   • 汇率: {rate:.4f}\n\n"
                    f"👤 业务员基本信息:\n"
                    f"   • 姓名: {settings_data['operator_name'] or '(未填写)'}\n"
                    f"   • 联系电话: {settings_data['operator_phone'] or '(未填写)'}"
                )
                self.accept()
            else:
                reply = QMessageBox.warning(
                    self,
                    "⚠️ 部分成功",
                    f"配置已保存到本地，但同步到服务器失败。\n\n"
                    f"原因: 网络错误或服务器不可用\n\n"
                    f"本地数据将在下次连接成功后自动同步。\n\n"
                    f"是否关闭对话框？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    self.accept()

        except ValueError as ve:
            QMessageBox.warning(self, "数据校验失败", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"发生未知错误: {e}")

    def _save_to_local(self, settings):
        """
        保存配置到本地文件（双写策略的一部分）

        Args:
            settings: dict, 要保存的配置字典
        """
        try:
            from config.local_settings_manager import save_local_settings
            save_local_settings(settings)
        except Exception as e:
            print(f"[ERROR] 保存到本地文件失败: {e}")

    def _update_sync_status(self, status_type, message):
        """
        更新同步状态指示器

        Args:
            status_type: str, 状态类型 ("success" | "warning" | "error")
            message: str, 状态消息
        """
        styles = {
            "success": """
                QLabel {
                    background: #f0fdf4;
                    color: #166534;
                    padding: 10px 16px;
                    border-radius: 6px;
                    border: 1px solid #86efac;
                    font-weight: 500;
                }
            """,
            "warning": """
                QLabel {
                    background: #fefce8;
                    color: #854d0e;
                    padding: 10px 16px;
                    border-radius: 6px;
                    border: 1px solid #fde047;
                    font-weight: 500;
                }
            """,
            "error": """
                QLabel {
                    background: #fef2f2;
                    color: #991b1b;
                    padding: 10px 16px;
                    border-radius: 6px;
                    border: 1px solid #fecaca;
                    font-weight: 500;
                }
            """
        }

        icons = {
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }

        self.sync_status_label.setText(f"{icons.get(status_type, '')} {message}")
        self.sync_status_label.setStyleSheet(styles.get(status_type, styles["warning"]))

    @staticmethod
    def _get_current_time():
        """获取当前时间字符串"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
