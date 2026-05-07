# -*- coding: utf-8 -*-
"""操作栏组件 - 统一管理表格中的操作按钮"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton


class ActionBarFactory:
    """操作栏工厂类 - 用于创建统一风格的操作按钮栏"""
    
    @staticmethod
    def create_customer_action_bar(edit_callback, toggle_callback, status):
        """创建客户管理操作栏"""
        widget = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        
        # 编辑按钮
        edit_btn = QPushButton("编辑")
        edit_btn.setFixedWidth(50)
        edit_btn.clicked.connect(edit_callback)
        btn_layout.addWidget(edit_btn)
        
        # 禁用/启用按钮
        toggle_btn = QPushButton("禁用" if status == 1 else "启用")
        toggle_btn.setFixedWidth(50)
        toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {'#ef4444' if status == 1 else '#10b981'};
                color: white;
                border: none;
                border-radius: 4px;
            }}
        """)
        toggle_btn.clicked.connect(toggle_callback)
        btn_layout.addWidget(toggle_btn)
        
        widget.setLayout(btn_layout)
        return widget
    
    @staticmethod
    def create_supplier_action_bar(edit_callback, toggle_callback, status):
        """创建供应商管理操作栏"""
        widget = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        
        # 编辑按钮
        edit_btn = QPushButton("编辑")
        edit_btn.setFixedWidth(50)
        edit_btn.clicked.connect(edit_callback)
        btn_layout.addWidget(edit_btn)
        
        # 禁用/启用按钮
        toggle_btn = QPushButton("禁用" if status == 1 else "启用")
        toggle_btn.setFixedWidth(50)
        toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {'#ef4444' if status == 1 else '#10b981'};
                color: white;
                border: none;
                border-radius: 4px;
            }}
        """)
        toggle_btn.clicked.connect(toggle_callback)
        btn_layout.addWidget(toggle_btn)
        
        widget.setLayout(btn_layout)
        return widget
    
    @staticmethod
    def create_product_action_bar(edit_callback, import_callback=None, cancel_import_callback=None, is_imported=False, is_admin=False):
        """创建产品管理操作栏"""
        widget = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        
        # 未导入状态：显示确认导入和编辑按钮
        if not is_imported:
            # 确认导入按钮（放在前面）
            if import_callback:
                import_btn = QPushButton("确认导入")
                import_btn.setFixedWidth(65)
                import_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f59e0b;
                        color: white;
                        border: none;
                        border-radius: 4px;
                    }
                """)
                import_btn.clicked.connect(import_callback)
                btn_layout.addWidget(import_btn)
            
            # 编辑按钮
            edit_btn = QPushButton("编辑")
            edit_btn.setFixedWidth(50)
            edit_btn.clicked.connect(edit_callback)
            btn_layout.addWidget(edit_btn)
        else:
            # 已导入状态
            if is_admin:
                # 管理员：显示编辑和取消导入按钮
                edit_btn = QPushButton("编辑")
                edit_btn.setFixedWidth(50)
                edit_btn.clicked.connect(edit_callback)
                btn_layout.addWidget(edit_btn)
                
                if cancel_import_callback:
                    cancel_btn = QPushButton("取消导入")
                    cancel_btn.setFixedWidth(65)
                    cancel_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #ef4444;
                            color: white;
                            border: none;
                            border-radius: 4px;
                        }
                    """)
                    cancel_btn.clicked.connect(cancel_import_callback)
                    btn_layout.addWidget(cancel_btn)
            # 普通用户：已导入状态不显示任何按钮
        
        widget.setLayout(btn_layout)
        return widget
    
    @staticmethod
    def create_pi_action_bar(edit_callback, detail_callback, status):
        """创建PI订单操作栏"""
        widget = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        
        # 编辑按钮
        edit_btn = QPushButton("编辑")
        edit_btn.setFixedWidth(50)
        edit_btn.clicked.connect(edit_callback)
        btn_layout.addWidget(edit_btn)
        
        # 详情按钮
        detail_btn = QPushButton("详情")
        detail_btn.setFixedWidth(50)
        detail_btn.clicked.connect(detail_callback)
        btn_layout.addWidget(detail_btn)
        
        # 状态按钮
        status_btn = QPushButton("关闭" if status == 1 else "打开")
        status_btn.setFixedWidth(50)
        status_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {'#ef4444' if status == 1 else '#10b981'};
                color: white;
                border: none;
                border-radius: 4px;
            }}
        """)
        btn_layout.addWidget(status_btn)
        
        widget.setLayout(btn_layout)
        return widget
