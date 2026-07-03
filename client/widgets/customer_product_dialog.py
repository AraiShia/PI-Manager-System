"""
客户产品编辑对话框 - 支持多编号、多OE号、图片管理
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QTextEdit, QComboBox, QPushButton, QWidget, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QCheckBox, QScrollArea,
    QMessageBox, QInputDialog, QApplication, QGridLayout
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QPixmap, QImage
import urllib.request
import json

from api.client import ApiClient
from product_categories import get_parent_category_options, get_child_category_options, get_category_name
from config import Config


def _normalize_image_url(image_url):
    """把后端返回的相对路径（/images/xxx）补全为绝对 URL"""
    if not image_url:
        return image_url
    if image_url.startswith(("http://", "https://")):
        return image_url
    base = (Config.API_BASE_URL or "").rstrip("/")
    if image_url.startswith("/"):
        return f"{base}{image_url}"
    return f"{base}/{image_url}"


class ImageLoadWorker(QThread):
    """异步图片加载工作线程"""
    finished = Signal(str, QPixmap)
    error = Signal(str, str)

    def __init__(self, url, max_w: int = 56, max_h: int = 56, parent=None):
        """
        Args:
            url: 图片 URL
            max_w: 缩放后最大宽度（默认 56，匹配副图）
            max_h: 缩放后最大高度（默认 56，匹配副图）
        """
        super().__init__(parent)
        self.url = _normalize_image_url(url)
        self.max_w = max_w
        self.max_h = max_h

    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                image_data = response.read()

            image = QImage.fromData(image_data)
            if image:
                pixmap = QPixmap.fromImage(image).scaled(
                    self.max_w, self.max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.finished.emit(self.url, pixmap)
            else:
                self.error.emit(self.url, "无法解析图片")
        except Exception as e:
            self.error.emit(self.url, str(e))


class ImageUploadWorker(QThread):
    """异步图片上传工作线程"""
    finished = Signal(str, bool, str)
    
    def __init__(self, api_client, file_path):
        super().__init__()
        self.api_client = api_client
        self.file_path = file_path
    
    def run(self):
        try:
            with open(self.file_path, 'rb') as f:
                filename = self.file_path.split('/')[-1]
                files = {'file': (filename, f.read(), 'image/jpeg')}
                resp = self.api_client.post("/images/upload", files=files)
                
                if resp and resp.get('url'):
                    self.finished.emit(resp['url'], True, "上传成功")
                elif resp and resp.get('message'):
                    self.finished.emit('', False, resp.get('message'))
                else:
                    self.finished.emit('', False, "上传失败")
        except Exception as e:
            self.finished.emit('', False, f"上传失败: {e}")


class BatchImportDialog(QDialog):
    """批量导入弹窗"""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title = title
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        title_label = QLabel(f"📋 {self.title}")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        hint_label = QLabel("请粘贴内容（每行一个）：")
        layout.addWidget(hint_label)
        
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("例如：\n12710304\n36547890\nABC123456")
        self.text_input.setMinimumHeight(200)
        layout.addWidget(self.text_input)
        
        self.count_label = QLabel("检测到: 0 个")
        self.count_label.setStyleSheet("color: #6b7280;")
        layout.addWidget(self.count_label)
        
        self.set_primary_checkbox = QCheckBox("☑ 将第一个设为主项")
        self.set_primary_checkbox.setChecked(True)
        layout.addWidget(self.set_primary_checkbox)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        confirm_btn = QPushButton("确认导入")
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(confirm_btn)
        
        layout.addLayout(btn_layout)
        self.text_input.textChanged.connect(self.update_count)
    
    def update_count(self):
        text = self.text_input.toPlainText()
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        self.count_label.setText(f"检测到: {len(lines)} 个")
    
    def get_items(self):
        text = self.text_input.toPlainText()
        return [line.strip() for line in text.split('\n') if line.strip()]
    
    def is_set_first_primary(self):
        return self.set_primary_checkbox.isChecked()


class ClickableLabel(QLabel):
    """可点击的 QLabel"""
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class SubImageWidget(QWidget):
    """副图网格容器 - 异步加载图片"""
    add_image_requested = Signal()  # 添加图片请求信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.images = []
        self.image_workers = []
        self.image_labels = {}
        self.loading_labels = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.scroll = QScrollArea()
        self.scroll.setMinimumHeight(150)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(8)

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
    
    def add_image(self, url):
        """添加图片"""
        self.images.append(url)
        self._rebuild()
    
    def remove_image(self, index):
        """删除图片"""
        if 0 <= index < len(self.images):
            self.images.pop(index)
            self._rebuild()
    
    def _rebuild(self):
        """重建图片显示 - 使用网格布局"""
        print(f"[DEBUG] _rebuild called, images count: {len(self.images)}")

        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for worker in self.image_workers:
            if not worker.isFinished():
                worker.quit()
        self.image_workers.clear()
        self.image_labels.clear()
        self.loading_labels.clear()

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(10)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(10)

        cols = 4

        for idx, url in enumerate(self.images):
            row = idx // cols
            col = idx % cols

            img_widget = QWidget()
            img_layout = QVBoxLayout(img_widget)
            img_layout.setContentsMargins(0, 0, 0, 0)
            img_layout.setSpacing(4)

            img_label = QLabel()
            img_label.setFixedSize(100, 100)
            img_label.setStyleSheet("border: 1px solid #e5e7eb; border-radius: 4px; background-color: #f3f4f6;")
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setText("加载中...")
            img_label.setProperty("url", url)
            self.image_labels[url] = img_label
            self.loading_labels[url] = True
            img_layout.addWidget(img_label)

            delete_btn = QPushButton("删除")
            delete_btn.setFixedHeight(28)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #dc2626;
                }
            """)
            delete_btn.clicked.connect(lambda checked, i=idx: self.remove_image(i))
            img_layout.addWidget(delete_btn)

            grid_layout.addWidget(img_widget, row, col)
            self._load_image_async(url)

        add_row = (len(self.images) // cols) + (1 if len(self.images) % cols > 0 else 0)

        add_widget = QWidget()
        add_layout = QVBoxLayout(add_widget)
        add_layout.setContentsMargins(0, 0, 0, 0)
        add_layout.setSpacing(4)

        add_label = QLabel()
        add_label.setFixedSize(100, 100)
        add_label.setAlignment(Qt.AlignCenter)
        add_label.setText("+")
        add_label.setStyleSheet("""
            border: 2px dashed #d1d5db;
            border-radius: 4px;
            background-color: #f9fafb;
            color: #9ca3af;
            font-size: 32px;
        """)
        add_layout.addWidget(add_label)

        add_btn = QPushButton("添加图片")
        add_btn.setFixedHeight(28)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                color: #374151;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
        """)
        add_btn.clicked.connect(self.add_image_requested.emit)
        add_layout.addWidget(add_btn)

        grid_layout.addWidget(add_widget, add_row, 0, 1, 1)

        print(f"[DEBUG] grid_widget created, items in grid_layout: {grid_layout.count()}")
        print(f"[DEBUG] add_widget added at row={add_row}, col=0")

        self.container_layout.addWidget(grid_widget)
        print(f"[DEBUG] container_layout now has {self.container_layout.count()} items")
    
    def _load_image_async(self, url):
        worker = ImageLoadWorker(url, self)
        worker.finished.connect(self._on_image_loaded)
        worker.error.connect(self._on_image_error)
        self.image_workers.append(worker)
        worker.start()
    
    def _on_image_loaded(self, url, pixmap):
        if url in self.image_labels and url in self.loading_labels:
            label = self.image_labels[url]
            scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(scaled_pixmap)
            label.setText("")
            del self.loading_labels[url]
    
    def _on_image_error(self, url, error):
        if url in self.image_labels and url in self.loading_labels:
            label = self.image_labels[url]
            label.setText("错误")
            del self.loading_labels[url]
    
    def get_images(self):
        return self.images


class CustomerProductDialog(QDialog):
    """客户产品编辑对话框"""
    # 2026-06-16 修复：信号改为 (bool, dict)，传完整 API 返回值（含 customer_remark / price_usd 等）
    product_confirmed = Signal(bool, dict)  # (success: bool, updated_product: dict)

    def __init__(self, api_client: ApiClient, product=None, parent=None, mode="normal"):
        super().__init__(parent)
        self.api_client = api_client
        self.product = product or {}
        self.is_edit = bool(product and product.get('id'))
        # 2026-07-02：临时产品转正功能已去除，confirm_temp 模式不再支持
        self.mode = "edit" if mode == "confirm_temp" else mode
        self._preset_customer_id = None
        
        self.customers = []
        self.categories = []
        self.codes = []
        self.oes = []
        self.sub_images = []
        self.main_image_url = None

        # 客户产品编号一次修改状态跟踪
        self._primary_code_modified = False
        
        if self.is_edit:
            self.setWindowTitle("编辑客户产品")
        else:
            self.setWindowTitle("新增客户产品")
        self.setMinimumSize(900, 700)
        self.resize(900, 700)
        
        QTimer.singleShot(0, self._load_data_async)
    
    def _load_data_async(self):
        """异步加载数据，不阻塞界面"""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        try:
            self.customers = self.api_client.get_customers() or []
            print(f"[DEBUG] 加载客户成功: {len(self.customers)} 个")
        except Exception as e:
            print(f"[ERROR] 加载客户失败: {e}")
        
        try:
            self.categories = self.api_client.get_product_categories() or []
            print(f"[DEBUG] 加载类目成功: {len(self.categories)} 个")
        except Exception as e:
            print(f"[ERROR] 加载类目失败: {e}")
            self.categories = []

        # 2026-06-23 修复：API 返回空（prd_product_category 表为空）时 fallback 到硬编码 CATEGORIES
        # 否则 L524 self.categories 找不到 category_code → parent_code 为 None → 一级类目无法回填
        if not self.categories:
            try:
                from product_categories import CATEGORIES, PARENT_CATEGORIES
                # 转换为 API 返回格式: {code, name, parent_id}
                self.categories = []
                for p in PARENT_CATEGORIES:
                    self.categories.append({
                        "code": p["code"],
                        "name": p["name"],
                        "parent_id": None,
                    })
                for c in CATEGORIES:
                    self.categories.append({
                        "code": c["code"],
                        "name": c["name"],
                        "parent_id": c.get("parent_code"),
                    })
                print(f"[DEBUG] 加载类目 fallback 到硬编码: {len(self.categories)} 个")
            except Exception as e:
                print(f"[ERROR] 加载类目 fallback 失败: {e}")
        
        if self.is_edit:
            product_id = self.product.get('id')
            if product_id:
                try:
                    codes_resp = self.api_client.get(f"/customer-products/{product_id}/codes")
                    if codes_resp and isinstance(codes_resp, list):
                        self.codes = codes_resp
                except Exception as e:
                    # 2026-06-12 修复：404 是产品无记录的预期情况，不应作为 ERROR
                    err_str = str(e)
                    if '404' in err_str:
                        print(f"[INFO] 该产品暂无客户产品编号记录 (product_id={product_id})")
                    else:
                        print(f"[ERROR] 加载编号失败: {e}")

                try:
                    oes_resp = self.api_client.get(f"/customer-products/{product_id}/oes")
                    if oes_resp and isinstance(oes_resp, list):
                        self.oes = oes_resp
                except Exception as e:
                    # 2026-06-12 修复：404 是产品无记录的预期情况，不应作为 ERROR
                    err_str = str(e)
                    if '404' in err_str:
                        print(f"[INFO] 该产品暂无OE号记录 (product_id={product_id})")
                    else:
                        print(f"[ERROR] 加载OE号失败: {e}")
                
                if self.product.get('sub_images'):
                    try:
                        self.sub_images = json.loads(self.product.get('sub_images')) or []
                    except:
                        self.sub_images = []
        
        QApplication.restoreOverrideCursor()

        self.init_ui()
        self._auto_fill_primary_code()
        self._update_modify_code_button_state()
        self.refresh_codes_table()
        self.refresh_oes_table()
    
    def init_ui(self):
        print("[DEBUG] init_ui started")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)
        
        # 客户选择
        customer_layout = QHBoxLayout()
        customer_layout.addWidget(QLabel("客户:"))
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumWidth(200)
        self.customer_combo.addItem("-- 请选择客户 --", None)
        for c in self.customers:
            self.customer_combo.addItem(c.get('customer_name', ''), c.get('id'))
        
        # 预设客户时自动选中
        if self._preset_customer_id:
            for i in range(self.customer_combo.count()):
                if self.customer_combo.itemData(i) == self._preset_customer_id:
                    self.customer_combo.setCurrentIndex(i)
                    break
        elif self.is_edit and self.product.get('customer_id'):
            for i in range(self.customer_combo.count()):
                if self.customer_combo.itemData(i) == self.product.get('customer_id'):
                    self.customer_combo.setCurrentIndex(i)
                    break
        
        customer_layout.addWidget(self.customer_combo)
        customer_layout.addStretch()
        scroll_layout.addLayout(customer_layout)
        
        # 基本信息
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout()
        basic_layout.setSpacing(12)
        
        # 系统编号（只读，带临时/正式标签）
        self.system_code_label = QLabel("")
        self.system_code_label.setStyleSheet("font-weight: bold;")
        basic_layout.addRow("系统编号:", self.system_code_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入产品名称")
        if self.is_edit:
            self.name_input.setText(self.product.get('product_name', ''))
        basic_layout.addRow("产品名称:", self.name_input)
        
        # 类别筛选 - 级联选择
        category_widget_layout = QHBoxLayout()
        
        self.category_filter_level1 = QComboBox()
        self.category_filter_level1.setMinimumWidth(100)
        self.category_filter_level1.addItem("-- 请选择大类 --", 0)
        for code, name in get_parent_category_options():
            self.category_filter_level1.addItem(name, code)
        self.category_filter_level1.currentIndexChanged.connect(self.on_category_level1_changed)
        category_widget_layout.addWidget(self.category_filter_level1)
        
        self.category_filter_level2 = QComboBox()
        self.category_filter_level2.setMinimumWidth(100)
        self.category_filter_level2.addItem("-- 请选择子类 --", 0)
        category_widget_layout.addWidget(self.category_filter_level2)
        
        basic_layout.addRow("产品类目:", category_widget_layout)
        
        # 编辑模式下，设置已选择的类别
        if self.is_edit and self.product.get('category_id'):
            category_code = self.product.get('category_id')
            # 查找父类别
            # 2026-06-23 修复：后端 Pydantic ProductCategoryResponse 序列化的字段是 parent_id
            # （非 client/product_categories.py 硬编码 CATEGORIES 用的 parent_code）。
            # 之前用 cat.get('parent_code') 永远拿不到值 → 一级下拉框无法回填 → 看起来类目丢失。
            parent_code = None
            for cat in self.categories:
                if cat.get('code') == category_code:
                    parent_code = cat.get('parent_id') or cat.get('parent_code')
                    break
            
            # 设置一级类别（先阻止信号，避免触发自动填充）
            if parent_code:
                self.category_filter_level1.currentIndexChanged.disconnect()
                for i in range(self.category_filter_level1.count()):
                    if self.category_filter_level1.itemData(i) == parent_code:
                        self.category_filter_level1.setCurrentIndex(i)
                        break
                self.category_filter_level1.currentIndexChanged.connect(self.on_category_level1_changed)
                
                # 手动填充二级类别选项
                self.category_filter_level2.clear()
                self.category_filter_level2.addItem("-- 请选择子类 --", 0)
                child_options = get_child_category_options(parent_code)
                for code, name in child_options:
                    self.category_filter_level2.addItem(name, code)
                
                # 设置二级类别
                for i in range(self.category_filter_level2.count()):
                    if self.category_filter_level2.itemData(i) == category_code:
                        self.category_filter_level2.setCurrentIndex(i)
                        break

            # 2026-07-03 修复：类目两个字段都有内容时锁定，不可再次编辑
            self._apply_category_lock()

        model_layout = QHBoxLayout()
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("默认等于主OE号")
        if self.is_edit:
            self.model_input.setText(self.product.get('customer_model', ''))
        model_layout.addWidget(self.model_input)
        auto_code_btn = QPushButton("自动生成编号")
        auto_code_btn.setToolTip("根据 客户编号 + 客户型号 自动生成客户产品编号")
        auto_code_btn.clicked.connect(self._auto_generate_primary_code)
        model_layout.addWidget(auto_code_btn)
        basic_layout.addRow("客户型号:", model_layout)

        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("产品颜色")
        if self.is_edit:
            self.color_input.setText(self.product.get('color', ''))
        basic_layout.addRow("颜色:", self.color_input)

        # 填充系统编号与临时/正式状态
        system_code = self.product.get('system_code', '')
        is_temp = self.product.get('is_system_code_temp', False)
        if is_temp:
            self.system_code_label.setText(f"{system_code} <span style='color:#f59e0b;'>[临时]</span>")
        else:
            self.system_code_label.setText(f"{system_code} <span style='color:#10b981;'>[正式]</span>")

        basic_group.setLayout(basic_layout)
        scroll_layout.addWidget(basic_group)
        
        # 图片区域
        image_group = QGroupBox("产品图片")
        image_layout = QHBoxLayout()
        image_layout.setSpacing(20)
        
        main_image_layout = QVBoxLayout()
        main_image_layout.addWidget(QLabel("主图"))
        self.main_image_label = ClickableLabel()
        self.main_image_label.setFixedSize(200, 200)
        self.main_image_label.setStyleSheet("border: 2px dashed #d1d5db; background-color: #f9fafb;")
        self.main_image_label.setAlignment(Qt.AlignCenter)
        self.main_image_label.setText("点击上传主图")
        self.main_image_label.setCursor(Qt.PointingHandCursor)
        self.main_image_label.clicked.connect(self.upload_main_image)
        main_image_layout.addWidget(self.main_image_label)
        
        main_btn_layout = QHBoxLayout()
        self.upload_main_btn = QPushButton("上传主图")
        self.upload_main_btn.clicked.connect(self.upload_main_image)
        main_btn_layout.addWidget(self.upload_main_btn)
        
        self.clear_main_btn = QPushButton("清除")
        self.clear_main_btn.clicked.connect(self.clear_main_image)
        main_btn_layout.addWidget(self.clear_main_btn)
        main_btn_layout.addStretch()
        main_image_layout.addLayout(main_btn_layout)
        
        image_layout.addLayout(main_image_layout)
        
        sub_image_layout = QVBoxLayout()
        sub_image_layout.addWidget(QLabel("副图（垂直滚动）"))
        print("[DEBUG] creating SubImageWidget...")
        self.sub_image_widget = SubImageWidget(self)
        print(f"[DEBUG] SubImageWidget created, type: {type(self.sub_image_widget).__name__}")
        print("[DEBUG] adding SubImageWidget to layout...")
        sub_image_layout.addWidget(self.sub_image_widget)
        print("[DEBUG] SubImageWidget added to layout")
        
        image_layout.addLayout(sub_image_layout)
        image_group.setLayout(image_layout)
        scroll_layout.addWidget(image_group)
        
        if self.is_edit and self.product.get('image_url'):
            self.load_main_image(self.product.get('image_url'))

        for url in self.sub_images:
            self.sub_image_widget.add_image(url)

        self.sub_image_widget.add_image_requested.connect(self.add_sub_image)

        print("[DEBUG] calling _rebuild to show add button...")
        self.sub_image_widget._rebuild()
        print("[DEBUG] init_ui completed")
        
        # 编号管理
        codes_group = QGroupBox("客户产品编号管理")
        codes_layout = QVBoxLayout()

        # 主编号显示与修改
        primary_code_layout = QHBoxLayout()
        self.primary_code_edit = QLineEdit()
        self.primary_code_edit.setReadOnly(True)
        self.primary_code_edit.setPlaceholderText("未生成（缺少客户型号）")
        primary_code_layout.addWidget(self.primary_code_edit, stretch=1)

        self.modify_code_btn = QPushButton("修改编号")
        self.modify_code_btn.setToolTip("只能修改一次")
        self.modify_code_btn.clicked.connect(self._on_modify_primary_code)
        primary_code_layout.addWidget(self.modify_code_btn)
        codes_layout.addLayout(primary_code_layout)

        self.codes_table = QTableWidget()
        self.codes_table.setColumnCount(3)
        self.codes_table.setHorizontalHeaderLabels(["编号", "主编号", "操作"])
        self.codes_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.codes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.codes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.codes_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.codes_table.setColumnWidth(1, 60)
        self.codes_table.setColumnWidth(2, 60)
        self.codes_table.setMaximumHeight(150)
        codes_layout.addWidget(self.codes_table)
        
        codes_btn_layout = QHBoxLayout()
        add_code_btn = QPushButton("+ 添加编号")
        add_code_btn.clicked.connect(self.add_code)
        codes_btn_layout.addWidget(add_code_btn)
        
        import_codes_btn = QPushButton("📋 复制粘贴批量导入")
        import_codes_btn.clicked.connect(self.import_codes_batch)
        codes_btn_layout.addWidget(import_codes_btn)
        codes_btn_layout.addStretch()
        codes_layout.addLayout(codes_btn_layout)
        
        codes_group.setLayout(codes_layout)
        scroll_layout.addWidget(codes_group)
        
        # OE号管理
        oes_group = QGroupBox("OE号管理")
        oes_layout = QVBoxLayout()
        
        self.oes_table = QTableWidget()
        self.oes_table.setColumnCount(3)
        self.oes_table.setHorizontalHeaderLabels(["OE号", "主OE", "操作"])
        self.oes_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.oes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.oes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.oes_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.oes_table.setColumnWidth(1, 60)
        self.oes_table.setColumnWidth(2, 60)
        self.oes_table.setMaximumHeight(150)
        oes_layout.addWidget(self.oes_table)
        
        oes_btn_layout = QHBoxLayout()
        add_oe_btn = QPushButton("+ 添加OE号")
        add_oe_btn.clicked.connect(self.add_oe)
        oes_btn_layout.addWidget(add_oe_btn)
        
        import_oes_btn = QPushButton("📋 复制粘贴批量导入")
        import_oes_btn.clicked.connect(self.import_oes_batch)
        oes_btn_layout.addWidget(import_oes_btn)
        oes_btn_layout.addStretch()
        oes_layout.addLayout(oes_btn_layout)
        
        oes_group.setLayout(oes_layout)
        scroll_layout.addWidget(oes_group)
        
        # 客户备注
        remark_group = QGroupBox("客户备注")
        remark_layout = QVBoxLayout()
        self.remark_input = QTextEdit()
        self.remark_input.setPlaceholderText("客户特殊要求...")
        self.remark_input.setMaximumHeight(80)
        if self.is_edit:
            self.remark_input.setText(self.product.get('customer_remark', ''))
        remark_layout.addWidget(self.remark_input)
        remark_group.setLayout(remark_layout)
        scroll_layout.addWidget(remark_group)
        
        # 价格
        price_group = QGroupBox("价格")
        price_layout = QHBoxLayout()
        
        price_layout.addWidget(QLabel("USD价格:"))
        self.price_usd_input = QLineEdit()
        self.price_usd_input.setPlaceholderText("0.00")
        self.price_usd_input.setFixedWidth(100)
        if self.is_edit:
            self.price_usd_input.setText(str(self.product.get('price_usd') or ''))
        price_layout.addWidget(self.price_usd_input)
        
        price_layout.addSpacing(30)
        
        price_layout.addWidget(QLabel("RMB价格:"))
        self.price_rmb_input = QLineEdit()
        self.price_rmb_input.setPlaceholderText("0.00")
        self.price_rmb_input.setFixedWidth(100)
        if self.is_edit:
            self.price_rmb_input.setText(str(self.product.get('price_rmb') or ''))
        price_layout.addWidget(self.price_rmb_input)
        
        price_layout.addStretch()
        price_group.setLayout(price_layout)
        scroll_layout.addWidget(price_group)
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("💾 保存")
        save_btn.setFixedWidth(100)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        save_btn.clicked.connect(self.save)
        btn_layout.addWidget(save_btn)
        
        main_layout.addLayout(btn_layout)
    
    def refresh_codes_table(self):
        self.codes_table.setRowCount(0)
        for code in self.codes:
            row = self.codes_table.rowCount()
            self.codes_table.insertRow(row)
            
            self.codes_table.setItem(row, 0, QTableWidgetItem(code.get('product_code', '')))
            
            is_primary = QCheckBox()
            is_primary.setChecked(code.get('is_primary', False))
            is_primary.clicked.connect(lambda checked, cid=code.get('id'): self.set_primary_code(cid))
            self.codes_table.setCellWidget(row, 1, is_primary)
            
            delete_btn = QPushButton("删除")
            delete_btn.setStyleSheet("color: #ef4444; border: none;")
            delete_btn.clicked.connect(lambda checked, cid=code.get('id'): self.delete_code(cid))
            self.codes_table.setCellWidget(row, 2, delete_btn)
    
    def refresh_oes_table(self):
        self.oes_table.setRowCount(0)
        for oe in self.oes:
            row = self.oes_table.rowCount()
            self.oes_table.insertRow(row)
            
            self.oes_table.setItem(row, 0, QTableWidgetItem(oe.get('oe_number', '')))
            
            is_primary = QCheckBox()
            is_primary.setChecked(oe.get('is_primary', False))
            is_primary.clicked.connect(lambda checked, oid=oe.get('id'): self.set_primary_oe(oid))
            self.oes_table.setCellWidget(row, 1, is_primary)
            
            delete_btn = QPushButton("删除")
            delete_btn.setStyleSheet("color: #ef4444; border: none;")
            delete_btn.clicked.connect(lambda checked, oid=oe.get('id'): self.delete_oe(oid))
            self.oes_table.setCellWidget(row, 2, delete_btn)
    
    def add_code(self):
        code, ok = QInputDialog.getText(self, "添加编号", "请输入编号：")
        if ok and code.strip():
            self.codes.append({
                'id': None,
                'product_code': code.strip(),
                'is_primary': len(self.codes) == 0
            })
            self.refresh_codes_table()
    
    def delete_code(self, code_id):
        self.codes = [c for c in self.codes if c.get('id') != code_id]
        self.refresh_codes_table()
    
    def set_primary_code(self, code_id):
        for code in self.codes:
            code['is_primary'] = (code.get('id') == code_id)
        self.refresh_codes_table()
    
    def import_codes_batch(self):
        dialog = BatchImportDialog("批量导入编号", self)
        if dialog.exec():
            items = dialog.get_items()
            set_first = dialog.is_set_first_primary()
            
            for idx, item in enumerate(items):
                self.codes.append({
                    'id': None,
                    'product_code': item,
                    'is_primary': (idx == 0 and set_first and not any(c.get('is_primary') for c in self.codes))
                })
            
            self.refresh_codes_table()
    
    def add_oe(self):
        oe, ok = QInputDialog.getText(self, "添加OE号", "请输入OE号：")
        if ok and oe.strip():
            self.oes.append({
                'id': None,
                'oe_number': oe.strip(),
                'is_primary': len(self.oes) == 0
            })
            self.refresh_oes_table()
    
    def delete_oe(self, oe_id):
        self.oes = [o for o in self.oes if o.get('id') != oe_id]
        self.refresh_oes_table()
    
    def set_primary_oe(self, oe_id):
        for oe in self.oes:
            oe['is_primary'] = (oe.get('id') == oe_id)
        if not any(o.get('is_primary') for o in self.oes) and self.oes:
            self.oes[0]['is_primary'] = True
        self.refresh_oes_table()
    
    def import_oes_batch(self):
        dialog = BatchImportDialog("批量导入OE号", self)
        if dialog.exec():
            items = dialog.get_items()
            set_first = dialog.is_set_first_primary()
            
            for idx, item in enumerate(items):
                self.oes.append({
                    'id': None,
                    'oe_number': item,
                    'is_primary': (idx == 0 and set_first and not any(o.get('is_primary') for o in self.oes))
                })
            
            self.refresh_oes_table()
    
    def load_main_image(self, url):
        try:
            url = _normalize_image_url(url)
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                image_data = response.read()
            
            image = QImage.fromData(image_data)
            if image:
                pixmap = QPixmap.fromImage(image).scaled(196, 196, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.main_image_label.setPixmap(pixmap)
                self.main_image_label.setText("")
                self.main_image_url = url
        except Exception as e:
            print(f"加载主图失败: {e}")
    
    def _apply_category_lock(self):
        """类目两个字段都有实际内容时锁定，不可再次编辑"""
        level1_code = self.category_filter_level1.currentData()
        level2_code = self.category_filter_level2.currentData()
        has_content = bool(level1_code and level1_code != 0 and level2_code and level2_code != 0)
        if has_content:
            self.category_filter_level1.setEnabled(False)
            self.category_filter_level2.setEnabled(False)
            tooltip = "产品类目已设置，不可再次修改"
            self.category_filter_level1.setToolTip(tooltip)
            self.category_filter_level2.setToolTip(tooltip)
            print(f"[客户产品] 类目已锁定: level1={level1_code}, level2={level2_code}")

    def _get_customer_code(self) -> str:
        """根据当前选中的客户获取客户编号"""
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            return ""
        for c in self.customers:
            if c.get("id") == customer_id:
                return (c.get("customer_code") or "").strip()
        return ""

    def _auto_fill_primary_code(self):
        """自动填充客户产品编号：优先显示已有主编号，否则按客户编号+客户型号生成"""
        primary = next((c for c in self.codes if c.get("is_primary")), None)
        if primary:
            self.primary_code_edit.setText(primary.get("product_code", ""))
            return

        customer_code = self._get_customer_code()
        customer_model = self.model_input.text().strip()
        if customer_code and customer_model:
            new_code = f"{customer_code}{customer_model}"
            self.codes.append({
                "id": None,
                "product_code": new_code,
                "is_primary": True,
            })
            self.primary_code_edit.setText(new_code)
            self.refresh_codes_table()
        else:
            self.primary_code_edit.setText("")

    def _update_modify_code_button_state(self):
        """编号只能修改一次，修改后禁用按钮"""
        self.modify_code_btn.setEnabled(not self._primary_code_modified)
        if self._primary_code_modified:
            self.modify_code_btn.setToolTip("编号已修改过，不可再次修改")
        else:
            self.modify_code_btn.setToolTip("只能修改一次")

    def _on_modify_primary_code(self):
        """修改客户产品编号（一次机会）"""
        if self._primary_code_modified:
            QMessageBox.information(self, "提示", "客户产品编号只能修改一次")
            return

        current = self.primary_code_edit.text().strip()
        new_code, ok = QInputDialog.getText(
            self,
            "修改客户产品编号",
            "请输入新的客户产品编号（只能修改一次，保存后生效）：",
            text=current,
        )
        if not ok:
            return

        new_code = new_code.strip()
        if not new_code:
            QMessageBox.warning(self, "警告", "编号不能为空")
            return
        if any(c.get("product_code") == new_code for c in self.codes):
            QMessageBox.warning(self, "警告", f"编号 {new_code} 已存在")
            return

        # 二次确认
        reply = QMessageBox.question(
            self,
            "确认修改",
            f"确定将客户产品编号修改为 {new_code} 吗？\n修改后不可再次修改。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # 替换当前主编号
        primary_idx = next(
            (i for i, c in enumerate(self.codes) if c.get("is_primary")), None
        )
        if primary_idx is not None:
            self.codes[primary_idx]["product_code"] = new_code
        else:
            self.codes.append({
                "id": None,
                "product_code": new_code,
                "is_primary": True,
            })

        self.primary_code_edit.setText(new_code)
        self._primary_code_modified = True
        self._update_modify_code_button_state()
        self.refresh_codes_table()

    def _auto_generate_primary_code(self):
        """自动生成客户产品编号：客户编号 + 客户型号"""
        customer_code = self._get_customer_code()
        model = self.model_input.text().strip()
        if not customer_code:
            QMessageBox.warning(self, "警告", "请先选择客户")
            return
        if not model:
            QMessageBox.warning(self, "警告", "请输入客户型号")
            return
        new_code = f"{customer_code}{model}"
        # 避免重复添加
        if any(c.get("product_code") == new_code for c in self.codes):
            QMessageBox.information(self, "提示", f"编号 {new_code} 已存在")
            return
        # 新添加的自动设为主编号
        self.codes.append({
            "id": None,
            "product_code": new_code,
            "is_primary": True,
        })
        # 取消其他主编号
        for c in self.codes[:-1]:
            c["is_primary"] = False
        self.refresh_codes_table()
        QMessageBox.information(self, "成功", f"已生成客户产品编号：{new_code}")

    def on_category_level1_changed(self):
        """一级类别变化时更新二级类别选项"""
        parent_code = self.category_filter_level1.currentData()
        self.category_filter_level2.clear()
        self.category_filter_level2.addItem("-- 请选择子类 --", 0)
        
        print(f"[客户产品] 一级类别变化: {parent_code}")
        
        if parent_code and parent_code != 0:
            child_options = get_child_category_options(parent_code)
            print(f"[客户产品] 找到 {len(child_options)} 个子类别")
            for code, name in child_options:
                self.category_filter_level2.addItem(name, code)
    
    def upload_main_image(self):
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.upload_main_btn.setEnabled(False)
            self.upload_main_btn.setText("上传中...")
            
            self.upload_worker = ImageUploadWorker(self.api_client, file_path)
            self.upload_worker.finished.connect(self.on_main_image_uploaded)
            self.upload_worker.start()
    
    def on_main_image_uploaded(self, url, success, message):
        self.upload_main_btn.setEnabled(True)
        self.upload_main_btn.setText("上传主图")

        if success:
            # 2026-06-23：去掉 QMessageBox 模态弹窗（阻塞 Dialog，用户无法继续填其他字段）
            # 改为 inline 提示（在主图区域显示上传状态）
            self._show_main_image_status("✓ 上传成功", success=True)
            self._load_main_image_async(url)
        else:
            # 失败也用 inline 提示，避免模态阻塞
            self._show_main_image_status(f"✗ {message}", success=False)

    def _show_main_image_status(self, text: str, success: bool = True):
        """2026-06-23：在主图下方显示上传状态（inline 提示，不阻塞 Dialog）"""
        color = "#10b981" if success else "#dc2626"
        if not hasattr(self, 'main_image_status_label') or self.main_image_status_label is None:
            # 第一次调用时创建 status label
            from PySide6.QtWidgets import QLabel
            self.main_image_status_label = QLabel("")
            self.main_image_status_label.setStyleSheet(f"color: {color}; font-size: 11px;")
            self.main_image_status_label.setAlignment(Qt.AlignCenter)
            # 找到主图按钮的 layout，插入 status
            parent_layout = self.upload_main_btn.parent().layout() if self.upload_main_btn.parent() else None
            if parent_layout:
                parent_layout.addWidget(self.main_image_status_label)
        self.main_image_status_label.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.main_image_status_label.setText(text)
        # 3 秒后自动清除（成功提示）
        if success:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, lambda: self.main_image_status_label.setText("") if hasattr(self, 'main_image_status_label') and self.main_image_status_label else None)

    def _load_main_image_async(self, url: str):
        """2026-06-23：异步下载并显示主图（之前用同步 urllib 在主线程，大图会卡 UI）"""
        self.load_main_image_worker = ImageLoadWorker(url, 196, 196)
        self.load_main_image_worker.finished.connect(self._on_main_image_loaded)
        self.load_main_image_worker.error.connect(lambda u, m: print(f"[主图] 加载失败: {m}"))
        self.load_main_image_worker.start()

    def _on_main_image_loaded(self, url: str, pixmap: QPixmap):
        """主图异步加载完成回调"""
        self.main_image_label.setPixmap(pixmap)
        self.main_image_label.setText("")
        self.main_image_url = url

    def clear_main_image(self):
        self.main_image_label.clear()
        self.main_image_label.setText("点击上传主图")
        self.main_image_url = None
    
    def add_sub_image(self):
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.sub_upload_worker = ImageUploadWorker(self.api_client, file_path)
            self.sub_upload_worker.finished.connect(self.on_sub_image_uploaded)
            self.sub_upload_worker.start()

    def on_sub_image_uploaded(self, url, success, message):
        if success:
            self.sub_image_widget.add_image(url)
            # 2026-06-23：去掉 QMessageBox 模态弹窗（阻塞 Dialog，无法继续操作其他区域）
            # 副图区域有内置的 + 添加图片 按钮，add_image 调用本身会更新 UI
        else:
            print(f"[副图] 上传失败: {message}")
    
    def save(self):
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            QMessageBox.warning(self, "警告", "请选择客户")
            return
        
        product_name = self.name_input.text().strip()
        if not product_name:
            QMessageBox.warning(self, "警告", "请输入产品名称")
            return
        
        new_category_id = self.category_filter_level2.currentData()
        previous_category_id = self.product.get('category_id') if self.is_edit else None
        if new_category_id and new_category_id != 0 and not previous_category_id:
            reply = QMessageBox.question(
                self,
                "确认产品类目",
                f"产品类目设置为 {self.category_filter_level2.currentText()} 后将无法再次修改，是否确认？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        # 2026-07-03 新增：保存时如果没有编号，自动生成 客户编号 + 客户型号
        if not self.codes:
            customer_code = self._get_customer_code()
            model = self.model_input.text().strip()
            if customer_code and model:
                self.codes.append({
                    "id": None,
                    "product_code": f"{customer_code}{model}",
                    "is_primary": True,
                })
                self.refresh_codes_table()

        data = {
            'customer_id': customer_id,
            'product_name': product_name,
            'category_id': new_category_id,
            'customer_model': self.model_input.text().strip(),
            'color': self.color_input.text().strip(),
            'customer_remark': self.remark_input.toPlainText().strip(),
            'price_usd': float(self.price_usd_input.text()) if self.price_usd_input.text() else None,
            'price_rmb': float(self.price_rmb_input.text()) if self.price_rmb_input.text() else None,
        }
        
        if hasattr(self, 'main_image_url') and self.main_image_url:
            data['image_url'] = self.main_image_url
        
        data['sub_images'] = self.sub_image_widget.get_images()
        data['codes'] = [c.get('product_code') for c in self.codes if not c.get('id')]
        data['oes'] = [o.get('oe_number') for o in self.oes if not o.get('id')]
        
        try:
            if self.is_edit:
                product_id = self.product.get('id')
                resp = self.api_client.put(f"/customer-products/{product_id}", data)
                
                for c in self.codes:
                    if not c.get('id'):
                        self.api_client.post(f"/customer-products/{product_id}/codes", {
                            'product_code': c.get('product_code'),
                            'is_primary': c.get('is_primary', False)
                        })
                
                for o in self.oes:
                    if not o.get('id'):
                        self.api_client.post(f"/customer-products/{product_id}/oes", {
                            'oe_number': o.get('oe_number'),
                            'is_primary': o.get('is_primary', False)
                        })
            else:
                resp = self.api_client.post("/customer-products", data)
            
            QMessageBox.information(self, "成功", "保存成功")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {e}")