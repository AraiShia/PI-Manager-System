# -*- coding: utf-8 -*-
"""
状态灯管理器

文件：client/widgets/status_indicator.py
创建日期：2026-06-04
来源：main.py L3485-3509（UI创建）, L3715-3785（状态更新逻辑）（已提取）
用途：封装订单详情页的4个状态灯（圆点+文字），可独立复用

调用方式：
```python
from widgets import StatusIndicatorManager

# 方式1：创建独立widget
manager = StatusIndicatorManager()
indicator_widget = manager.create_widget()

# 方式2：传入parent
manager = StatusIndicatorManager(parent=self)
indicator_widget = manager.create_widget()

# 方式3：传入已有layout
manager = StatusIndicatorManager()
manager.create_widget(your_layout)

# 更新状态
manager.update({'is_temp': False, 'is_purchased': True, 'has_stock': True, 'has_invoice': False})

# 设为灰色
manager.set_gray()
```

依赖：
- PySide6.QtWidgets: QWidget, QHBoxLayout, QLabel
- PySide6.QtCore: Qt
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt


class StatusIndicatorManager:
    """
    状态灯管理器
    
    功能：
    - 创建4个状态灯（圆点+文字）：正式/临时、已采/未采、有库/缺库、有票/无票
    - 根据状态字典更新颜色和文字
    - 支持灰色默认状态
    
    状态灯配置：
    | 索引 | 状态键 | 激活文字 | 未激活文字 | 激活颜色 | 未激活颜色 |
    |------|--------|----------|------------|----------|------------|
    | 0    | is_temp | 正式      | 临时       | #22c55e  | #fbbf24   |
    | 1    | is_purchased | 已采 | 未采     | #3b82f6  | #6b7280   |
    | 2    | has_stock | 有库     | 缺库       | #22c55e  | #ef4444   |
    | 3    | has_invoice | 有票    | 无票       | #22c55e  | #6b7280   |
    
    使用示例：
    ```python
    from widgets import StatusIndicatorManager
    
    # 在 MainWindow 中创建
    self._status_manager = StatusIndicatorManager(self)
    self._status_indicator = self._status_manager.create_widget()
    header_layout.addWidget(self._status_indicator)
    
    # 当产品状态变化时更新
    item_status = {
        'is_temp': False,
        'is_purchased': True,
        'has_stock': True,
        'has_invoice': False
    }
    self._status_manager.update(item_status)
    ```
    """
    
    # 状态灯配置常量
    STATUS_CONFIG = [
        {
            'key': 'is_temp',
            'active_text': '正式',
            'inactive_text': '临时',
            'active_color': '#22c55e',
            'inactive_color': '#fbbf24',
        },
        {
            'key': 'is_purchased',
            'active_text': '已采',
            'inactive_text': '未采',
            'active_color': '#3b82f6',
            'inactive_color': '#6b7280',
        },
        {
            'key': 'has_stock',
            'active_text': '有库',
            'inactive_text': '缺库',
            'active_color': '#22c55e',
            'inactive_color': '#ef4444',
        },
        {
            'key': 'has_invoice',
            'active_text': '有票',
            'inactive_text': '无票',
            'active_color': '#22c55e',
            'inactive_color': '#6b7280',
        },
    ]
    
    def __init__(self, parent=None):
        """
        初始化状态灯管理器
        
        Args:
            parent: QWidget, 父窗口（可选）
        """
        self.parent = parent
        self._widget = None
        self._layout = None
        self.dots = []  # 圆点 QLabel 列表
        self.labels = []  # 文字 QLabel 列表
    
    def create_widget(self, layout=None) -> QWidget:
        """
        创建状态灯容器 widget
        
        Args:
            layout: QHBoxLayout, 如果传入则将 widget 添加到此 layout（可选）
        
        Returns:
            QWidget: 状态灯容器 widget
        """
        self._widget = QWidget(self.parent)
        self._layout = QHBoxLayout(self._widget)
        self._layout.setContentsMargins(8, 0, 0, 0)
        self._layout.setSpacing(8)
        
        for config in self.STATUS_CONFIG:
            # 创建圆点
            dot = QLabel()
            dot.setFixedSize(12, 12)
            dot.setStyleSheet("background-color: #6b7280; border-radius: 6px;")
            self._layout.addWidget(dot)
            self.dots.append(dot)
            
            # 创建文字标签
            label = QLabel(config['inactive_text'])
            label.setStyleSheet("color: #6b7280; font-size: 12px;")
            self._layout.addWidget(label)
            self.labels.append(label)
        
        if layout is not None:
            layout.addWidget(self._widget)
        
        return self._widget
    
    def update(self, status_dict: dict):
        """
        根据状态字典更新状态灯颜色和文字
        
        Args:
            status_dict: dict, 产品状态字典，包含以下键：
                - is_temp: bool, 是否临时产品
                - is_purchased: bool, 是否已采购
                - has_stock: bool, 是否有库存
                - has_invoice: bool, 是否有发票
        """
        if not self._widget:
            return
        
        for i, config in enumerate(self.STATUS_CONFIG):
            key = config['key']
            # 对于 is_temp，True 表示临时（未激活），False 表示正式（激活）
            if key == 'is_temp':
                is_active = not status_dict.get(key, False)
            else:
                is_active = status_dict.get(key, False)
            
            color = config['active_color'] if is_active else config['inactive_color']
            text = config['active_text'] if is_active else config['inactive_text']
            
            # 更新圆点颜色
            self.dots[i].setStyleSheet(f"background-color: {color}; border-radius: 6px;")
            
            # 更新文字
            self.labels[i].setText(text)
            self.labels[i].setStyleSheet(f"color: {color}; font-size: 12px;")
    
    def set_gray(self):
        """
        设置所有状态灯为灰色默认状态
        
        用于无选中行或数据加载中时的默认显示。
        """
        if not self._widget:
            return
        
        for i, config in enumerate(self.STATUS_CONFIG):
            self.dots[i].setStyleSheet("background-color: #6b7280; border-radius: 6px;")
            self.labels[i].setText(config['inactive_text'])
            self.labels[i].setStyleSheet("color: #6b7280; font-size: 12px;")
    
    @staticmethod
    def get_status_labels() -> list:
        """
        获取状态灯文字配置列表
        
        Returns:
            list[dict]: 状态灯配置列表，每个配置包含 key, active_text, inactive_text
        """
        return [
            {'key': c['key'], 'active_text': c['active_text'], 'inactive_text': c['inactive_text']}
            for c in StatusIndicatorManager.STATUS_CONFIG
        ]
    
    @staticmethod
    def calculate_status_from_item(item: dict) -> dict:
        """
        从产品项数据计算状态字典
        
        Args:
            item: dict, 产品项数据
        
        Returns:
            dict: 状态字典
        """
        return {
            'is_temp': item.get('is_temp', False),
            'is_purchased': item.get('is_purchased', False),
            'has_stock': item.get('has_stock', True),
            'has_invoice': item.get('has_invoice', False)
        }