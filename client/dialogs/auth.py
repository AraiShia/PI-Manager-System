# -*- coding: utf-8 -*-
"""登录和设置相关 Dialog"""

from PySide6.QtWidgets import QDialog, QLabel, QComboBox, QLineEdit, QPushButton, QGroupBox, QVBoxLayout, QHBoxLayout, QDoubleSpinBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from config import Config
from utils.machine_id import resolve_department, get_machine_code


class LoginWindow(QDialog):
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.selected_dept = None
        self.machine_code = get_machine_code()
        self.resolved_dept = resolve_department(self.machine_code)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("PI订单管理系统 - 登录")
        self.setFixedSize(700, 720)
        
        title = QLabel("PI订单管理系统", self)
        title.setGeometry(50, 80, 600, 60)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 36px; font-weight: bold;")
        
        version = QLabel("客户端 v1.0", self)
        version.setGeometry(50, 150, 600, 30)
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 16px; color: #666666;")
        
        mode_label = QLabel("登录模式：", self)
        mode_label.setGeometry(50, 220, 600, 30)
        mode_label.setAlignment(Qt.AlignCenter)
        mode_label.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 18px;")
        
        self.mode_combo = QComboBox(self)
        self.mode_combo.setGeometry(160, 260, 380, 50)
        self.mode_combo.addItem("普通用户模式", False)
        self.mode_combo.addItem("管理员模式", True)
        self.mode_combo.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 16px;")
        
        dept_label = QLabel("选择部门：", self)
        dept_label.setGeometry(50, 330, 600, 30)
        dept_label.setAlignment(Qt.AlignCenter)
        dept_label.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 18px;")

        self.dept_combo = QComboBox(self)
        self.dept_combo.setGeometry(160, 370, 380, 50)
        self.dept_combo.addItems([v["name"] for v in Config.DEPARTMENT_DB_CONFIG.values()])
        self.dept_combo.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 16px;")

        # 机器码显示（用于本地配置存储标识）
        machine_label = QLabel("机器码：", self)
        machine_label.setGeometry(50, 435, 600, 25)
        machine_label.setAlignment(Qt.AlignCenter)
        machine_label.setStyleSheet(
            "font-family: 'Microsoft YaHei'; font-size: 14px; color: #64748b;"
        )

        self.machine_value_label = QLabel(self.machine_code, self)
        self.machine_value_label.setGeometry(50, 460, 600, 25)
        self.machine_value_label.setAlignment(Qt.AlignCenter)
        self.machine_value_label.setStyleSheet(
            "font-family: 'Microsoft YaHei'; font-size: 12px; color: #2563eb;"
        )

        api_label = QLabel("API服务器地址：", self)
        api_label.setGeometry(50, 495, 600, 30)
        api_label.setAlignment(Qt.AlignCenter)
        api_label.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 18px;")
        
        self.api_url_input = QLineEdit(self)
        self.api_url_input.setGeometry(150, 535, 400, 50)
        self.api_url_input.setText(Config.API_BASE_URL)
        self.api_url_input.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 16px; padding-left: 10px;")

        self.login_btn = QPushButton("登录", self)
        self.login_btn.setGeometry(160, 600, 380, 55)
        self.login_btn.setStyleSheet("""
            QPushButton {
                font-family: 'Microsoft YaHei';
                font-size: 18px;
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.login_btn.clicked.connect(self.connect_to_server)
        
        self.status_label = QLabel("", self)
        self.status_label.setGeometry(50, 665, 600, 30)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 16px; color: red;")

    def connect_to_server(self):
        is_admin = self.mode_combo.currentData()
        dept_name = self.dept_combo.currentText()
        api_url = self.api_url_input.text().strip()

        if not api_url:
            self.status_label.setText("请输入API服务器地址")
            return

        self.status_label.setText("正在连接...")
        self.status_label.setStyleSheet("color: #2563eb;")

        try:
            dept_id = next((k for k, v in Config.DEPARTMENT_DB_CONFIG.items() if v["name"] == dept_name), "S")
            self.selected_dept = dept_id

            dept_db_config = Config.DEPARTMENT_DB_CONFIG[dept_id]

            self.api_client.base_url = api_url
            
            if hasattr(self.api_client, 'current_user'):
                from cache_manager import set_user
                self.api_client.current_user = {
                    "id": 1,
                    "username": "admin" if is_admin else "user",
                    "real_name": "管理员" if is_admin else "普通用户",
                    "is_admin": is_admin,
                    "dept_id": dept_id
                }
                set_user(str(self.api_client.current_user["id"]))
            
            db_config = {
                "db_host": dept_db_config["db_host"],
                "db_port": dept_db_config["db_port"],
                "db_user": dept_db_config["db_user"],
                "db_password": dept_db_config["db_password"],
                "db_name": dept_db_config["db_name"]
            }
            
            products = self.api_client.get_products(db_config=db_config)
            
            self.status_label.setText("连接成功！")
            self.status_label.setStyleSheet("color: #16a34a;")
            QTimer.singleShot(500, self.accept)
        except Exception as e:
            self.status_label.setText(f"连接失败: {str(e)}")
            self.status_label.setStyleSheet("color: #dc2626;")

    def get_selected_department(self):
        return self.selected_dept


class SettingsDialog(QDialog):
    """系统设置对话框"""
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.setWindowTitle("系统设置")
        self.setMinimumWidth(450)
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        profit_group = QGroupBox("毛利率设置")
        profit_layout = QVBoxLayout()
        
        profit_info = QLabel("毛利率用于自动计算产品报价基准价。\n公式: 预估美金报价 = 工厂人民币价格 × (1 + 毛利率) / 汇率")
        profit_info.setStyleSheet("color: #64748b; font-size: 12px;")
        profit_layout.addWidget(profit_info)
        
        profit_input_layout = QHBoxLayout()
        profit_input_layout.addWidget(QLabel("基础毛利率:"))
        
        self.profit_margin_spin = QDoubleSpinBox()
        self.profit_margin_spin.setRange(0, 100)
        self.profit_margin_spin.setDecimals(2)
        self.profit_margin_spin.setSuffix(" %")
        self.profit_margin_spin.setFixedWidth(120)
        profit_input_layout.addWidget(self.profit_margin_spin)
        
        profit_input_layout.addStretch()
        profit_layout.addLayout(profit_input_layout)
        
        profit_group.setLayout(profit_layout)
        layout.addWidget(profit_group)
        
        rate_group = QGroupBox("汇率设置")
        rate_layout = QVBoxLayout()
        
        rate_info = QLabel("人民币兑美元汇率，用于计算预估美金报价。")
        rate_info.setStyleSheet("color: #64748b; font-size: 12px;")
        rate_layout.addWidget(rate_info)
        
        rate_input_layout = QHBoxLayout()
        rate_input_layout.addWidget(QLabel("USD/RMB 汇率:"))
        
        self.exchange_rate_spin = QDoubleSpinBox()
        self.exchange_rate_spin.setRange(0.01, 100)
        self.exchange_rate_spin.setDecimals(4)
        self.exchange_rate_spin.setFixedWidth(120)
        rate_input_layout.addWidget(self.exchange_rate_spin)
        
        rate_input_layout.addStretch()
        rate_layout.addLayout(rate_input_layout)
        
        rate_group.setLayout(rate_layout)
        layout.addWidget(rate_group)
        
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
        save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def load_settings(self):
        try:
            from config.local_settings_manager import load_local_settings
            settings = load_local_settings()
            self.profit_margin_spin.setValue(settings.get('default_profit_margin', 25.0))
            self.exchange_rate_spin.setValue(settings.get('exchange_rate', 7.24))
        except Exception as e:
            print(f"加载设置失败: {e}")
            self.profit_margin_spin.setValue(25.0)
            self.exchange_rate_spin.setValue(7.24)
    
    def save_settings(self):
        try:
            margin = self.profit_margin_spin.value()
            rate = self.exchange_rate_spin.value()
            
            from config.local_settings_manager import save_local_settings
            settings = {
                'default_profit_margin': margin,
                'exchange_rate': rate
            }
            save_local_settings(settings)
            
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "成功", f"设置已保存\n毛利率: {margin}%\n汇率: {rate}")
            self.accept()
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", f"保存失败: {e}")