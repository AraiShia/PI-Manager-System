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


class ImageLoadWorker(QThread):
    """异步图片加载工作线程"""
    finished = Signal(str, QPixmap)
    error = Signal(str, str)
    
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
    
    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                image_data = response.read()
            
            image = QImage.fromData(image_data)
            if image:
                pixmap = QPixmap.fromImage(image).scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.finished.emit(self.url, pixmap)
            else:
                self.error.emit(self.url, "无法解析图片")
        except Exception as e:
            self.error.emit(self.url, str(e))


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
        add_btn.clicked.connect(self._add_new_image)
        add_layout.addWidget(add_btn)

        grid_layout.addWidget(add_widget, add_row, 0, 1, 1)

        self.container_layout.addWidget(grid_widget)
    
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
    
    def _add_new_image(self):
        if hasattr(self.parent(), 'add_sub_image'):
            self.parent().add_sub_image()
    
    def get_images(self):
        return self.images


class CustomerProductDialog(QDialog):
    """客户产品编辑对话框"""
    def __init__(self, api_client: ApiClient, product=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.product = product or {}
        self.is_edit = bool(product and product.get('id'))
        
        self.customers = []
        self.categories = []
        self.codes = []
        self.oes = []
        self.sub_images = []
        self.main_image_url = None
        
        self.setWindowTitle("编辑客户产品" if self.is_edit else "新增客户产品")
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
        
        if self.is_edit:
            product_id = self.product.get('id')
            if product_id:
                try:
                    codes_resp = self.api_client.get(f"/customer-products/{product_id}/codes")
                    if codes_resp and isinstance(codes_resp, list):
                        self.codes = codes_resp
                except Exception as e:
                    print(f"[ERROR] 加载编号失败: {e}")
                
                try:
                    oes_resp = self.api_client.get(f"/customer-products/{product_id}/oes")
                    if oes_resp and isinstance(oes_resp, list):
                        self.oes = oes_resp
                except Exception as e:
                    print(f"[ERROR] 加载OE号失败: {e}")
                
                if self.product.get('sub_images'):
                    try:
                        self.sub_images = json.loads(self.product.get('sub_images')) or []
                    except:
                        self.sub_images = []
        
        QApplication.restoreOverrideCursor()
        
        self.init_ui()
        self.refresh_codes_table()
        self.refresh_oes_table()
    
    def init_ui(self):
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
        
        if self.is_edit and self.product.get('customer_id'):
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
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入产品名称")
        if self.is_edit:
            self.name_input.setText(self.product.get('product_name', ''))
        basic_layout.addRow("产品名称:", self.name_input)
        
        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(200)
        self.category_combo.addItem("-- 请选择类目 --", None)
        for cat in self.categories:
            self.category_combo.addItem(cat.get('name', ''), cat.get('code'))
        
        if self.is_edit and self.product.get('category_id'):
            for i in range(self.category_combo.count()):
                if self.category_combo.itemData(i) == self.product.get('category_id'):
                    self.category_combo.setCurrentIndex(i)
                    break
        
        basic_layout.addRow("产品类目:", self.category_combo)
        
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("默认等于主OE号")
        if self.is_edit:
            self.model_input.setText(self.product.get('customer_model', ''))
        basic_layout.addRow("客户型号:", self.model_input)
        
        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("产品颜色")
        if self.is_edit:
            self.color_input.setText(self.product.get('color', ''))
        basic_layout.addRow("颜色:", self.color_input)
        
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
        sub_image_layout.addWidget(QLabel("副图（横向滚动）"))
        self.sub_image_widget = SubImageWidget(self)
        sub_image_layout.addWidget(self.sub_image_widget)
        
        image_layout.addLayout(sub_image_layout)
        image_group.setLayout(image_layout)
        scroll_layout.addWidget(image_group)
        
        if self.is_edit and self.product.get('image_url'):
            self.load_main_image(self.product.get('image_url'))
        
        for url in self.sub_images:
            self.sub_image_widget.add_image(url)
        
        # 编号管理
        codes_group = QGroupBox("客户产品编号管理")
        codes_layout = QVBoxLayout()
        
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
    
    def upload_main_image(self):
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    files = {'file': (file_path.split('/')[-1], f.read(), 'image/jpeg')}
                    resp = self.api_client.post("/images/upload", files=files)
                    if resp and resp.get('url'):
                        self.load_main_image(resp['url'])
                        QMessageBox.information(self, "成功", "主图上传成功")
                    elif resp and resp.get('message'):
                        QMessageBox.warning(self, "警告", resp.get('message'))
            except Exception as e:
                QMessageBox.warning(self, "错误", f"上传失败: {e}")
    
    def clear_main_image(self):
        self.main_image_label.clear()
        self.main_image_label.setText("点击上传主图")
        self.main_image_url = None
    
    def add_sub_image(self):
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    files = {'file': (file_path.split('/')[-1], f.read(), 'image/jpeg')}
                    resp = self.api_client.post("/images/upload", files=files)
                    if resp and resp.get('url'):
                        self.sub_image_widget.add_image(resp['url'])
                        QMessageBox.information(self, "成功", "副图上传成功")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"上传失败: {e}")
    
    def save(self):
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            QMessageBox.warning(self, "警告", "请选择客户")
            return
        
        product_name = self.name_input.text().strip()
        if not product_name:
            QMessageBox.warning(self, "警告", "请输入产品名称")
            return
        
        data = {
            'customer_id': customer_id,
            'product_name': product_name,
            'category_id': self.category_combo.currentData(),
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