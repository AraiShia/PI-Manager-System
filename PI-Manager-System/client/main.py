# -*- coding: utf-8 -*-
import sys
import os
import pandas as pd
import asyncio
import ctypes
import urllib.request
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'config'))

# 省份编码映射（静态数据，模块级别只创建一次）
PROVINCE_CODE_MAP = {
    "北京": "11", "天津": "12", "河北": "13", "山西": "14", "内蒙古": "15",
    "辽宁": "21", "吉林": "22", "黑龙江": "23",
    "上海": "31", "江苏": "32", "浙江": "33", "安徽": "34", "福建": "35", "江西": "36", "山东": "37",
    "河南": "41", "湖北": "42", "湖南": "43", "广东": "44", "广西": "45", "海南": "46",
    "重庆": "50", "四川": "51", "贵州": "52", "云南": "53", "西藏": "54",
    "陕西": "61", "甘肃": "62", "青海": "63", "宁夏": "64", "新疆": "65",
    "台湾": "71", "香港": "81", "澳门": "82"
}

# 城市编码映射（静态数据，模块级别只创建一次）
CITY_CODE_MAP = {
    "11": {"北京": "1"}, "12": {"天津": "1"}, "31": {"上海": "1"}, "50": {"重庆": "1"},
    "13": {"石家庄": "1", "唐山": "2", "秦皇岛": "3", "邯郸": "4", "邢台": "5", "保定": "6", "张家口": "7", "承德": "8", "沧州": "9", "廊坊": "A", "衡水": "B"},
    "14": {"太原": "1", "大同": "2", "阳泉": "3", "长治": "4", "晋城": "5", "朔州": "6", "晋中": "7", "运城": "8", "忻州": "9", "临汾": "A", "吕梁": "B"},
    "15": {"呼和浩特": "1", "包头": "2", "乌海": "3", "赤峰": "4", "通辽": "5", "鄂尔多斯": "6", "呼伦贝尔": "7", "巴彦淖尔": "8", "乌兰察布": "9", "兴安": "A", "锡林郭勒": "B", "阿拉善": "C"},
    "21": {"沈阳": "1", "大连": "2", "鞍山": "3", "抚顺": "4", "本溪": "5", "丹东": "6", "锦州": "7", "营口": "8", "阜新": "9", "辽阳": "A", "盘锦": "B", "铁岭": "C", "朝阳": "D", "葫芦岛": "E"},
    "22": {"长春": "1", "吉林": "2", "四平": "3", "辽源": "4", "通化": "5", "白山": "6", "松原": "7", "白城": "8", "延边": "9"},
    "23": {"哈尔滨": "1", "齐齐哈尔": "2", "鸡西": "3", "鹤岗": "4", "双鸭山": "5", "大庆": "6", "伊春": "7", "佳木斯": "8", "七台河": "9", "牡丹江": "A", "黑河": "B", "绥化": "C", "大兴安岭": "D"},
    "32": {"南京": "1", "无锡": "2", "徐州": "3", "常州": "4", "苏州": "5", "南通": "6", "连云港": "7", "淮安": "8", "盐城": "9", "扬州": "A", "镇江": "B", "泰州": "C", "宿迁": "D"},
    "33": {"杭州": "1", "宁波": "2", "温州": "3", "嘉兴": "4", "湖州": "5", "绍兴": "6", "金华": "7", "衢州": "8", "舟山": "9", "台州": "A", "丽水": "B"},
    "34": {"合肥": "1", "芜湖": "2", "蚌埠": "3", "淮南": "4", "马鞍山": "5", "淮北": "6", "铜陵": "7", "安庆": "8", "黄山": "9", "阜阳": "A", "宿州": "B", "滁州": "C", "六安": "D", "宣城": "E", "池州": "F", "亳州": "G"},
    "35": {"福州": "1", "厦门": "2", "莆田": "3", "三明": "4", "泉州": "5", "漳州": "6", "南平": "7", "龙岩": "8", "宁德": "9"},
    "36": {"南昌": "1", "景德镇": "2", "萍乡": "3", "九江": "4", "新余": "5", "鹰潭": "6", "赣州": "7", "吉安": "8", "宜春": "9", "抚州": "A", "上饶": "B"},
    "37": {"济南": "1", "青岛": "2", "淄博": "3", "枣庄": "4", "东营": "5", "烟台": "6", "潍坊": "7", "济宁": "8", "泰安": "9", "威海": "A", "日照": "B", "临沂": "C", "德州": "D", "滨州": "E", "菏泽": "F"},
    "41": {"郑州": "1", "开封": "2", "洛阳": "3", "平顶山": "4", "安阳": "5", "鹤壁": "6", "新乡": "7", "焦作": "8", "濮阳": "9", "许昌": "A", "漯河": "B", "三门峡": "C", "南阳": "D", "商丘": "E", "信阳": "F", "周口": "G", "驻马店": "H", "济源": "I"},
    "42": {"武汉": "1", "黄石": "2", "十堰": "3", "宜昌": "4", "襄阳": "5", "鄂州": "6", "荆门": "7", "孝感": "8", "荆州": "9", "黄冈": "A", "咸宁": "B", "随州": "C", "恩施": "D", "仙桃": "E", "潜江": "F", "天门": "G"},
    "43": {"长沙": "1", "株洲": "2", "湘潭": "3", "衡阳": "4", "邵阳": "5", "岳阳": "6", "常德": "7", "张家界": "8", "益阳": "9", "郴州": "A", "永州": "B", "怀化": "C", "娄底": "D", "湘西": "E"},
    "44": {"广州": "1", "韶关": "2", "深圳": "3", "珠海": "4", "汕头": "5", "佛山": "6", "江门": "7", "湛江": "8", "茂名": "9", "肇庆": "A", "惠州": "B", "梅州": "C", "汕尾": "D", "河源": "E", "阳江": "F", "清远": "G", "东莞": "H", "中山": "I", "潮州": "J", "揭阳": "K", "云浮": "L"},
    "45": {"南宁": "1", "柳州": "2", "桂林": "3", "梧州": "4", "北海": "5", "防城港": "6", "钦州": "7", "贵港": "8", "玉林": "9", "百色": "A", "贺州": "B", "河池": "C", "来宾": "D", "崇左": "E"},
    "46": {"海口": "1", "三亚": "2", "三沙": "3", "儋州": "4"},
    "51": {"成都": "1", "自贡": "2", "攀枝花": "3", "泸州": "4", "德阳": "5", "绵阳": "6", "广元": "7", "遂宁": "8", "内江": "9", "乐山": "A", "南充": "B", "眉山": "C", "宜宾": "D", "广安": "E", "达州": "F", "雅安": "G", "巴中": "H", "资阳": "I", "阿坝": "J", "甘孜": "K", "凉山": "L"},
    "52": {"贵阳": "1", "六盘水": "2", "遵义": "3", "安顺": "4", "毕节": "5", "铜仁": "6", "黔西南": "7", "黔东南": "8", "黔南": "9"},
    "53": {"昆明": "1", "曲靖": "2", "玉溪": "3", "保山": "4", "昭通": "5", "丽江": "6", "普洱": "7", "临沧": "8", "楚雄": "9", "红河": "A", "文山": "B", "西双版纳": "C", "大理": "D", "怒江": "E", "迪庆": "F"},
    "54": {"拉萨": "1", "日喀则": "2", "昌都": "3", "林芝": "4", "山南": "5", "那曲": "6", "阿里": "7"},
    "61": {"西安": "1", "铜川": "2", "宝鸡": "3", "咸阳": "4", "渭南": "5", "延安": "6", "汉中": "7", "榆林": "8", "安康": "9", "商洛": "A"},
    "62": {"兰州": "1", "嘉峪关": "2", "金昌": "3", "白银": "4", "天水": "5", "武威": "6", "张掖": "7", "平凉": "8", "酒泉": "9", "庆阳": "A", "定西": "B", "陇南": "C", "临夏": "D", "甘南": "E"},
    "63": {"西宁": "1", "海东": "2", "海北": "3", "黄南": "4", "海南": "5", "果洛": "6", "玉树": "7", "海西": "8"},
    "64": {"银川": "1", "石嘴山": "2", "吴忠": "3", "固原": "4", "中卫": "5"},
    "65": {"乌鲁木齐": "1", "克拉玛依": "2", "吐鲁番": "3", "哈密": "4", "昌吉": "5", "博尔塔拉": "6", "巴音郭楞": "7", "阿克苏": "8", "克孜勒苏": "9", "喀什": "A", "和田": "B", "伊犁": "C", "塔城": "D", "阿勒泰": "E", "石河子": "F", "阿拉尔": "G", "图木舒克": "H", "五家渠": "I", "北屯": "J", "铁门关": "K", "双河": "L", "可克达拉": "M", "昆玉": "N", "胡杨河": "O", "新星": "P"},
    "71": {"台北": "1", "高雄": "2", "台中": "3", "台南": "4", "新北": "5", "桃园": "6"},
    "81": {"香港": "1"}, "82": {"澳门": "1"}
}

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QStackedWidget, QMessageBox, QTableWidget, QTableWidgetItem, QDialog, QFormLayout, QLineEdit, QTextEdit, QComboBox, QHeaderView, QAbstractItemView, QGridLayout, QCheckBox, QGroupBox, QFileDialog, QProgressDialog, QTabWidget, QScrollArea
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPalette, QColor, QFont, QFontDatabase, QBrush, QPixmap, QImage
from api.client import ApiClient
from api.cached_client import CachedApiClient
from config import Config
from cache_manager import cache_manager
from product_categories import get_category_options, get_category_code, get_category_name
from widgets.action_bar import ActionBarFactory

def get_font(size=10, weight=QFont.Weight.Normal):
    font = QFont()
    font.setPointSize(size)
    font.setWeight(weight)
    # 尝试多种中文字体
    available = QFontDatabase.families()
    for family in ["Microsoft YaHei", "SimHei", "SimSun", "KaiTi", "WenQuanYi Micro Hei", "Heiti SC"]:
        if family in available:
            font.setFamily(family)
            return font
    # 如果没有中文字体，使用默认字体
    font.setFamily(QFont().defaultFamily())
    return font

def set_global_font(app):
    font = get_font(10)
    app.setFont(font)

# 部门配置映射（从配置文件获取）
DEPARTMENT_CONFIG = Config.DEPARTMENT_DB_CONFIG

class LoginWindow(QDialog):
    def __init__(self, api_client: ApiClient):
        super().__init__()
        self.api_client = api_client
        self.selected_dept = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("PI订单管理系统 - 登录")
        self.setFixedSize(700, 650)
        
        # 使用绝对定位
        # 标题
        title = QLabel("PI订单管理系统", self)
        title.setGeometry(50, 80, 600, 60)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 36px; font-weight: bold;")
        
        # 版本
        version = QLabel("客户端 v1.0", self)
        version.setGeometry(50, 150, 600, 30)
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 16px; color: #666666;")
        
        # 登录模式选择
        mode_label = QLabel("登录模式：", self)
        mode_label.setGeometry(50, 220, 600, 30)
        mode_label.setAlignment(Qt.AlignCenter)
        mode_label.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 18px;")
        
        self.mode_combo = QComboBox(self)
        self.mode_combo.setGeometry(160, 260, 380, 50)
        self.mode_combo.addItem("普通用户模式", False)
        self.mode_combo.addItem("管理员模式", True)
        self.mode_combo.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 16px;")
        
        # 部门标签
        dept_label = QLabel("选择部门：", self)
        dept_label.setGeometry(50, 330, 600, 30)
        dept_label.setAlignment(Qt.AlignCenter)
        dept_label.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 18px;")
        
        # 部门下拉框
        self.dept_combo = QComboBox(self)
        self.dept_combo.setGeometry(160, 370, 380, 50)
        self.dept_combo.addItems([v["name"] for v in DEPARTMENT_CONFIG.values()])
        self.dept_combo.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 16px;")
        
        # API标签
        api_label = QLabel("API服务器地址：", self)
        api_label.setGeometry(50, 440, 600, 30)
        api_label.setAlignment(Qt.AlignCenter)
        api_label.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 18px;")
        
        # API输入框
        self.api_url_input = QLineEdit(self)
        self.api_url_input.setGeometry(150, 480, 400, 50)
        self.api_url_input.setText(Config.API_BASE_URL)
        self.api_url_input.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 16px; padding-left: 10px;")
        
        # 登录按钮
        self.login_btn = QPushButton("登录", self)
        self.login_btn.setGeometry(160, 550, 380, 55)
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
        
        # 状态标签
        self.status_label = QLabel("", self)
        self.status_label.setGeometry(50, 620, 600, 30)
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
            # 获取部门ID和对应的数据库配置（自动获取，不对外显示）
            dept_id = next((k for k, v in DEPARTMENT_CONFIG.items() if v["name"] == dept_name), "S")
            self.selected_dept = dept_id
            
            # 从部门配置中自动获取数据库连接参数
            dept_db_config = DEPARTMENT_CONFIG[dept_id]

            # 设置API客户端
            self.api_client.base_url = api_url
            
            # 设置当前用户信息（模拟登录）
            if hasattr(self.api_client, 'current_user'):
                self.api_client.current_user = {
                    "id": 1,
                    "username": "admin" if is_admin else "user",
                    "real_name": "管理员" if is_admin else "普通用户",
                    "is_admin": is_admin,
                    "dept_id": dept_id
                }
                # 设置缓存用户ID
                cache_manager.set_user(str(self.api_client.current_user["id"]))
            
            # 传递数据库配置到API（从配置文件获取，不对外显示）
            db_config = {
                "db_host": dept_db_config["db_host"],
                "db_port": dept_db_config["db_port"],
                "db_user": dept_db_config["db_user"],
                "db_password": dept_db_config["db_password"],
                "db_name": dept_db_config["db_name"]
            }
            
            # 测试连接
            products = self.api_client.get_products(db_config=db_config)
            
            self.status_label.setText("连接成功！")
            self.status_label.setStyleSheet("color: #16a34a;")
            QTimer.singleShot(500, self.accept)
        except Exception as e:
            self.status_label.setText(f"连接失败: {str(e)}")
            self.status_label.setStyleSheet("color: #dc2626;")

    def get_selected_department(self):
        return self.selected_dept


class ProductDialog(QDialog):
    def __init__(self, api_client: ApiClient, dept_id: str, product=None):
        super().__init__()
        self.api_client = api_client
        self.dept_id = dept_id
        self.product = product
        self.is_edit = product is not None
        self.suppliers = []
        self.init_ui()
        QTimer.singleShot(0, self.load_suppliers)

    def load_suppliers(self):
        try:
            self.suppliers = self.api_client.get_suppliers()
            self.supplier_combo.clear()
            self.supplier_combo.addItem("", "")
            for s in self.suppliers:
                self.supplier_combo.addItem(f"{s.get('supplier_code')} - {s.get('supplier_name')}", s.get('id'))
            
            if self.product and self.product.get('supplier_id'):
                for i in range(self.supplier_combo.count()):
                    if self.supplier_combo.itemData(i) == self.product.get('supplier_id'):
                        self.supplier_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            print(f"加载供应商失败: {e}")

    def init_ui(self):
        self.setWindowTitle("编辑产品" if self.is_edit else "新增产品")
        self.setMinimumSize(700, 800)
        self.resize(700, 800)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        
        form_layout = QFormLayout(scroll_widget)
        form_layout.setSpacing(15)

        if self.is_edit:
            self.code_label = QLabel(self.product.get('product_code', ''))
            form_layout.addRow("产品编号:", self.code_label)

        self.oe_input = QLineEdit()
        self.oe_input.setPlaceholderText("请输入OE号")
        self.oe_input.setMinimumHeight(32)
        if self.product:
            self.oe_input.setText(self.product.get('oe_number', ''))
        form_layout.addRow("OE号:", self.oe_input)

        self.factory_input = QLineEdit()
        self.factory_input.setPlaceholderText("请输入工厂编号")
        self.factory_input.setMinimumHeight(32)
        if self.product:
            self.factory_input.setText(self.product.get('factory_code', ''))
        form_layout.addRow("工厂编号:", self.factory_input)

        self.brand_input = QLineEdit()
        self.brand_input.setPlaceholderText("请输入品牌")
        self.brand_input.setMinimumHeight(32)
        if self.product:
            self.brand_input.setText(self.product.get('brand', ''))
        form_layout.addRow("品牌:", self.brand_input)

        self.detail_input = QTextEdit()
        self.detail_input.setPlaceholderText("请输入产品细节描述")
        if self.product:
            self.detail_input.setText(self.product.get('detail_desc', ''))
        self.detail_input.setMaximumHeight(80)
        form_layout.addRow("细节描述:", self.detail_input)

        self.supplier_combo = QComboBox()
        self.supplier_combo.setFixedHeight(35)
        form_layout.addRow("供应商:", self.supplier_combo)

        price_group = QGroupBox("价格信息")
        price_group.setMinimumHeight(120)
        price_layout = QGridLayout()
        
        self.exw_incl_input = QLineEdit()
        self.exw_incl_input.setPlaceholderText("EXW含税价")
        self.exw_incl_input.setMinimumHeight(32)
        if self.product:
            self.exw_incl_input.setText(str(self.product.get('exw_price_incl', '') or ''))
        price_layout.addWidget(QLabel("EXW含税价:"), 0, 0)
        price_layout.addWidget(self.exw_incl_input, 0, 1)

        self.exw_excl_input = QLineEdit()
        self.exw_excl_input.setPlaceholderText("EXW不含税价")
        self.exw_excl_input.setMinimumHeight(32)
        if self.product:
            self.exw_excl_input.setText(str(self.product.get('exw_price_excl', '') or ''))
        price_layout.addWidget(QLabel("EXW不含税价:"), 0, 2)
        price_layout.addWidget(self.exw_excl_input, 0, 3)

        self.fob_incl_input = QLineEdit()
        self.fob_incl_input.setPlaceholderText("FOB含税价")
        self.fob_incl_input.setMinimumHeight(32)
        if self.product:
            self.fob_incl_input.setText(str(self.product.get('fob_price_incl', '') or ''))
        price_layout.addWidget(QLabel("FOB含税价:"), 1, 0)
        price_layout.addWidget(self.fob_incl_input, 1, 1)

        self.fob_excl_input = QLineEdit()
        self.fob_excl_input.setPlaceholderText("FOB不含税价")
        self.fob_excl_input.setMinimumHeight(32)
        if self.product:
            self.fob_excl_input.setText(str(self.product.get('fob_price_excl', '') or ''))
        price_layout.addWidget(QLabel("FOB不含税价:"), 1, 2)
        price_layout.addWidget(self.fob_excl_input, 1, 3)

        self.freight_input = QLineEdit()
        self.freight_input.setPlaceholderText("运费")
        self.freight_input.setMinimumHeight(32)
        if self.product:
            self.freight_input.setText(str(self.product.get('freight', '') or ''))
        price_layout.addWidget(QLabel("运费:"), 2, 0)
        price_layout.addWidget(self.freight_input, 2, 1)

        self.packing_fee_input = QLineEdit()
        self.packing_fee_input.setPlaceholderText("包装费")
        self.packing_fee_input.setMinimumHeight(32)
        if self.product:
            self.packing_fee_input.setText(str(self.product.get('packing_fee', '') or ''))
        price_layout.addWidget(QLabel("包装费:"), 2, 2)
        price_layout.addWidget(self.packing_fee_input, 2, 3)

        price_group.setLayout(price_layout)
        form_layout.addRow(price_group)

        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("请输入采购渠道（如1688、对私付款等）")
        self.channel_input.setMinimumHeight(32)
        if self.product:
            self.channel_input.setText(self.product.get('purchase_channel', ''))
        form_layout.addRow("采购渠道:", self.channel_input)

        size_group = QGroupBox("包装尺寸")
        size_group.setMinimumHeight(120)
        size_layout = QGridLayout()
        
        self.carton_length_input = QLineEdit()
        self.carton_length_input.setPlaceholderText("长(cm)")
        self.carton_length_input.setMinimumHeight(32)
        if self.product:
            self.carton_length_input.setText(str(self.product.get('carton_length_cm', '') or ''))
        size_layout.addWidget(QLabel("纸箱长(cm):"), 0, 0)
        size_layout.addWidget(self.carton_length_input, 0, 1)

        self.carton_width_input = QLineEdit()
        self.carton_width_input.setPlaceholderText("宽(cm)")
        self.carton_width_input.setMinimumHeight(32)
        if self.product:
            self.carton_width_input.setText(str(self.product.get('carton_width_cm', '') or ''))
        size_layout.addWidget(QLabel("纸箱宽(cm):"), 0, 2)
        size_layout.addWidget(self.carton_width_input, 0, 3)

        self.carton_height_input = QLineEdit()
        self.carton_height_input.setPlaceholderText("高(cm)")
        self.carton_height_input.setMinimumHeight(32)
        if self.product:
            self.carton_height_input.setText(str(self.product.get('carton_height_cm', '') or ''))
        size_layout.addWidget(QLabel("纸箱高(cm):"), 1, 0)
        size_layout.addWidget(self.carton_height_input, 1, 1)

        self.units_input = QLineEdit()
        self.units_input.setPlaceholderText("每箱数量")
        self.units_input.setMinimumHeight(32)
        if self.product:
            self.units_input.setText(str(self.product.get('units_per_carton', '') or ''))
        size_layout.addWidget(QLabel("每箱数量:"), 1, 2)
        size_layout.addWidget(self.units_input, 1, 3)

        size_group.setLayout(size_layout)
        form_layout.addRow(size_group)

        weight_group = QGroupBox("重量信息")
        weight_group.setMinimumHeight(80)
        weight_layout = QHBoxLayout()
        
        self.gross_weight_input = QLineEdit()
        self.gross_weight_input.setPlaceholderText("毛重(kg)")
        self.gross_weight_input.setMinimumHeight(32)
        if self.product:
            self.gross_weight_input.setText(str(self.product.get('gross_weight_kg', '') or ''))
        weight_layout.addWidget(QLabel("毛重(kg):"))
        weight_layout.addWidget(self.gross_weight_input)

        self.weight_input = QLineEdit()
        self.weight_input.setPlaceholderText("净重(kg)")
        self.weight_input.setMinimumHeight(32)
        if self.product:
            self.weight_input.setText(str(self.product.get('weight_kg', '') or ''))
        weight_layout.addWidget(QLabel("净重(kg):"))
        weight_layout.addWidget(self.weight_input)

        weight_group.setLayout(weight_layout)
        form_layout.addRow(weight_group)

        self.category_combo = QComboBox()
        self.category_combo.setFixedHeight(35)
        for code, name in get_category_options():
            self.category_combo.addItem(name, code)
        
        if self.product:
            category_code = str(self.product.get('category_id', '01'))
            for i in range(self.category_combo.count()):
                if self.category_combo.itemData(i) == category_code:
                    self.category_combo.setCurrentIndex(i)
                    break
        form_layout.addRow("产品类别:", self.category_combo)

        # 图片上传区域
        image_group = QGroupBox("产品图片")
        image_group.setMinimumHeight(300)
        image_layout = QVBoxLayout()
        
        self.image_preview = QLabel()
        self.image_preview.setFixedSize(200, 200)
        self.image_preview.setStyleSheet("border: 2px dashed #d1d5db;")
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setText("点击选择图片")
        self.image_preview.setCursor(Qt.PointingHandCursor)
        # 使用事件过滤器替代直接赋值mousePressEvent，更可靠
        self.image_preview.installEventFilter(self)
        
        self.selected_image_path = None
        if self.product and self.product.get('default_image_url'):
            try:
                image_data = urllib.request.urlopen(self.product.get('default_image_url')).read()
                image = QImage.fromData(image_data)
                pixmap = QPixmap.fromImage(image).scaled(196, 196, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_preview.setPixmap(pixmap)
                self.image_preview.setText("")
            except:
                pass
        
        image_layout.addWidget(self.image_preview)
        
        image_btn_layout = QHBoxLayout()
        self.upload_image_btn = QPushButton("上传图片")
        self.upload_image_btn.setFixedWidth(100)
        self.upload_image_btn.clicked.connect(self.select_image)
        image_btn_layout.addWidget(self.upload_image_btn)
        
        self.clear_image_btn = QPushButton("清除图片")
        self.clear_image_btn.setFixedWidth(100)
        self.clear_image_btn.clicked.connect(self.clear_image)
        image_btn_layout.addWidget(self.clear_image_btn)
        
        image_layout.addLayout(image_btn_layout)
        image_group.setLayout(image_layout)
        form_layout.addRow(image_group)

        # 将滚动区域添加到主布局
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.save_product)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj == self.image_preview and event.type() == QEvent.MouseButtonPress:
            self.select_image(event)
            return True
        return super().eventFilter(obj, event)
    
    def select_image(self, event=None):
        print("DEBUG - select_image called")
        # 如果已经有图片显示，显示选项菜单
        if self.image_preview.pixmap() is not None:
            print("DEBUG - 已有图片，显示菜单")
            from PySide6.QtWidgets import QMenu
            from PySide6.QtGui import QAction
            menu = QMenu(self)
            view_action = QAction("查看大图", self)
            change_action = QAction("更换图片", self)
            menu.addAction(view_action)
            menu.addAction(change_action)
            
            def view_image():
                print("DEBUG - 查看大图")
                from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel
                dialog = QDialog(self)
                dialog.setWindowTitle("查看图片")
                dialog.setMinimumSize(600, 600)
                layout = QVBoxLayout()
                label = QLabel()
                label.setAlignment(Qt.AlignCenter)
                if self.selected_image_path:
                    pixmap = QPixmap(self.selected_image_path).scaled(580, 580, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                else:
                    pixmap = self.image_preview.pixmap().scaled(580, 580, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label.setPixmap(pixmap)
                layout.addWidget(label)
                dialog.setLayout(layout)
                dialog.exec()
            
            def change_image():
                print("DEBUG - 更换图片")
                file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.gif)")
                print(f"DEBUG - 选择的文件路径: {file_path}")
                if file_path:
                    self.selected_image_path = file_path
                    print(f"DEBUG - selected_image_path 设置为: {self.selected_image_path}")
                    pixmap = QPixmap(file_path).scaled(196, 196, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.image_preview.setPixmap(pixmap)
            
            view_action.triggered.connect(view_image)
            change_action.triggered.connect(change_image)
            
            menu.exec(self.image_preview.mapToGlobal(event.pos()) if event else self.image_preview.mapToGlobal(self.image_preview.rect().center()))
            return
        
        # 没有图片时，直接选择图片
        print("DEBUG - 没有图片，直接选择")
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.gif)")
        print(f"DEBUG - 选择的文件路径: {file_path}")
        if file_path:
            self.selected_image_path = file_path
            print(f"DEBUG - selected_image_path 设置为: {self.selected_image_path}")
            pixmap = QPixmap(file_path).scaled(196, 196, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_preview.setPixmap(pixmap)
            self.image_preview.setText("")

    def clear_image(self):
        self.selected_image_path = None
        self.image_preview.clear()
        self.image_preview.setText("点击选择图片")

    def save_product(self):
        print("DEBUG - save_product called")
        
        oe_number = self.oe_input.text().strip()
        detail_desc = self.detail_input.toPlainText().strip()
        
        print(f"DEBUG - oe_number: '{oe_number}'")
        print(f"DEBUG - detail_desc: '{detail_desc}'")
        
        if not oe_number:
            QMessageBox.warning(self, "提示", "请输入OE号")
            return
        
        if not detail_desc:
            QMessageBox.warning(self, "提示", "请输入细节描述")
            return

        data = {
            "dept_id": self.dept_id,
            "oe_number": oe_number,
            "factory_code": self.factory_input.text().strip(),
            "brand": self.brand_input.text().strip(),
            "detail_desc": detail_desc,
            "supplier_id": self.supplier_combo.currentData() or None,
            "purchase_channel": self.channel_input.text().strip(),
            "category_id": int(self.category_combo.currentData()),
        }

        def try_float(value):
            try:
                return float(value) if value.strip() else None
            except ValueError:
                return None

        data["exw_price_incl"] = try_float(self.exw_incl_input.text())
        data["exw_price_excl"] = try_float(self.exw_excl_input.text())
        data["fob_price_incl"] = try_float(self.fob_incl_input.text())
        data["fob_price_excl"] = try_float(self.fob_excl_input.text())
        data["freight"] = try_float(self.freight_input.text())
        data["packing_fee"] = try_float(self.packing_fee_input.text())
        data["carton_length_cm"] = try_float(self.carton_length_input.text())
        data["carton_width_cm"] = try_float(self.carton_width_input.text())
        data["carton_height_cm"] = try_float(self.carton_height_input.text())
        data["units_per_carton"] = int(self.units_input.text()) if self.units_input.text().strip() else None
        data["gross_weight_kg"] = try_float(self.gross_weight_input.text())
        data["weight_kg"] = try_float(self.weight_input.text())

        # 打印完整数据用于调试
        print(f"DEBUG - 准备保存数据: {data}")

        # 创建加载对话框
        from PySide6.QtWidgets import QProgressDialog
        progress = QProgressDialog("正在保存产品...", "取消", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None)
        progress.show()
        
        # 使用QTimer延迟执行保存操作，避免UI冻结
        def do_save():
            try:
                # 如果有选择图片，先上传图片
                if self.selected_image_path:
                    print(f"DEBUG - 准备上传图片: {self.selected_image_path}")
                    try:
                        image_url = self.api_client.upload_image(self.selected_image_path)
                        print(f"DEBUG - 图片上传结果: {image_url}")
                        if image_url:
                            data["default_image_url"] = image_url
                            print(f"DEBUG - 设置 default_image_url: {image_url}")
                        else:
                            print("DEBUG - 图片上传失败，返回None")
                    except Exception as e:
                        print(f"DEBUG - 图片上传异常: {str(e)}")
                        QMessageBox.warning(self, "警告", f"图片上传失败: {str(e)}")
                
                if self.is_edit:
                    print(f"DEBUG - 编辑产品，ID: {self.product.get('id')}")
                    self.api_client.update_product(self.product.get('id'), data)
                    print("DEBUG - 产品更新成功")
                    # 如果是编辑且有新图片，关联图片到产品
                    if self.selected_image_path and 'default_image_url' in data:
                        self.api_client.set_product_default_image(self.product.get('id'), data['default_image_url'])
                    QMessageBox.information(self, "成功", "产品信息已更新")
                else:
                    print("DEBUG - 创建新产品")
                    print(f"DEBUG - 请求数据: {data}")
                    result = self.api_client.create_product(data)
                    print(f"DEBUG - 创建结果: {result}")
                    # 如果是新建且有图片，关联图片到产品
                    if self.selected_image_path and result and 'id' in result:
                        self.api_client.set_product_default_image(result['id'], data.get('default_image_url'))
                    QMessageBox.information(self, "成功", "产品创建成功")
                progress.close()
                self.accept()
            except Exception as e:
                print(f"DEBUG - 保存产品失败: {str(e)}")
                progress.close()
                QMessageBox.warning(self, "错误", f"保存产品失败: {str(e)}")
        
        QTimer.singleShot(100, do_save)

class CustomerDialog(QDialog):
    def __init__(self, api_client: ApiClient, customer=None):
        super().__init__()
        self.api_client = api_client
        self.customer = customer
        self.is_edit = customer is not None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑客户" if self.is_edit else "新增客户")
        self.setMinimumSize(550, 550)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.dept_combo = QComboBox()
        self.dept_combo.addItems([
            "S - 索英普",
            "W - 维那",
            "M - 马迪那",
            "D - 银达"
        ])
        form_layout.addRow("部门:", self.dept_combo)

        if self.is_edit:
            self.code_label = QLabel(self.customer.get('customer_code', ''))
            form_layout.addRow("客户编号:", self.code_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入客户名称")
        if self.customer:
            self.name_input.setText(self.customer.get('customer_name', ''))
        form_layout.addRow("客户名称 *:", self.name_input)

        self.country_input = QLineEdit()
        self.country_input.setPlaceholderText("请输入所在国家")
        if self.customer:
            self.country_input.setText(self.customer.get('country', ''))
        form_layout.addRow("所在国家 *:", self.country_input)

        self.basic_require_input = QTextEdit()
        self.basic_require_input.setPlaceholderText("请输入通用交易条款")
        self.basic_require_input.setMaximumHeight(60)
        if self.customer:
            self.basic_require_input.setText(self.customer.get('basic_require', ''))
        form_layout.addRow("基本要求:", self.basic_require_input)

        self.special_input = QTextEdit()
        self.special_input.setPlaceholderText("请输入特殊要求，如特定包装、标签等")
        self.special_input.setMaximumHeight(60)
        if self.customer:
            self.special_input.setText(self.customer.get('special_require', ''))
        form_layout.addRow("特殊要求:", self.special_input)

        self.payment_input = QLineEdit()
        self.payment_input.setPlaceholderText("如 T/T 30天")
        if self.customer:
            self.payment_input.setText(self.customer.get('payment_terms', ''))
        form_layout.addRow("付款条款:", self.payment_input)

        contact_group = QGroupBox("联系人信息")
        contact_layout = QFormLayout()
        contact_layout.setSpacing(10)

        self.contact_name_input = QLineEdit()
        self.contact_name_input.setPlaceholderText("联系人姓名")
        if self.customer:
            self.contact_name_input.setText(self.customer.get('contact_name', ''))
        contact_layout.addRow("姓名:", self.contact_name_input)

        self.contact_phone_input = QLineEdit()
        self.contact_phone_input.setPlaceholderText("电话")
        if self.customer:
            self.contact_phone_input.setText(self.customer.get('contact_phone', ''))
        contact_layout.addRow("电话:", self.contact_phone_input)

        self.contact_email_input = QLineEdit()
        self.contact_email_input.setPlaceholderText("邮箱")
        if self.customer:
            self.contact_email_input.setText(self.customer.get('contact_email', ''))
        contact_layout.addRow("邮箱:", self.contact_email_input)

        contact_group.setLayout(contact_layout)
        layout.addLayout(form_layout)
        layout.addWidget(contact_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.save_customer)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def save_customer(self):
        print("save_customer called")  # 调试信息
        print(f"is_edit: {self.is_edit}")  # 调试信息
        print(f"customer: {self.customer}")  # 调试信息
        
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入客户名称")
            return
        if not self.country_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入所在国家")
            return

        dept_map = {"S - 索英普": "S", "W - 维那": "W", "M - 马迪那": "M", "D - 银达": "D"}
        dept_id = dept_map.get(self.dept_combo.currentText(), "S")

        data = {
            "dept_id": dept_id,
            "customer_name": self.name_input.text().strip(),
            "country": self.country_input.text().strip(),
            "basic_require": self.basic_require_input.toPlainText().strip(),
            "special_require": self.special_input.toPlainText().strip(),
            "payment_terms": self.payment_input.text().strip()
        }

        print(f"准备保存数据: {data}")  # 调试信息

        contact_name = self.contact_name_input.text().strip()
        contact_phone = self.contact_phone_input.text().strip()
        contact_email = self.contact_email_input.text().strip()
        if contact_name or contact_phone or contact_email:
            data["contacts"] = [{
                "name": contact_name,
                "phone": contact_phone,
                "email": contact_email,
                "is_primary": 1
            }]

        try:
            print(f"调用API: {'update' if self.is_edit else 'create'}")  # 调试信息
            if self.is_edit:
                customer_id = self.customer.get('id', 'NOT_FOUND')
                print(f"更新客户ID: {customer_id}")  # 调试信息
                result = self.api_client.update_customer(customer_id, data)
                print(f"API返回结果: {result}")  # 调试信息
            else:
                result = self.api_client.create_customer(data)
                print(f"API返回结果: {result}")  # 调试信息
            print("API调用成功")  # 调试信息
            self.accept()
        except Exception as e:
            print(f"API调用失败: {str(e)}")  # 调试信息
            QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")
            traceback.print_exc()


class CustomerDetailDialog(QDialog):
    def __init__(self, api_client: ApiClient, customer):
        super().__init__()
        self.api_client = api_client
        self.customer = customer
        self.addresses = []
        self.contacts = []
        self.pi_orders = []
        self.init_ui()
        self.load_data()

    def init_ui(self):
        self.setWindowTitle(f"客户详情 - {self.customer.get('customer_name', '')}")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # 标签页
        self.tab_widget = QTabWidget()
        
        # 基本信息页
        self.basic_tab = QWidget()
        self.setup_basic_tab()
        
        # 收货地址页
        self.address_tab = QWidget()
        self.setup_address_tab()
        
        # 联系人页
        self.contact_tab = QWidget()
        self.setup_contact_tab()
        
        # PI订单历史页
        self.pi_tab = QWidget()
        self.setup_pi_tab()

        self.tab_widget.addTab(self.basic_tab, "基本信息")
        self.tab_widget.addTab(self.address_tab, "收货地址")
        self.tab_widget.addTab(self.contact_tab, "联系人")
        self.tab_widget.addTab(self.pi_tab, "交易历史")

        layout.addWidget(self.tab_widget)

        # 关闭按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def setup_basic_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        form_layout.addRow(QLabel("<b>客户编号:</b>"), QLabel(self.customer.get('customer_code', '')))
        form_layout.addRow(QLabel("<b>客户名称:</b>"), QLabel(self.customer.get('customer_name', '')))
        form_layout.addRow(QLabel("<b>所属部门:</b>"), QLabel(self.customer.get('dept_id', '')))
        form_layout.addRow(QLabel("<b>所在国家:</b>"), QLabel(self.customer.get('country', '')))
        
        basic_require = self.customer.get('basic_require', '')
        form_layout.addRow(QLabel("<b>基本要求:</b>"), QLabel(basic_require if basic_require else "-"))
        
        form_layout.addRow(QLabel("<b>付款条款:</b>"), QLabel(self.customer.get('payment_terms', '') or "-"))
        
        status = self.customer.get('status', 1)
        status_text = "启用" if status == 1 else "禁用"
        status_color = "#10b981" if status == 1 else "#ef4444"
        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
        form_layout.addRow(QLabel("<b>状态:</b>"), status_label)

        layout.addLayout(form_layout)
        layout.addStretch()

        special_require = self.customer.get('special_require', '')
        if special_require:
            special_group = QGroupBox("特殊要求")
            special_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #dc2626; border-radius: 5px; }")
            special_layout = QVBoxLayout()
            special_label = QLabel(special_require)
            special_label.setWordWrap(True)
            special_label.setStyleSheet("color: #dc2626; padding: 5px;")
            special_layout.addWidget(special_label)
            special_group.setLayout(special_layout)
            layout.addWidget(special_group)

        self.basic_tab.setLayout(layout)

    def setup_address_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # 工具栏
        toolbar = QHBoxLayout()
        add_btn = QPushButton("+ 添加地址")
        add_btn.clicked.connect(self.add_address)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        toolbar.addWidget(add_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 地址列表
        self.addresses_table = QTableWidget()
        self.addresses_table.setColumnCount(5)
        self.addresses_table.setHorizontalHeaderLabels(["国家", "港口", "详细地址", "默认地址", "操作"])
        self.addresses_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.addresses_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.addresses_table)

        self.address_tab.setLayout(layout)

    def setup_contact_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.addStretch()
        
        add_btn = QPushButton("+ 新增联系人")
        add_btn.clicked.connect(self.add_contact)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        toolbar.addWidget(add_btn)
        
        layout.addLayout(toolbar)

        self.contacts_table = QTableWidget()
        self.contacts_table.setColumnCount(6)
        self.contacts_table.setHorizontalHeaderLabels(["姓名", "职位", "电话", "邮箱", "是否主要", "操作"])
        self.contacts_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.contacts_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.contacts_table)

        self.contact_tab.setLayout(layout)

    def setup_pi_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        self.pi_table = QTableWidget()
        self.pi_table.setColumnCount(4)
        self.pi_table.setHorizontalHeaderLabels(["PI号", "总金额", "状态", "创建时间"])
        self.pi_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.pi_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.pi_table)

        self.pi_tab.setLayout(layout)

    def load_data(self):
        try:
            # 加载地址
            self.addresses = self.api_client.get_customer_addresses(self.customer['id'])
            self.load_addresses_table()

            # 加载联系人
            self.contacts = self.api_client.get_customer_contacts(self.customer['id'])
            self.load_contacts_table()

            # 加载PI订单
            self.pi_orders = self.api_client.get_customer_pi_list(self.customer['id'])
            self.load_pi_table()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载数据失败: {str(e)}")

    def load_addresses_table(self):
        self.addresses_table.setRowCount(len(self.addresses))
        for row, addr in enumerate(self.addresses):
            self.addresses_table.setItem(row, 0, QTableWidgetItem(addr.get('country', '')))
            self.addresses_table.setItem(row, 1, QTableWidgetItem(addr.get('port', '')))
            self.addresses_table.setItem(row, 2, QTableWidgetItem(addr.get('address_detail', '')))
            
            is_default = addr.get('is_default', 0)
            default_text = "是" if is_default == 1 else "否"
            self.addresses_table.setItem(row, 3, QTableWidgetItem(default_text))

            # 操作按钮
            btn_layout = QHBoxLayout()
            
            edit_btn = QPushButton("编辑")
            edit_btn.setFixedWidth(45)
            edit_btn.clicked.connect(lambda _, addr=addr: self.edit_address(addr))
            btn_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("删除")
            delete_btn.setFixedWidth(45)
            delete_btn.setStyleSheet("color: #dc2626;")
            delete_btn.clicked.connect(lambda _, addr=addr: self.delete_address(addr))
            btn_layout.addWidget(delete_btn)

            btn_widget = QWidget()
            btn_widget.setLayout(btn_layout)
            self.addresses_table.setCellWidget(row, 4, btn_widget)

    def load_contacts_table(self):
        self.contacts_table.setRowCount(len(self.contacts))
        for row, contact in enumerate(self.contacts):
            self.contacts_table.setItem(row, 0, QTableWidgetItem(contact.get('name', '')))
            self.contacts_table.setItem(row, 1, QTableWidgetItem(contact.get('position', '')))
            self.contacts_table.setItem(row, 2, QTableWidgetItem(contact.get('phone', '')))
            self.contacts_table.setItem(row, 3, QTableWidgetItem(contact.get('email', '')))
            
            is_primary = contact.get('is_primary', 0)
            primary_text = "是" if is_primary == 1 else "否"
            self.contacts_table.setItem(row, 4, QTableWidgetItem(primary_text))

            # 操作按钮
            btn_layout = QHBoxLayout()
            
            edit_btn = QPushButton("编辑")
            edit_btn.setFixedWidth(45)
            edit_btn.clicked.connect(lambda _, c=contact: self.edit_contact(c))
            btn_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("删除")
            delete_btn.setFixedWidth(45)
            delete_btn.setStyleSheet("color: #dc2626;")
            delete_btn.clicked.connect(lambda _, c=contact: self.delete_contact(c))
            btn_layout.addWidget(delete_btn)

            btn_widget = QWidget()
            btn_widget.setLayout(btn_layout)
            self.contacts_table.setCellWidget(row, 5, btn_widget)

    def load_pi_table(self):
        self.pi_table.setRowCount(len(self.pi_orders))
        for row, pi in enumerate(self.pi_orders):
            self.pi_table.setItem(row, 0, QTableWidgetItem(pi.get('pi_number', '')))
            self.pi_table.setItem(row, 1, QTableWidgetItem(str(pi.get('total_amount', ''))))
            
            status = pi.get('status', '')
            self.pi_table.setItem(row, 2, QTableWidgetItem(status))
            
            created_at = pi.get('created_at', '')
            if created_at:
                created_at = created_at[:19] if isinstance(created_at, str) else str(created_at)
            self.pi_table.setItem(row, 3, QTableWidgetItem(created_at))

    def add_address(self):
        dialog = AddressDialog(self.api_client, customer_id=self.customer['id'])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def edit_address(self, address):
        dialog = AddressDialog(self.api_client, customer_id=self.customer['id'], address=address)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def delete_address(self, address):
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个地址吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.api_client.delete_customer_address(self.customer['id'], address['id'])
                self.load_data()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败：{str(e)}")

    def add_contact(self):
        dialog = ContactDialog(self.api_client, customer_id=self.customer['id'])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def edit_contact(self, contact):
        dialog = ContactDialog(self.api_client, customer_id=self.customer['id'], contact=contact)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def delete_contact(self, contact):
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个联系人吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.api_client.delete_customer_contact(self.customer['id'], contact['id'])
                self.load_data()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败：{str(e)}")


class AddressDialog(QDialog):
    def __init__(self, api_client: ApiClient, customer_id, address=None):
        super().__init__()
        self.api_client = api_client
        self.customer_id = customer_id
        self.address = address
        self.is_edit = address is not None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑地址" if self.is_edit else "添加地址")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.country_input = QLineEdit()
        if self.address:
            self.country_input.setText(self.address.get('country', ''))
        form_layout.addRow("国家:", self.country_input)

        self.port_input = QLineEdit()
        if self.address:
            self.port_input.setText(self.address.get('port', ''))
        form_layout.addRow("港口:", self.port_input)

        self.detail_input = QTextEdit()
        if self.address:
            self.detail_input.setText(self.address.get('address_detail', ''))
        self.detail_input.setMaximumHeight(80)
        form_layout.addRow("详细地址:", self.detail_input)

        self.default_checkbox = QCheckBox("设为默认地址")
        if self.address and self.address.get('is_default', 0) == 1:
            self.default_checkbox.setChecked(True)
        form_layout.addRow("", self.default_checkbox)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.save_address)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def save_address(self):
        data = {
            "country": self.country_input.text().strip(),
            "port": self.port_input.text().strip(),
            "address_detail": self.detail_input.toPlainText().strip(),
            "is_default": 1 if self.default_checkbox.isChecked() else 0
        }

        try:
            if self.is_edit:
                self.api_client.update_customer_address(self.customer_id, self.address['id'], data)
            else:
                self.api_client.create_customer_address(self.customer_id, data)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败：{str(e)}")


class ContactDialog(QDialog):
    def __init__(self, api_client: ApiClient, customer_id, contact=None):
        super().__init__()
        self.api_client = api_client
        self.customer_id = customer_id
        self.contact = contact
        self.is_edit = contact is not None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑联系人" if self.is_edit else "添加联系人")
        self.setFixedSize(400, 350)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.name_input = QLineEdit()
        if self.contact:
            self.name_input.setText(self.contact.get('name', ''))
        form_layout.addRow("姓名:", self.name_input)

        self.position_input = QLineEdit()
        if self.contact:
            self.position_input.setText(self.contact.get('position', ''))
        form_layout.addRow("职位:", self.position_input)

        self.phone_input = QLineEdit()
        if self.contact:
            self.phone_input.setText(self.contact.get('phone', ''))
        form_layout.addRow("电话:", self.phone_input)

        self.email_input = QLineEdit()
        if self.contact:
            self.email_input.setText(self.contact.get('email', ''))
        form_layout.addRow("邮箱:", self.email_input)

        self.primary_checkbox = QCheckBox("设为主要联系人")
        if self.contact and self.contact.get('is_primary', 0) == 1:
            self.primary_checkbox.setChecked(True)
        form_layout.addRow("", self.primary_checkbox)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.save_contact)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def save_contact(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入联系人姓名")
            return

        data = {
            "name": self.name_input.text().strip(),
            "position": self.position_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "email": self.email_input.text().strip(),
            "is_primary": 1 if self.primary_checkbox.isChecked() else 0
        }

        try:
            if self.is_edit:
                self.api_client.update_customer_contact(self.customer_id, self.contact['id'], data)
            else:
                self.api_client.create_customer_contact(self.customer_id, data)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败：{str(e)}")


class SupplierDialog(QDialog):
    def __init__(self, api_client: ApiClient, supplier=None):
        super().__init__()
        self.api_client = api_client
        self.supplier = supplier
        self.is_edit = supplier is not None
        self.provinces = []
        self.cities = []
        self.selected_city_code = ""
        self.init_ui()
        QTimer.singleShot(0, self.load_provinces)

    def load_provinces(self):
        try:
            self.provinces = self.api_client.get_provinces()
            self.province_combo.clear()
            self.province_combo.addItems(self.provinces)
            if self.supplier and self.supplier.get('region'):
                region = self.supplier.get('region', '')
                for prov in self.provinces:
                    if region.startswith(prov):
                        self.province_combo.setCurrentText(prov)
                        self.load_cities(prov)
                        city_name = region[len(prov):].strip()
                        if city_name and city_name in self.cities:
                            self.city_combo.setCurrentText(city_name)
                        break
        except Exception as e:
            print(f"加载省份失败: {e}")

    def load_cities(self, province):
        try:
            self.cities = self.api_client.get_cities(province)
            self.city_combo.clear()
            self.city_combo.addItems(self.cities)
        except Exception as e:
            print(f"加载城市失败: {e}")

    def on_province_changed(self, province):
        self.load_cities(province)

    def on_city_changed(self, city):
        province = self.province_combo.currentText()
        try:
            # 使用模块级别的静态映射（只创建一次）
            p_code = PROVINCE_CODE_MAP.get(province, "")
            c_map = CITY_CODE_MAP.get(p_code, {})
            self.selected_city_code = p_code + c_map.get(city, "0")
        except Exception as e:
            print(f"获取城市编码失败: {e}")

    def init_ui(self):
        self.setWindowTitle("编辑供应商" if self.is_edit else "新增供应商")
        self.setFixedSize(500, 480)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        if self.is_edit:
            self.code_label = QLabel(self.supplier.get('supplier_code', ''))
            form_layout.addRow("供应商编号:", self.code_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入供应商名称")
        if self.supplier:
            self.name_input.setText(self.supplier.get('supplier_name', ''))
        form_layout.addRow("供应商名称:", self.name_input)

        province_layout = QHBoxLayout()
        self.province_combo = QComboBox()
        self.province_combo.setFixedHeight(35)
        self.province_combo.currentTextChanged.connect(self.on_province_changed)
        province_layout.addWidget(self.province_combo)

        self.city_combo = QComboBox()
        self.city_combo.setFixedHeight(35)
        self.city_combo.currentTextChanged.connect(self.on_city_changed)
        province_layout.addWidget(self.city_combo)
        form_layout.addRow("省份/城市:", province_layout)

        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("请输入联系人")
        if self.supplier:
            self.contact_input.setText(self.supplier.get('contact_person', ''))
        form_layout.addRow("联系人:", self.contact_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("请输入联系电话")
        if self.supplier:
            self.phone_input.setText(self.supplier.get('phone', ''))
        form_layout.addRow("联系电话:", self.phone_input)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("请输入邮箱地址")
        if self.supplier:
            self.email_input.setText(self.supplier.get('email', ''))
        form_layout.addRow("邮箱:", self.email_input)

        self.address_input = QTextEdit()
        self.address_input.setPlaceholderText("请输入详细地址")
        if self.supplier:
            self.address_input.setText(self.supplier.get('address', ''))
        self.address_input.setMaximumHeight(80)
        form_layout.addRow("详细地址:", self.address_input)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.save_supplier)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def save_supplier(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入供应商名称")
            return

        province = self.province_combo.currentText()
        city = self.city_combo.currentText()
        region = f"{province} {city}" if province and city else ""

        data = {
            "supplier_name": self.name_input.text().strip(),
            "province": province,
            "city": city,
            "city_code": self.selected_city_code,
            "region": region,
            "contact_person": self.contact_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "email": self.email_input.text().strip(),
            "address": self.address_input.toPlainText().strip()
        }

        try:
            if self.is_edit:
                self.api_client.update_supplier(self.supplier['id'], data)
            else:
                self.api_client.create_supplier(data)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")


class MainWindow(QMainWindow):
    def __init__(self, api_client: ApiClient, dept_id: str):
        super().__init__()
        self.api_client = api_client
        self.dept_id = dept_id
        self.init_ui()
        self.load_data()

    def init_ui(self):
        self.setWindowTitle(f"PI订单管理系统 - {DEPARTMENT_CONFIG[self.dept_id]['name']}")
        self.setMinimumSize(1200, 800)
        # 默认全屏显示
        self.showMaximized()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        header = QWidget()
        header.setFixedHeight(70)
        header.setStyleSheet("background-color: #2563eb;")
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel(f"📦 PI订单管理系统 - {DEPARTMENT_CONFIG[self.dept_id]['name']}")
        title.setFont(get_font(16, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # 用户信息和管理员模式切换
        self.user_info_label = QLabel()
        self.user_info_label.setStyleSheet("color: white; font-size: 14px;")
        header_layout.addWidget(self.user_info_label)
        
        self.admin_mode_label = QLabel()
        self.admin_mode_label.setStyleSheet("color: #fbbf24; font-size: 12px; font-weight: bold;")
        header_layout.addWidget(self.admin_mode_label)
        
        # 退出登录按钮
        logout_btn = QPushButton("退出")
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
        """)
        logout_btn.clicked.connect(self.logout)
        header_layout.addWidget(logout_btn)

        header.setLayout(header_layout)
        main_layout.addWidget(header)

        content = QWidget()
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)

        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background-color: #1e293b;")
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(0, 20, 0, 0)
        sidebar_layout.setSpacing(5)

        self.tab_buttons = {}
        tabs = [
            ("产品管理", "products"),
            ("客户管理", "customers"),
            ("供应商管理", "suppliers"),
            ("PI管理", "pi"),
            ("采购管理", "purchase")
        ]

        for name, key in tabs:
            btn = QPushButton(name)
            btn.setFixedHeight(45)
            btn.setFont(get_font(10))
            btn.setStyleSheet("""
                QPushButton {
                    color: white;
                    background-color: transparent;
                    border: none;
                    text-align: left;
                    padding-left: 20px;
                }
                QPushButton:hover {
                    background-color: #334155;
                }
                QPushButton:checked {
                    background-color: #2563eb;
                }
            """)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self.switch_tab(k))
            sidebar_layout.addWidget(btn)
            self.tab_buttons[key] = btn

        self.tab_buttons["products"].setChecked(True)

        sidebar_layout.addStretch()
        sidebar.setLayout(sidebar_layout)
        content_layout.addWidget(sidebar)

        self.content_stack = QStackedWidget()

        self.products_widget = self.create_products_tab()
        self.customers_widget = self.create_customers_tab()
        self.suppliers_widget = self.create_suppliers_tab()
        self.pi_widget = self.create_pi_tab()
        self.purchase_widget = self.create_purchase_tab()

        self.content_stack.addWidget(self.products_widget)
        self.content_stack.addWidget(self.customers_widget)
        self.content_stack.addWidget(self.suppliers_widget)
        self.content_stack.addWidget(self.pi_widget)
        self.content_stack.addWidget(self.purchase_widget)

        content_layout.addWidget(self.content_stack)
        content.setLayout(content_layout)
        main_layout.addWidget(content)

        central_widget.setLayout(main_layout)

    def switch_tab(self, key):
        tab_map = {"products": 0, "customers": 1, "suppliers": 2, "pi": 3, "purchase": 4}
        self.content_stack.setCurrentIndex(tab_map.get(key, 0))
        for k, btn in self.tab_buttons.items():
            btn.setChecked(k == key)

    def create_products_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        toolbar = QHBoxLayout()
        
        title = QLabel("产品列表")
        title.setFont(get_font(14, QFont.Weight.Bold))
        toolbar.addWidget(title)
        
        toolbar.addStretch()

        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索（OE号/产品编号/工厂编号/品牌/描述）")
        self.search_input.setFixedWidth(250)
        search_layout.addWidget(self.search_input)

        self.category_filter = QComboBox()
        self.category_filter.addItem("全部分类", 0)
        search_layout.addWidget(self.category_filter)
        
        # 加载产品类别
        self.load_product_categories()

        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.search_products)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        search_layout.addWidget(search_btn)

        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.reset_search)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        search_layout.addWidget(reset_btn)

        toolbar.addLayout(search_layout)

        add_btn = QPushButton("+ 新增产品")
        add_btn.clicked.connect(self.add_product)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        toolbar.addWidget(add_btn)

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_products)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        toolbar.addWidget(refresh_btn)

        import_btn = QPushButton("批量导入")
        import_btn.clicked.connect(self.import_products)
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        toolbar.addWidget(import_btn)

        # 批量操作按钮
        batch_layout = QHBoxLayout()
        batch_layout.setSpacing(10)
        
        self.select_all_checkbox = QCheckBox("全选")
        self.select_all_checkbox.stateChanged.connect(self.toggle_select_all_products)
        batch_layout.addWidget(self.select_all_checkbox)
        
        batch_disable_btn = QPushButton("批量禁用")
        batch_disable_btn.clicked.connect(self.batch_toggle_product_status)
        batch_disable_btn.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #d97706; }
        """)
        batch_layout.addWidget(batch_disable_btn)
        
        batch_delete_btn = QPushButton("批量删除")
        batch_delete_btn.clicked.connect(self.batch_delete_products)
        batch_delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #b91c1c; }
        """)
        batch_layout.addWidget(batch_delete_btn)
        
        # 批量确认导入按钮
        batch_confirm_import_btn = QPushButton("批量确认导入")
        batch_confirm_import_btn.clicked.connect(self.batch_confirm_import_products)
        batch_confirm_import_btn.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #d97706; }
        """)
        batch_layout.addWidget(batch_confirm_import_btn)
        
        toolbar.addLayout(batch_layout)

        layout.addLayout(toolbar)

        self.products_table = QTableWidget()
        self.products_table.setColumnCount(11)
        self.products_table.setHorizontalHeaderLabels(["选择", "图片", "ID", "工厂编号", "OE号", "品牌", "每箱数量", "单价", "状态", "操作", "产品编号"])
        self.products_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.products_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # 设置图片列宽度和行高
        self.products_table.setColumnWidth(1, 70)
        self.products_table.verticalHeader().setDefaultSectionSize(70)
        # 默认隐藏产品编号列（最后一列）
        self.products_table.setColumnHidden(10, True)
        self.products_table.doubleClicked.connect(self.on_product_double_click)
        layout.addWidget(self.products_table)

        widget.setLayout(layout)
        return widget

    def create_customers_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        toolbar = QHBoxLayout()
        title = QLabel("客户列表")
        title.setFont(get_font(14, QFont.Weight.Bold))
        toolbar.addWidget(title)
        toolbar.addStretch()

        self.customer_select_all_checkbox = QCheckBox("全选")
        self.customer_select_all_checkbox.clicked.connect(self.toggle_select_all_customers)
        toolbar.addWidget(self.customer_select_all_checkbox)

        self.customer_search_input = QLineEdit()
        self.customer_search_input.setPlaceholderText("搜索客户名称/编号...")
        self.customer_search_input.setFixedWidth(200)
        self.customer_search_input.returnPressed.connect(self.search_customers)
        toolbar.addWidget(self.customer_search_input)

        self.customer_country_filter = QComboBox()
        self.customer_country_filter.addItem("全部国家", 0)
        self.customer_country_filter.setFixedWidth(150)
        toolbar.addWidget(self.customer_country_filter)

        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.search_customers)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        toolbar.addWidget(search_btn)

        add_btn = QPushButton("+ 新增客户")
        add_btn.clicked.connect(self.add_customer)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        toolbar.addWidget(add_btn)

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_customers)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        self.customers_table = QTableWidget()
        self.customers_table.setColumnCount(8)
        self.customers_table.setHorizontalHeaderLabels(["选择", "ID", "客户编号", "客户名称", "国家", "付款条款", "状态", "操作"])
        self.customers_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.customers_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.customers_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.customers_table.doubleClicked.connect(self.on_customer_double_click)
        layout.addWidget(self.customers_table)

        widget.setLayout(layout)
        return widget

    def create_suppliers_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        toolbar = QHBoxLayout()
        title = QLabel("供应商列表")
        title.setFont(get_font(14, QFont.Weight.Bold))
        toolbar.addWidget(title)
        toolbar.addStretch()

        self.select_all_checkbox = QCheckBox("全选")
        self.select_all_checkbox.clicked.connect(self.toggle_select_all_suppliers)
        toolbar.addWidget(self.select_all_checkbox)

        delete_btn = QPushButton("删除选中")
        delete_btn.clicked.connect(self.delete_selected_suppliers)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #b91c1c; }
        """)
        toolbar.addWidget(delete_btn)

        import_btn = QPushButton("批量导入")
        import_btn.clicked.connect(self.import_suppliers)
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: #16a34a;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #15803d; }
        """)
        toolbar.addWidget(import_btn)

        add_btn = QPushButton("+ 新增供应商")
        add_btn.clicked.connect(self.add_supplier)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        toolbar.addWidget(add_btn)

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_suppliers)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        self.suppliers_table = QTableWidget()
        self.suppliers_table.setColumnCount(8)
        self.suppliers_table.setHorizontalHeaderLabels(["", "ID", "供应商编号", "供应商名称", "地区", "联系人", "电话", "操作"])
        self.suppliers_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.suppliers_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.suppliers_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.suppliers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.suppliers_table.setColumnWidth(0, 40)
        self.suppliers_table.doubleClicked.connect(self.on_supplier_double_click)
        layout.addWidget(self.suppliers_table)

        widget.setLayout(layout)
        return widget

    def toggle_select_all_suppliers(self, checked):
        for row in range(self.suppliers_table.rowCount()):
            checkbox = self.suppliers_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(checked)

    def delete_selected_suppliers(self):
        selected_ids = []
        for row in range(self.suppliers_table.rowCount()):
            checkbox = self.suppliers_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                supplier_id = int(self.suppliers_table.item(row, 1).text())
                selected_ids.append(supplier_id)

        if not selected_ids:
            QMessageBox.warning(self, "提示", "请先选择要删除的供应商")
            return

        reply = QMessageBox.question(self, "确认删除", f"确定要删除选中的 {len(selected_ids)} 个供应商吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        for supplier_id in selected_ids:
            try:
                self.api_client.delete_supplier(supplier_id)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除供应商失败: {str(e)}")

        self.load_suppliers()
        self.select_all_checkbox.setChecked(False)

    def create_pi_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        toolbar = QHBoxLayout()
        title = QLabel("PI订单列表")
        title.setFont(get_font(14, QFont.Weight.Bold))
        toolbar.addWidget(title)
        toolbar.addStretch()

        add_btn = QPushButton("+ 新建PI")
        add_btn.clicked.connect(self.add_pi)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        toolbar.addWidget(add_btn)

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_pi_orders)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        self.pi_table = QTableWidget()
        self.pi_table.setColumnCount(5)
        self.pi_table.setHorizontalHeaderLabels(["ID", "PI号", "金额(USD)", "状态", "创建时间"])
        self.pi_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.pi_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.pi_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.pi_table)

        widget.setLayout(layout)
        return widget

    def create_purchase_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        toolbar = QHBoxLayout()
        title = QLabel("采购订单列表")
        title.setFont(get_font(14, QFont.Weight.Bold))
        toolbar.addWidget(title)
        toolbar.addStretch()

        add_btn = QPushButton("+ 新建采购单")
        add_btn.clicked.connect(self.add_purchase)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        toolbar.addWidget(add_btn)

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_purchase_orders)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        self.purchase_table = QTableWidget()
        self.purchase_table.setColumnCount(6)
        self.purchase_table.setHorizontalHeaderLabels(["ID", "采购单号", "PI号", "供应商", "金额", "状态"])
        self.purchase_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.purchase_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.purchase_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.purchase_table)

        widget.setLayout(layout)
        return widget

    def load_data(self):
        # 更新用户信息显示
        self.update_user_info()
        
        self.load_products()
        self.load_customers()
        self.load_suppliers()
        self.load_pi_orders()
        self.load_purchase_orders()
    
    def update_user_info(self):
        """更新用户信息显示"""
        if hasattr(self.api_client, 'current_user') and self.api_client.current_user:
            user = self.api_client.current_user
            self.user_info_label.setText(f"👤 {user.get('real_name', '用户')}")
            
            if user.get('is_admin'):
                self.admin_mode_label.setText("🔑 管理员模式")
            else:
                self.admin_mode_label.setText("👤 普通用户")
        else:
            self.user_info_label.setText("👤 未登录")
            self.admin_mode_label.setText("")
    
    def logout(self):
        """退出登录"""
        reply = QMessageBox.question(
            self, 
            "确认退出", 
            "确定要退出登录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self.api_client, 'logout'):
                self.api_client.logout()
            self.close()

    def load_products(self):
        try:
            products = self.api_client.get_products()
            self.products_table.setRowCount(len(products))
            for row, p in enumerate(products):
                checkbox = QCheckBox()
                checkbox.setCheckState(Qt.CheckState.Unchecked)
                checkbox.setStyleSheet("margin-left: 50%;")
                self.products_table.setCellWidget(row, 0, checkbox)

                # 显示图片缩略图
                image_label = QLabel()
                image_label.setFixedSize(60, 60)
                image_label.setStyleSheet("border: 1px solid #e5e7eb;")
                image_label.setAlignment(Qt.AlignCenter)
                
                image_url = p.get('default_image_url')
                if image_url:
                    try:
                        image_data = urllib.request.urlopen(image_url).read()
                        image = QImage.fromData(image_data)
                        pixmap = QPixmap.fromImage(image).scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        image_label.setPixmap(pixmap)
                    except Exception as e:
                        image_label.setText("暂无图片")
                else:
                    image_label.setText("暂无图片")
                
                image_label.mousePressEvent = lambda event, p=p: self.view_product_images(p.get('id'))
                image_label.setCursor(Qt.PointingHandCursor)
                self.products_table.setCellWidget(row, 1, image_label)

                self.products_table.setItem(row, 2, QTableWidgetItem(str(p.get('id', ''))))
                self.products_table.setItem(row, 3, QTableWidgetItem(p.get('factory_code', '')))
                self.products_table.setItem(row, 4, QTableWidgetItem(p.get('oe_number', '')))
                self.products_table.setItem(row, 5, QTableWidgetItem(p.get('brand', '')))
                self.products_table.setItem(row, 6, QTableWidgetItem(str(p.get('units_per_carton', ''))))
                
                unit_price = p.get('fob_price_excl') or p.get('exw_price_excl') or ''
                self.products_table.setItem(row, 7, QTableWidgetItem(str(unit_price)))
                
                status = p.get('status', 1)
                status_text = "启用" if status == 1 else "禁用"
                status_color = "#10b981" if status == 1 else "#ef4444"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(QBrush(QColor(status_color)))
                self.products_table.setItem(row, 8, status_item)

                # 创建操作栏
                is_imported = p.get('is_imported', 0) == 1
                is_admin = False
                if hasattr(self.api_client, 'current_user') and self.api_client.current_user:
                    is_admin = self.api_client.current_user.get('is_admin', False)
                
                # DEBUG日志
                print(f"DEBUG - Product {p.get('product_code')}: is_imported={p.get('is_imported')}, is_admin={is_admin}")
                
                def create_edit_callback(product):
                    return lambda: self.edit_product(product)
                
                def create_import_callback(product):
                    return lambda: self.confirm_product_import(product)
                
                def create_cancel_import_callback(product):
                    return lambda: self.cancel_product_import(product)
                
                action_bar = ActionBarFactory.create_product_action_bar(
                    edit_callback=create_edit_callback(p),
                    import_callback=create_import_callback(p),
                    cancel_import_callback=create_cancel_import_callback(p),
                    is_imported=is_imported,
                    is_admin=is_admin
                )
                self.products_table.setCellWidget(row, 9, action_bar)
                
                # 产品编号放在最后一列（默认隐藏）
                self.products_table.setItem(row, 10, QTableWidgetItem(p.get('product_code', '')))
                
            self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载产品数据失败: {str(e)}")

    def view_product_images(self, product):
        """查看产品图片"""
        product_id = product.get('id')
        product_code = product.get('product_code', '')
        image_url = product.get('default_image_url')
        
        if not image_url:
            QMessageBox.information(self, "图片查看", f"产品 {product_code} 暂无图片")
            return
        
        try:
            # 创建图片查看对话框
            dialog = QDialog(self)
            dialog.setWindowTitle(f"产品图片 - {product_code}")
            dialog.setMinimumSize(600, 600)
            
            layout = QVBoxLayout()
            
            # 图片标签
            image_label = QLabel()
            image_label.setAlignment(Qt.AlignCenter)
            
            # 加载图片
            image_data = urllib.request.urlopen(image_url).read()
            image = QImage.fromData(image_data)
            pixmap = QPixmap.fromImage(image).scaled(580, 580, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_label.setPixmap(pixmap)
            
            layout.addWidget(image_label)
            dialog.setLayout(layout)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载图片失败: {str(e)}")
    
    def confirm_product_import(self, product):
        """确认产品导入"""
        print(f"DEBUG - confirm_product_import called for product: {product.get('product_code')}")

        product_id = product.get('id')
        product_code = product.get('product_code', '')

        # 检查产品是否已经导入
        if product.get('is_imported') == 1:
            QMessageBox.warning(self, "提示", f"产品 {product_code} 已经确认导入，无需重复操作")
            return

        reply = QMessageBox.question(
            self, "确认导入",
            f"确定要确认产品 {product_code} 已导入吗？确认后将无法修改（普通用户）",
            QMessageBox.Ok | QMessageBox.Cancel
        )

        if reply == QMessageBox.Ok:
            try:
                print(f"DEBUG - Calling API to confirm import for product_id: {product_id}")
                result = self.api_client.confirm_product_import(product_id)
                print(f"DEBUG - API response: {result}")
                QMessageBox.information(self, "成功", "产品导入已确认")
                self.load_products()
            except Exception as e:
                print(f"DEBUG - Confirm import failed: {str(e)}")
                QMessageBox.warning(self, "错误", f"确认导入失败: {str(e)}")
    
    def cancel_product_import(self, product):
        """取消产品导入确认（仅管理员）"""
        print(f"DEBUG - cancel_product_import called for product: {product.get('product_code')}")
        
        product_id = product.get('id')
        product_code = product.get('product_code', '')
        
        reply = QMessageBox.question(
            self, "取消导入", 
            f"确定要取消产品 {product_code} 的导入确认吗？",
            QMessageBox.Ok | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Ok:
            try:
                print(f"DEBUG - Calling API to cancel import for product_id: {product_id}")
                result = self.api_client.cancel_product_import(product_id)
                print(f"DEBUG - API response: {result}")
                QMessageBox.information(self, "成功", "产品导入确认已取消")
                self.load_products()
            except Exception as e:
                print(f"DEBUG - Cancel import failed: {str(e)}")
                QMessageBox.warning(self, "错误", f"取消导入失败: {str(e)}")

    def batch_confirm_import_products(self):
        """批量确认产品导入"""
        print("DEBUG - batch_confirm_import_products called")
        
        selected_products = []
        already_imported = []
        
        # 获取选中的产品
        for row in range(self.products_table.rowCount()):
            checkbox = self.products_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                # 获取产品数据
                product_id = int(self.products_table.item(row, 2).text())
                product_code = self.products_table.item(row, 9)  # 产品编号在第10列（索引9）
                if not product_code:
                    product_code = self.products_table.item(row, 10).text()  # 或者从隐藏列获取
                else:
                    product_code = product_code.text()
                
                # 检查是否已导入（从数据源获取）
                # 这里需要重新获取产品数据来检查is_imported状态
                try:
                    product_detail = self.api_client.get_product_detail(product_id)
                    if product_detail.get('is_imported') == 1:
                        already_imported.append(product_code)
                    else:
                        selected_products.append({'id': product_id, 'code': product_code})
                except Exception as e:
                    print(f"DEBUG - Failed to get product detail for {product_id}: {str(e)}")
                    selected_products.append({'id': product_id, 'code': product_code})
        
        if not selected_products and not already_imported:
            QMessageBox.warning(self, "提示", "请先选择要确认导入的产品")
            return
        
        # 如果有已导入的产品，显示提示
        message = ""
        if already_imported:
            message = f"以下产品已确认导入，将跳过：\n{', '.join(already_imported)}\n\n"
        
        if not selected_products:
            QMessageBox.information(self, "提示", message + "没有需要确认导入的产品")
            return
        
        reply = QMessageBox.question(
            self, "批量确认导入",
            f"{message}确定要确认选中的 {len(selected_products)} 个产品已导入吗？\n确认后将无法修改（普通用户）",
            QMessageBox.Ok | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Ok:
            success_count = 0
            failed_count = 0
            failed_list = []
            
            for product in selected_products:
                try:
                    print(f"DEBUG - Calling API to confirm import for product_id: {product['id']}")
                    result = self.api_client.confirm_product_import(product['id'])
                    print(f"DEBUG - API response: {result}")
                    success_count += 1
                except Exception as e:
                    print(f"DEBUG - Confirm import failed for {product['code']}: {str(e)}")
                    failed_count += 1
                    failed_list.append(product['code'])
            
            # 显示结果
            result_msg = f"批量确认导入完成\n成功：{success_count} 个\n失败：{failed_count} 个"
            if failed_list:
                result_msg += f"\n失败产品：{', '.join(failed_list)}"
            
            QMessageBox.information(self, "批量确认导入结果", result_msg)
            self.load_products()

    def search_products(self):
        keyword = self.search_input.text().strip()
        category_id = self.category_filter.currentData()
        category_id = category_id if category_id != 0 else None
        
        try:
            # 搜索时显示产品编号列
            self.products_table.setColumnHidden(10, False)
            print(f"搜索参数 - 关键词: '{keyword}', 类别ID: {category_id}")
            products = self.api_client.search_products(keyword, category_id)
            print(f"搜索结果数量: {len(products)}")
            self.products_table.setRowCount(len(products))
            for row, p in enumerate(products):
                checkbox = QCheckBox()
                checkbox.setCheckState(Qt.CheckState.Unchecked)
                checkbox.setStyleSheet("margin-left: 50%;")
                self.products_table.setCellWidget(row, 0, checkbox)
                
                # 显示图片缩略图
                image_label = QLabel()
                image_label.setFixedSize(60, 60)
                image_label.setStyleSheet("border: 1px solid #e5e7eb;")
                image_label.setAlignment(Qt.AlignCenter)
                
                image_url = p.get('default_image_url')
                if image_url:
                    try:
                        image_data = urllib.request.urlopen(image_url).read()
                        image = QImage.fromData(image_data)
                        pixmap = QPixmap.fromImage(image).scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        image_label.setPixmap(pixmap)
                    except Exception as e:
                        image_label.setText("暂无图片")
                else:
                    image_label.setText("暂无图片")
                
                image_label.mousePressEvent = lambda event, p=p: self.view_product_images(p.get('id'))
                image_label.setCursor(Qt.PointingHandCursor)
                self.products_table.setCellWidget(row, 1, image_label)

                self.products_table.setItem(row, 2, QTableWidgetItem(str(p.get('id', ''))))
                self.products_table.setItem(row, 3, QTableWidgetItem(p.get('factory_code', '')))
                self.products_table.setItem(row, 4, QTableWidgetItem(p.get('oe_number', '')))
                self.products_table.setItem(row, 5, QTableWidgetItem(p.get('brand', '')))
                self.products_table.setItem(row, 6, QTableWidgetItem(str(p.get('units_per_carton', ''))))
                
                unit_price = p.get('fob_price_excl') or p.get('exw_price_excl') or ''
                self.products_table.setItem(row, 7, QTableWidgetItem(str(unit_price)))
                
                status = p.get('status', 1)
                status_text = "启用" if status == 1 else "禁用"
                status_color = "#10b981" if status == 1 else "#ef4444"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(QBrush(QColor(status_color)))
                self.products_table.setItem(row, 8, status_item)

                edit_btn = QPushButton("编辑")
                edit_btn.setFixedWidth(50)
                edit_btn.clicked.connect(lambda _, p=p: self.edit_product(p))
                self.products_table.setCellWidget(row, 9, edit_btn)
                
                # 产品编号放在最后一列（默认隐藏）
                self.products_table.setItem(row, 10, QTableWidgetItem(p.get('product_code', '')))
                
            self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        except Exception as e:
            print(f"搜索错误: {str(e)}")
            QMessageBox.warning(self, "错误", f"搜索产品失败: {str(e)}")

    def reset_search(self):
        self.search_input.clear()
        self.category_filter.setCurrentIndex(0)
        self.load_products()

    def load_product_categories(self):
        """从数据库加载产品类别"""
        try:
            categories = self.api_client.get("/product-categories")
            # 清空现有选项（保留"全部分类"）
            self.category_filter.clear()
            self.category_filter.addItem("全部分类", 0)
            for cat in categories:
                self.category_filter.addItem(cat.get('name', ''), cat.get('id', 0))
        except Exception as e:
            print(f"加载产品类别失败: {str(e)}")

    def toggle_select_all_products(self, state):
        for row in range(self.products_table.rowCount()):
            checkbox = self.products_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setCheckState(Qt.CheckState(state))

    def get_selected_product_ids(self):
        selected_ids = []
        for row in range(self.products_table.rowCount()):
            checkbox = self.products_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                id_item = self.products_table.item(row, 2)
                if id_item:
                    selected_ids.append(int(id_item.text()))
        return selected_ids

    def batch_toggle_product_status(self):
        selected_ids = self.get_selected_product_ids()
        if not selected_ids:
            QMessageBox.warning(self, "警告", "请先选择要操作的产品")
            return

        reply = QMessageBox.question(
            self, "确认操作", 
            f"确定要切换选中的 {len(selected_ids)} 个产品的状态吗？",
            QMessageBox.Ok | QMessageBox.Cancel
        )

        if reply == QMessageBox.Ok:
            try:
                for product_id in selected_ids:
                    self.api_client.update_product_status(product_id, None)
                QMessageBox.information(self, "成功", f"已成功切换 {len(selected_ids)} 个产品的状态")
                self.load_products()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"批量操作失败: {str(e)}")

    def batch_delete_products(self):
        selected_ids = self.get_selected_product_ids()
        if not selected_ids:
            QMessageBox.warning(self, "警告", "请先选择要删除的产品")
            return

        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除选中的 {len(selected_ids)} 个产品吗？此操作不可恢复！",
            QMessageBox.Ok | QMessageBox.Cancel
        )

        if reply == QMessageBox.Ok:
            try:
                for product_id in selected_ids:
                    self.api_client.delete_product(product_id)
                QMessageBox.information(self, "成功", f"已成功删除 {len(selected_ids)} 个产品")
                self.load_products()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"批量删除失败: {str(e)}")

    def view_product_images(self, product_id):
        try:
            images = self.api_client.get_product_images(product_id)
            
            if not images:
                QMessageBox.information(self, "提示", "该产品暂无图片")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle("产品图片")
            dialog.setMinimumSize(800, 600)
            
            layout = QVBoxLayout()
            
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            
            for i, image_data in enumerate(images, 1):
                image_url = image_data.get('image_url', '')
                if image_url:
                    try:
                        response = requests.get(image_url)
                        response.raise_for_status()
                        
                        pixmap = QPixmap()
                        pixmap.loadFromData(response.content)
                        
                        if not pixmap.isNull():
                            label = QLabel(f"图片 {i}")
                            label.setFont(get_font(12, QFont.Weight.Bold))
                            scroll_layout.addWidget(label)
                            
                            image_label = QLabel()
                            image_label.setPixmap(pixmap.scaled(700, 500, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            scroll_layout.addWidget(image_label)
                        else:
                            scroll_layout.addWidget(QLabel(f"图片 {i} 加载失败"))
                    except Exception as e:
                        scroll_layout.addWidget(QLabel(f"图片 {i} 加载失败: {str(e)}"))
            
            scroll_area.setWidget(scroll_content)
            layout.addWidget(scroll_area)
            
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)
            
            dialog.setLayout(layout)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取产品图片失败: {str(e)}")

    def load_customers(self):
        try:
            customers = self.api_client.get_customers()
            self.customers_table.setRowCount(len(customers))
            
            countries = sorted(set([c.get('country', '') for c in customers if c.get('country')]))
            current_country = self.customer_country_filter.currentText()
            self.customer_country_filter.clear()
            self.customer_country_filter.addItem("全部国家", 0)
            for country in countries:
                self.customer_country_filter.addItem(country, country)
            index = self.customer_country_filter.findText(current_country)
            if index >= 0:
                self.customer_country_filter.setCurrentIndex(index)
            
            for row, c in enumerate(customers):
                checkbox = QCheckBox()
                checkbox.setStyleSheet("margin-left: 50%;")
                self.customers_table.setCellWidget(row, 0, checkbox)
                
                self.customers_table.setItem(row, 1, QTableWidgetItem(str(c.get('id', ''))))
                self.customers_table.setItem(row, 2, QTableWidgetItem(c.get('customer_code', '')))
                self.customers_table.setItem(row, 3, QTableWidgetItem(c.get('customer_name', '')))
                self.customers_table.setItem(row, 4, QTableWidgetItem(c.get('country', '')))
                self.customers_table.setItem(row, 5, QTableWidgetItem(c.get('payment_terms', '')))
                
                status = c.get('status', 1)
                status_text = "启用" if status == 1 else "禁用"
                status_color = "#10b981" if status == 1 else "#ef4444"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(QBrush(QColor(status_color)))
                self.customers_table.setItem(row, 6, status_item)

                action_bar = ActionBarFactory.create_customer_action_bar(
                    edit_callback=lambda _, c=c: self.edit_customer(c),
                    toggle_callback=lambda _, c=c: self.toggle_customer_status(c),
                    status=status
                )
                self.customers_table.setCellWidget(row, 7, action_bar)
            
            self.customer_select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载客户数据失败: {str(e)}")

    def search_customers(self):
        keyword = self.customer_search_input.text().strip()
        country = self.customer_country_filter.currentData()
        country = country if country != 0 else None
        
        try:
            customers = self.api_client.search_customers(keyword, country)
            self.customers_table.setRowCount(len(customers))
            for row, c in enumerate(customers):
                checkbox = QCheckBox()
                checkbox.setStyleSheet("margin-left: 50%;")
                self.customers_table.setCellWidget(row, 0, checkbox)
                
                self.customers_table.setItem(row, 1, QTableWidgetItem(str(c.get('id', ''))))
                self.customers_table.setItem(row, 2, QTableWidgetItem(c.get('customer_code', '')))
                self.customers_table.setItem(row, 3, QTableWidgetItem(c.get('customer_name', '')))
                self.customers_table.setItem(row, 4, QTableWidgetItem(c.get('country', '')))
                self.customers_table.setItem(row, 5, QTableWidgetItem(c.get('payment_terms', '')))
                
                status = c.get('status', 1)
                status_text = "启用" if status == 1 else "禁用"
                status_color = "#10b981" if status == 1 else "#ef4444"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(QBrush(QColor(status_color)))
                self.customers_table.setItem(row, 6, status_item)

                action_bar = ActionBarFactory.create_customer_action_bar(
                    edit_callback=lambda _, c=c: self.edit_customer(c),
                    toggle_callback=lambda _, c=c: self.toggle_customer_status(c),
                    status=status
                )
                self.customers_table.setCellWidget(row, 7, action_bar)
            
            self.customer_select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"搜索客户失败: {str(e)}")

    def toggle_customer_status(self, customer):
        try:
            result = self.api_client.toggle_customer_status(customer['id'])
            if result:
                self.load_customers()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"操作失败: {str(e)}")

    def on_customer_double_click(self, index):
        row = index.row()
        customer_id = self.customers_table.item(row, 1).text()
        try:
            customer = self.api_client.get_customer_detail(int(customer_id))
            self.view_customer_detail(customer)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载客户详情失败: {str(e)}")

    def view_customer_detail(self, customer):
        dialog = CustomerDetailDialog(self.api_client, customer)
        dialog.exec()

    def toggle_select_all_customers(self, state):
        for row in range(self.customers_table.rowCount()):
            checkbox = self.customers_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setCheckState(Qt.CheckState(state))

    def load_suppliers(self):
        try:
            suppliers = self.api_client.get_suppliers()
            self.suppliers_table.setRowCount(len(suppliers))
            for row, s in enumerate(suppliers):
                checkbox = QCheckBox()
                checkbox.setStyleSheet("margin-left: 15px;")
                self.suppliers_table.setCellWidget(row, 0, checkbox)

                self.suppliers_table.setItem(row, 1, QTableWidgetItem(str(s.get('id', ''))))
                self.suppliers_table.setItem(row, 2, QTableWidgetItem(s.get('supplier_code', '')))
                self.suppliers_table.setItem(row, 3, QTableWidgetItem(s.get('supplier_name', '')))
                self.suppliers_table.setItem(row, 4, QTableWidgetItem(s.get('region', '')))
                self.suppliers_table.setItem(row, 5, QTableWidgetItem(s.get('contact_person', '')))
                self.suppliers_table.setItem(row, 6, QTableWidgetItem(s.get('phone', '')))

                edit_btn = QPushButton("编辑")
                edit_btn.setFixedWidth(60)
                edit_btn.clicked.connect(lambda _, s=s: self.edit_supplier(s))
                self.suppliers_table.setCellWidget(row, 7, edit_btn)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载供应商数据失败: {str(e)}")

    def load_pi_orders(self):
        try:
            pi_orders = self.api_client.get_pi_orders()
            self.pi_table.setRowCount(len(pi_orders))
            status_map = {1: "草稿", 2: "已确认", 3: "已发货", 4: "已完成"}
            for row, pi in enumerate(pi_orders):
                self.pi_table.setItem(row, 0, QTableWidgetItem(str(pi.get('id', ''))))
                self.pi_table.setItem(row, 1, QTableWidgetItem(pi.get('pi_no', '')))
                self.pi_table.setItem(row, 2, QTableWidgetItem(str(pi.get('total_amount', ''))))
                self.pi_table.setItem(row, 3, QTableWidgetItem(status_map.get(pi.get('status', 1), "未知")))
                self.pi_table.setItem(row, 4, QTableWidgetItem(str(pi.get('created_at', ''))))
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载PI订单数据失败: {str(e)}")

    def load_purchase_orders(self):
        try:
            purchase_orders = self.api_client.get_purchase_orders()
            self.purchase_table.setRowCount(len(purchase_orders))
            status_map = {1: "草稿", 2: "已确认", 3: "已入库"}
            for row, po in enumerate(purchase_orders):
                self.purchase_table.setItem(row, 0, QTableWidgetItem(str(po.get('id', ''))))
                self.purchase_table.setItem(row, 1, QTableWidgetItem(po.get('po_no', '')))
                self.purchase_table.setItem(row, 2, QTableWidgetItem(po.get('pi_no', '')))
                self.purchase_table.setItem(row, 3, QTableWidgetItem(po.get('supplier_name', '')))
                self.purchase_table.setItem(row, 4, QTableWidgetItem(str(po.get('total_amount', ''))))
                self.purchase_table.setItem(row, 5, QTableWidgetItem(status_map.get(po.get('status', 1), "未知")))
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载采购订单数据失败: {str(e)}")

    def toggle_product_status(self, product):
        product_id = product.get('id')
        product_code = product.get('product_code', '')
        status = product.get('status', 1)
        status_text = "禁用" if status == 1 else "启用"
        
        reply = QMessageBox.question(
            self, "确认操作", 
            f"确定要{status_text}产品 {product_code} 吗？",
            QMessageBox.Ok | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Ok:
            try:
                self.api_client.toggle_product_status(product_id)
                QMessageBox.information(self, "成功", f"产品已{status_text}")
                self.load_products()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"{status_text}产品失败: {str(e)}")

    def delete_product(self, product):
        product_id = product.get('id')
        product_code = product.get('product_code', '')
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除产品 {product_code} 吗？此操作不可恢复！",
            QMessageBox.Ok | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Ok:
            try:
                self.api_client.delete_product(product_id)
                QMessageBox.information(self, "成功", "产品已删除")
                self.load_products()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除产品失败: {str(e)}")

    def add_product(self):
        print("add_product called, dept_id:", self.dept_id)
        try:
            dialog = ProductDialog(self.api_client, self.dept_id)
            print("ProductDialog created successfully")
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_products()
        except Exception as e:
            print("Error in add_product:", str(e))
            QMessageBox.warning(self, "错误", f"打开新增产品对话框失败: {str(e)}")

    def on_product_double_click(self, index):
        row = index.row()
        product_id = self.products_table.item(row, 2).text()
        try:
            product = self.api_client.get_product_detail(int(product_id))
            self.edit_product(product)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载产品信息失败: {str(e)}")

    def edit_product(self, product):
        dialog = ProductDialog(self.api_client, self.dept_id, product)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_products()

    def import_products(self):
        print("DEBUG - import_products called")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择导入文件", "", "Excel文件 (*.xlsx *.xls)"
        )
        
        print(f"DEBUG - Selected file: {file_path}")
        
        if not file_path:
            return
        
        try:
            df = pd.read_excel(file_path)
            print(f"DEBUG - Excel file loaded, rows: {len(df)}")
            
            products_data = []
            for idx, row in df.iterrows():
                product = {
                    "oe_number": str(row.get("OE号", "")),
                    "factory_code": str(row.get("工厂编号", "")),
                    "brand": str(row.get("品牌", "")),
                    "detail_desc": str(row.get("细节描述", "")),
                    "category_id": int(row.get("类别ID", 1)),
                    "supplier_id": int(row.get("供应商ID", 0)) if pd.notna(row.get("供应商ID")) else None,
                    "exw_price_incl": float(row.get("EXW含税价", 0)) if pd.notna(row.get("EXW含税价")) else None,
                    "exw_price_excl": float(row.get("EXW不含税价", 0)) if pd.notna(row.get("EXW不含税价")) else None,
                    "fob_price_incl": float(row.get("FOB含税价", 0)) if pd.notna(row.get("FOB含税价")) else None,
                    "fob_price_excl": float(row.get("FOB不含税价", 0)) if pd.notna(row.get("FOB不含税价")) else None,
                    "freight": float(row.get("运费", 0)) if pd.notna(row.get("运费")) else None,
                    "packing_fee": float(row.get("包装费", 0)) if pd.notna(row.get("包装费")) else None,
                    "purchase_channel": str(row.get("采购渠道", "")),
                    "carton_length_cm": float(row.get("纸箱长(cm)", 0)) if pd.notna(row.get("纸箱长(cm)")) else None,
                    "carton_width_cm": float(row.get("纸箱宽(cm)", 0)) if pd.notna(row.get("纸箱宽(cm)")) else None,
                    "carton_height_cm": float(row.get("纸箱高(cm)", 0)) if pd.notna(row.get("纸箱高(cm)")) else None,
                    "carton_volume_cbm": float(row.get("纸箱体积(CBM)", 0)) if pd.notna(row.get("纸箱体积(CBM)")) else None,
                    "carton_weight_kg": float(row.get("纸箱重量(KG)", 0)) if pd.notna(row.get("纸箱重量(KG)")) else None,
                    "pieces_per_carton": int(row.get("每箱数量", 0)) if pd.notna(row.get("每箱数量")) else None,
                    "unit": str(row.get("单位", "件")),
                    "moq": int(row.get("最小起订量", 0)) if pd.notna(row.get("最小起订量")) else None,
                }
                products_data.append(product)
            
            print(f"DEBUG - Prepared {len(products_data)} products for import")
            print(f"DEBUG - First product data: {products_data[0] if products_data else 'None'}")
            
            result = self.api_client.import_products(products_data)
            print(f"DEBUG - Import API result: {result}")
            
            if result.get("success"):
                QMessageBox.information(self, "成功", f"成功导入 {result.get('count', 0)} 个产品")
            else:
                QMessageBox.warning(self, "导入结果", f"导入完成，部分失败: {result.get('message', '')}")
            
            self.load_products()
            
        except Exception as e:
            print(f"DEBUG - Import failed: {str(e)}")
            QMessageBox.warning(self, "错误", f"导入失败: {str(e)}")

    def add_customer(self):
        dialog = CustomerDialog(self.api_client)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_customers()

    def edit_customer(self, customer):
        dialog = CustomerDialog(self.api_client, customer)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_customers()

    def import_suppliers(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择导入文件", "", 
            "Excel文件 (*.xlsx *.xls);;CSV文件 (*.csv)"
        )
        
        if not file_path:
            return
            
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8')
            else:
                df = pd.read_excel(file_path)
            
            supplier_list = []
            province_codes = self.PROVINCE_CODES
            city_data = self.CITY_DATA
            
            for _, row in df.iterrows():
                supplier_data = {}
                
                for col in df.columns:
                    col_lower = str(col).strip().lower()
                    value = row[col]
                    
                    if pd.isna(value):
                        value = None
                    else:
                        value = str(value).strip()
                    
                    if '供应商' in col_lower or '名称' in col_lower:
                        supplier_data['supplier_name'] = value
                    elif '省份' in col_lower:
                        supplier_data['province'] = value
                    elif '城市' in col_lower or '市' in col_lower:
                        supplier_data['city'] = value
                    elif '联系人' in col_lower:
                        supplier_data['contact_person'] = value
                    elif '电话' in col_lower or '手机' in col_lower:
                        supplier_data['phone'] = value
                    elif '邮箱' in col_lower or 'email' in col_lower:
                        supplier_data['email'] = value
                    elif '地址' in col_lower:
                        supplier_data['address'] = value
                
                if 'supplier_name' in supplier_data and supplier_data['supplier_name']:
                    province = supplier_data.get('province')
                    city = supplier_data.get('city')
                    
                    if province and city:
                        province_code = province_codes.get(province)
                        if province_code:
                            cities = city_data.get(province_code, {})
                            city_code = cities.get(city)
                            if city_code:
                                supplier_data['city_code'] = province_code + city_code
                    
                    supplier_list.append(supplier_data)
            
            if not supplier_list:
                QMessageBox.warning(self, "警告", "未找到有效的供应商数据")
                return
                
            progress = QProgressDialog("正在导入供应商...", "取消", 0, len(supplier_list), self)
            progress.setWindowModality(2)
            progress.show()
            
            def import_task():
                try:
                    result = self.api_client.post("/suppliers/batch", {"suppliers": supplier_list})
                    return result
                except Exception as e:
                    return {"error": str(e)}
            
            result = import_task()
            
            progress.close()
            
            if "error" in result:
                QMessageBox.critical(self, "导入失败", f"导入过程中发生错误: {result['error']}")
            else:
                success = result.get("success", 0)
                failed = result.get("failed", 0)
                msg = f"导入完成！\n成功: {success} 条\n失败: {failed} 条"
                if failed > 0:
                    failed_items = result.get("failed_items", [])
                    for item in failed_items[:5]:
                        msg += f"\n- {item['supplier_name']}: {item['error']}"
                    if len(failed_items) > 5:
                        msg += f"\n... 还有 {len(failed_items) - 5} 条失败记录"
                QMessageBox.information(self, "导入完成", msg)
                self.load_suppliers()
                
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"读取文件时发生错误: {str(e)}")

    def add_supplier(self):
        dialog = SupplierDialog(self.api_client)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_suppliers()

    def on_supplier_double_click(self, index):
        row = index.row()
        supplier_id = self.suppliers_table.item(row, 1).text()
        try:
            supplier = self.api_client.get_supplier_detail(int(supplier_id))
            self.edit_supplier(supplier)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载供应商信息失败: {str(e)}")

    def edit_supplier(self, supplier):
        dialog = SupplierDialog(self.api_client, supplier)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_suppliers()

    def add_pi(self):
        dialog = PIDialog(self.api_client, self.dept_id)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_pi_orders()

    def add_purchase(self):
        dialog = PurchaseDialog(self.api_client, self.dept_id)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_purchase_orders()


class PIDialog(QDialog):
    def __init__(self, api_client, dept_id, pi=None):
        super().__init__()
        self.api_client = api_client
        self.dept_id = dept_id
        self.pi = pi
        self.is_edit = pi is not None
        self.customers = []
        self.products = []
        self.items = []
        self.init_ui()
        QTimer.singleShot(0, self.load_data)
    
    def load_data(self):
        self.load_customers()
        self.load_products()

    def load_customers(self):
        try:
            self.customers = self.api_client.get_customers()
            self.customer_combo.clear()
            self.customer_combo.addItem("", "")
            for c in self.customers:
                self.customer_combo.addItem(f"{c.get('customer_code')} - {c.get('customer_name')}", c.get('id'))
        except Exception as e:
            print(f"加载客户失败: {e}")

    def load_products(self):
        try:
            self.products = self.api_client.get_products()
            self.product_combo.clear()
            self.product_combo.addItem("", "")
            for p in self.products:
                self.product_combo.addItem(f"{p.get('product_code')} - {p.get('oe_number')}", p)
        except Exception as e:
            print(f"加载产品失败: {e}")

    def init_ui(self):
        self.setWindowTitle("编辑PI单" if self.is_edit else "新建PI单")
        self.setFixedSize(700, 600)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.customer_combo = QComboBox()
        self.customer_combo.setFixedHeight(35)
        form_layout.addRow("客户:", self.customer_combo)

        self.currency_combo = QComboBox()
        self.currency_combo.setFixedHeight(35)
        self.currency_combo.addItems(["USD", "CNY", "EUR"])
        form_layout.addRow("货币:", self.currency_combo)

        layout.addLayout(form_layout)

        items_group = QGroupBox("产品明细")
        items_layout = QVBoxLayout()

        toolbar = QHBoxLayout()
        self.product_combo = QComboBox()
        self.product_combo.setFixedWidth(200)
        toolbar.addWidget(self.product_combo)

        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("数量")
        self.quantity_input.setFixedWidth(100)
        toolbar.addWidget(self.quantity_input)

        self.unit_price_input = QLineEdit()
        self.unit_price_input.setPlaceholderText("单价")
        self.unit_price_input.setFixedWidth(100)
        toolbar.addWidget(self.unit_price_input)

        add_item_btn = QPushButton("+ 添加")
        add_item_btn.clicked.connect(self.add_item)
        toolbar.addWidget(add_item_btn)

        items_layout.addLayout(toolbar)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels(["产品编号", "OE号", "数量", "单价", "操作"])
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.items_table.setFixedHeight(200)
        items_layout.addWidget(self.items_table)

        items_group.setLayout(items_layout)
        layout.addWidget(items_group)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_pi)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        buttons_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def add_item(self):
        product = self.product_combo.currentData()
        quantity = self.quantity_input.text().strip()
        unit_price = self.unit_price_input.text().strip()

        if not product or not quantity or not unit_price:
            QMessageBox.warning(self, "警告", "请填写完整信息")
            return

        try:
            quantity = int(quantity)
            unit_price = float(unit_price)
        except ValueError:
            QMessageBox.warning(self, "警告", "数量和单价必须是数字")
            return

        self.items.append({
            "product_id": product.get('id'),
            "product_code": product.get('product_code'),
            "oe_number": product.get('oe_number'),
            "quantity": quantity,
            "unit_price": unit_price,
            "customer_code": "",
            "detail_desc": "",
            "remark": ""
        })

        self.update_items_table()

    def update_items_table(self):
        self.items_table.setRowCount(len(self.items))
        for row, item in enumerate(self.items):
            self.items_table.setItem(row, 0, QTableWidgetItem(item.get('product_code', '')))
            self.items_table.setItem(row, 1, QTableWidgetItem(item.get('oe_number', '')))
            self.items_table.setItem(row, 2, QTableWidgetItem(str(item.get('quantity', ''))))
            self.items_table.setItem(row, 3, QTableWidgetItem(str(item.get('unit_price', ''))))

            delete_btn = QPushButton("删除")
            delete_btn.setFixedWidth(50)
            delete_btn.setStyleSheet("background-color: #dc2626; color: white; border: none; border-radius: 4px; padding: 2px;")
            delete_btn.clicked.connect(lambda _, r=row: self.remove_item(r))
            self.items_table.setCellWidget(row, 4, delete_btn)

    def remove_item(self, row):
        del self.items[row]
        self.update_items_table()

    def save_pi(self):
        customer_id = self.customer_combo.currentData()
        currency = self.currency_combo.currentText()

        if not customer_id:
            QMessageBox.warning(self, "警告", "请选择客户")
            return

        if not self.items:
            QMessageBox.warning(self, "警告", "请添加产品明细")
            return

        pi_data = {
            "dept_id": self.dept_id,
            "customer_id": customer_id,
            "currency": currency,
            "items": self.items,
            "payment_stages": []
        }

        try:
            if self.is_edit:
                self.api_client.update_pi(self.pi.get('id'), pi_data)
            else:
                self.api_client.create_pi(pi_data)
            QMessageBox.information(self, "成功", "PI单已保存")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")


class PurchaseDialog(QDialog):
    def __init__(self, api_client, dept_id, purchase=None):
        super().__init__()
        self.api_client = api_client
        self.dept_id = dept_id
        self.purchase = purchase
        self.is_edit = purchase is not None
        self.pi_orders = []
        self.suppliers = []
        self.products = []
        self.items = []
        self.init_ui()
        QTimer.singleShot(0, self.load_data)
    
    def load_data(self):
        self.load_pi_orders()
        self.load_suppliers()
        self.load_products()

    def load_pi_orders(self):
        try:
            self.pi_orders = self.api_client.get_pi_orders()
            self.pi_combo.clear()
            self.pi_combo.addItem("", "")
            for pi in self.pi_orders:
                self.pi_combo.addItem(f"{pi.get('pi_no')} - {pi.get('total_amount')} {pi.get('currency')}", pi)
        except Exception as e:
            print(f"加载PI订单失败: {e}")

    def load_suppliers(self):
        try:
            self.suppliers = self.api_client.get_suppliers()
            self.supplier_combo.clear()
            self.supplier_combo.addItem("", "")
            for s in self.suppliers:
                self.supplier_combo.addItem(f"{s.get('supplier_code')} - {s.get('supplier_name')}", s.get('id'))
        except Exception as e:
            print(f"加载供应商失败: {e}")

    def load_products(self):
        try:
            self.products = self.api_client.get_products()
            self.product_combo.clear()
            self.product_combo.addItem("", "")
            for p in self.products:
                self.product_combo.addItem(f"{p.get('product_code')} - {p.get('oe_number')}", p)
        except Exception as e:
            print(f"加载产品失败: {e}")

    def init_ui(self):
        self.setWindowTitle("编辑采购单" if self.is_edit else "新建采购单")
        self.setFixedSize(700, 600)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.pi_combo = QComboBox()
        self.pi_combo.setFixedHeight(35)
        form_layout.addRow("关联PI单:", self.pi_combo)

        self.supplier_combo = QComboBox()
        self.supplier_combo.setFixedHeight(35)
        form_layout.addRow("供应商:", self.supplier_combo)

        self.currency_combo = QComboBox()
        self.currency_combo.setFixedHeight(35)
        self.currency_combo.addItems(["CNY", "USD", "EUR"])
        form_layout.addRow("货币:", self.currency_combo)

        layout.addLayout(form_layout)

        items_group = QGroupBox("采购明细")
        items_layout = QVBoxLayout()

        toolbar = QHBoxLayout()
        self.product_combo = QComboBox()
        self.product_combo.setFixedWidth(200)
        toolbar.addWidget(self.product_combo)

        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("数量")
        self.quantity_input.setFixedWidth(100)
        toolbar.addWidget(self.quantity_input)

        self.unit_price_input = QLineEdit()
        self.unit_price_input.setPlaceholderText("单价")
        self.unit_price_input.setFixedWidth(100)
        toolbar.addWidget(self.unit_price_input)

        add_item_btn = QPushButton("+ 添加")
        add_item_btn.clicked.connect(self.add_item)
        toolbar.addWidget(add_item_btn)

        items_layout.addLayout(toolbar)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels(["产品编号", "OE号", "数量", "单价", "操作"])
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.items_table.setFixedHeight(200)
        items_layout.addWidget(self.items_table)

        items_group.setLayout(items_layout)
        layout.addWidget(items_group)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_purchase)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        buttons_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #d1d5db; }
        """)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def add_item(self):
        product = self.product_combo.currentData()
        quantity = self.quantity_input.text().strip()
        unit_price = self.unit_price_input.text().strip()

        if not product or not quantity or not unit_price:
            QMessageBox.warning(self, "警告", "请填写完整信息")
            return

        try:
            quantity = int(quantity)
            unit_price = float(unit_price)
        except ValueError:
            QMessageBox.warning(self, "警告", "数量和单价必须是数字")
            return

        self.items.append({
            "product_id": product.get('id'),
            "product_code": product.get('product_code'),
            "oe_number": product.get('oe_number'),
            "quantity": quantity,
            "unit_price": unit_price,
            "remark": ""
        })

        self.update_items_table()

    def update_items_table(self):
        self.items_table.setRowCount(len(self.items))
        for row, item in enumerate(self.items):
            self.items_table.setItem(row, 0, QTableWidgetItem(item.get('product_code', '')))
            self.items_table.setItem(row, 1, QTableWidgetItem(item.get('oe_number', '')))
            self.items_table.setItem(row, 2, QTableWidgetItem(str(item.get('quantity', ''))))
            self.items_table.setItem(row, 3, QTableWidgetItem(str(item.get('unit_price', ''))))

            delete_btn = QPushButton("删除")
            delete_btn.setFixedWidth(50)
            delete_btn.setStyleSheet("background-color: #dc2626; color: white; border: none; border-radius: 4px; padding: 2px;")
            delete_btn.clicked.connect(lambda _, r=row: self.remove_item(r))
            self.items_table.setCellWidget(row, 4, delete_btn)

    def remove_item(self, row):
        del self.items[row]
        self.update_items_table()

    def save_purchase(self):
        pi = self.pi_combo.currentData()
        supplier_id = self.supplier_combo.currentData()
        currency = self.currency_combo.currentText()

        if not pi:
            QMessageBox.warning(self, "警告", "请选择关联的PI单")
            return

        if not supplier_id:
            QMessageBox.warning(self, "警告", "请选择供应商")
            return

        if not self.items:
            QMessageBox.warning(self, "警告", "请添加采购明细")
            return

        purchase_data = {
            "dept_id": self.dept_id,
            "pi_id": pi.get('id'),
            "supplier_id": supplier_id,
            "currency": currency,
            "items": self.items
        }

        try:
            if self.is_edit:
                self.api_client.update_purchase(self.purchase.get('id'), purchase_data)
            else:
                self.api_client.create_purchase(purchase_data)
            QMessageBox.information(self, "成功", "采购单已保存")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")


def main():
    ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    
    # 启用高DPI缩放（使用推荐方式）
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
    
    app = QApplication(sys.argv)
    
    # 设置全局字体
    font = QFont()
    font.setFamily("Microsoft YaHei")
    font.setPointSize(10)
    app.setFont(font)

    # 使用带缓存功能的API客户端
    api_client = CachedApiClient()

    try:
        login = LoginWindow(api_client)
        if login.exec() != QDialog.DialogCode.Accepted:
            return

        dept_id = login.get_selected_department() or "S"
        window = MainWindow(api_client, dept_id)
        window.show()

        sys.exit(app.exec())
    except Exception as e:
        print("Error during application execution:", str(e))
        traceback.print_exc()
        # 显示错误对话框
        error_dialog = QDialog()
        error_dialog.setWindowTitle("启动错误")
        error_dialog.resize(400, 200)
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"启动失败: {str(e)}"))
        layout.addWidget(QLabel("请检查日志获取详细信息"))
        error_dialog.setLayout(layout)
        error_dialog.exec()
        sys.exit(1)


if __name__ == "__main__":
    main()