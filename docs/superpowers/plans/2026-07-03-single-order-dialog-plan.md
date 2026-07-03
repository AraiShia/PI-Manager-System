# 单条新增 Dialog 简化实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 简化 `SingleOrderDialog`，只保留核心字段（客户、产品搜索、客户产品编号、OE号、数量、单价），去掉产品描述、交货日期、备注。

**架构：** 修改现有 `client/widgets/single_order_dialog.py`，移除多余字段，调整界面布局，保持与 `order_import_dialog.py` 的调用接口不变。

**技术栈：** PySide6、Qt Widgets

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `client/widgets/single_order_dialog.py` | 单条订单快速创建对话框，简化后只包含核心字段 |
| `client/widgets/order_import_dialog.py` | 调用 `SingleOrderDialog` 的父组件，保持接口不变 |

---

### 任务 1：修改 SingleOrderDialog 界面布局

**文件：**
- 修改：`client/widgets/single_order_dialog.py`

- [ ] **步骤 1：修改 init_ui 方法，移除产品描述、交货日期、备注字段**

```python
def init_ui(self):
    """初始化UI"""
    layout = QVBoxLayout(self)
    
    title = QLabel("单条新增订单")
    title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title)
    
    form_layout = QFormLayout()
    
    self.customer_combo = QComboBox()
    self.customer_combo.setMinimumWidth(300)
    self.customer_combo.currentIndexChanged.connect(self.on_customer_changed)
    form_layout.addRow("客户:", self.customer_combo)
    
    self.product_search_input = QLineEdit()
    self.product_search_input.setPlaceholderText("输入OE号或产品名称搜索...")
    self.product_search_input.textChanged.connect(self.on_search_text_changed)
    self.product_search_input.returnPressed.connect(self.select_first_result)
    form_layout.addRow("产品搜索:", self.product_search_input)
    
    self.search_results_list = QListWidget()
    self.search_results_list.setMaximumHeight(120)
    self.search_results_list.setAlternatingRowColors(True)
    self.search_results_list.itemClicked.connect(self.on_result_selected)
    form_layout.addRow("", self.search_results_list)
    
    self.selected_product_label = QLabel("未选择产品")
    self.selected_product_label.setStyleSheet("color: #666; font-style: italic;")
    form_layout.addRow("已选产品:", self.selected_product_label)
    
    self.customer_code_input = QLineEdit()
    self.customer_code_input.setPlaceholderText("客户产品编号")
    form_layout.addRow("客户产品编号:", self.customer_code_input)
    
    self.oe_number_input = QLineEdit()
    self.oe_number_input.setPlaceholderText("OE号")
    form_layout.addRow("OE号:", self.oe_number_input)
    
    self.quantity_spin = QSpinBox()
    self.quantity_spin.setMinimum(1)
    self.quantity_spin.setMaximum(999999)
    self.quantity_spin.setValue(1)
    self.quantity_spin.valueChanged.connect(self.calculate_amount)
    form_layout.addRow("数量:", self.quantity_spin)
    
    self.unit_price_spin = QDoubleSpinBox()
    self.unit_price_spin.setMinimum(0.01)
    self.unit_price_spin.setMaximum(999999.99)
    self.unit_price_spin.setDecimals(2)
    self.unit_price_spin.setPrefix("$ ")
    self.unit_price_spin.valueChanged.connect(self.calculate_amount)
    form_layout.addRow("单价(USD):", self.unit_price_spin)
    
    self.amount_label = QLabel("$ 0.00")
    self.amount_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
    form_layout.addRow("合计金额:", self.amount_label)
    
    layout.addLayout(form_layout)
    
    btn_layout = QHBoxLayout()
    btn_layout.addStretch()
    
    cancel_btn = QPushButton("取消")
    cancel_btn.clicked.connect(self.reject)
    cancel_btn.setStyleSheet("padding: 8px 16px;")
    btn_layout.addWidget(cancel_btn)
    
    save_btn = QPushButton("保存")
    save_btn.clicked.connect(self.save_order)
    save_btn.setStyleSheet("""
        QPushButton {
            background-color: #10b981;
            color: white;
            font-weight: bold;
            padding: 8px 20px;
        }
        QPushButton:hover {
            background-color: #059669;
        }
    """)
    btn_layout.addWidget(save_btn)
    
    layout.addLayout(btn_layout)
    
    self.search_timer = QTimer()
    self.search_timer.setSingleShot(True)
    self.search_timer.timeout.connect(self.perform_search)
```

- [ ] **步骤 2：修改 on_result_selected 方法，只填充保留的字段**

```python
def on_result_selected(self, item):
    """选择搜索结果"""
    if not item:
        return
    
    product = item.data(Qt.ItemDataRole.UserRole)
    if not product:
        return
    
    self.selected_product = product
    self.selected_product_label.setText(
        f"{product.get('oe_number', '')} - {product.get('detail_desc', '')}"
    )
    self.selected_product_label.setStyleSheet("color: #10b981; font-weight: bold;")
    
    self.oe_number_input.setText(product.get('oe_number', ''))
    self.customer_code_input.setText(product.get('customer_code', ''))
    
    if product.get('unit_price'):
        self.unit_price_spin.setValue(float(product.get('unit_price')))
    elif product.get('price_usd'):
        self.unit_price_spin.setValue(float(product.get('price_usd')))
```

- [ ] **步骤 3：修改 save_order 方法，只收集保留的字段**

```python
def save_order(self):
    """保存订单 / 补充单条产品"""
    if self.customer_combo.currentIndex() < 0:
        QMessageBox.warning(self, "提示", "请选择客户")
        return

    customer_id = self.customer_combo.currentData()
    product_id = self.selected_product.get('id') if self.selected_product else None

    product_data = {
        'customer_id': customer_id,
        'product_id': product_id,
        'customer_code': self.customer_code_input.text(),
        'oe_number': self.oe_number_input.text(),
        'quantity': self.quantity_spin.value(),
        'unit_price': float(self.unit_price_spin.value()),
    }

    if not product_data['customer_code']:
        QMessageBox.warning(self, "提示", "请输入客户产品编号")
        return
    if not product_data['oe_number']:
        QMessageBox.warning(self, "提示", "请输入OE号")
        return

    if self._mode == 'supplement':
        self._captured_product_data = product_data
        self.accept()
        return

    try:
        response = self.api_client.post("/orders/single", data=product_data)
        if response and response.get('success'):
            QMessageBox.information(self, "成功", f"订单创建成功！\nPI号: {response.get('pi_no', '')}")
            self.accept()
        else:
            QMessageBox.warning(self, "错误", response.get('error', '创建失败') if response else '创建失败')
    except Exception as e:
        QMessageBox.warning(self, "错误", f"创建订单失败: {str(e)}")
```

- [ ] **步骤 4：调整对话框最小尺寸**

```python
self.setMinimumSize(500, 400)
```

- [ ] **步骤 5：语法检查**

```bash
cd e:\AI\TraeProject\PI-Manager-System\client
python -m py_compile widgets/single_order_dialog.py
```

预期：无错误。

- [ ] **步骤 6：Commit**

```bash
git add client/widgets/single_order_dialog.py
git commit -m "feat(client): simplify SingleOrderDialog with core fields only"
```

---

### 任务 2：更新 order_import_dialog.py 中 _add_single_product_to_preview 方法

**文件：**
- 修改：`client/widgets/order_import_dialog.py`

- [ ] **步骤 1：修改 _add_single_product_to_preview 方法，适配新的数据结构**

```python
def _add_single_product_to_preview(self, product_data: dict):
    """将单条产品数据添加到预览表格"""
    if not self.preview_table:
        return

    if self.preview_data is None:
        self.preview_data = {'headers': [], 'rows': [], 'total': 0}

    self.preview_data['rows'].append(product_data)
    self.preview_data['total'] = len(self.preview_data['rows'])

    if self.preview_table.columnCount() == 0:
        headers = ['行号', '客户产品编号', 'OE号', '数量', '单价', '状态']
        self.preview_table.setColumnCount(len(headers))
        self.preview_table.setHorizontalHeaderLabels(headers)

    row_idx = self.preview_table.rowCount()
    self.preview_table.insertRow(row_idx)

    from PySide6.QtWidgets import QTableWidgetItem
    from PySide6.QtGui import QColor

    self.preview_table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))
    self.preview_table.setItem(row_idx, 1, QTableWidgetItem(product_data.get('customer_code', '')))
    self.preview_table.setItem(row_idx, 2, QTableWidgetItem(product_data.get('oe_number', '') or ''))
    self.preview_table.setItem(row_idx, 3, QTableWidgetItem(str(product_data.get('quantity', 1))))

    price = product_data.get('unit_price')
    price_str = f"${price:.2f}" if price else ''
    self.preview_table.setItem(row_idx, 4, QTableWidgetItem(price_str))

    status_item = QTableWidgetItem('正式')
    self.preview_table.setItem(row_idx, 5, status_item)

    total_rows = self.preview_table.rowCount()

    self.preview_status_label.setText(
        f"共 {total_rows} 行数据（手动添加 {total_rows} 条）"
    )

    self.import_btn.setEnabled(True)

    for col in range(self.preview_table.columnCount()):
        item = self.preview_table.item(row_idx, col)
        if item:
            item.setBackground(QColor("#dbeafe"))

    QMessageBox.information(
        self,
        "成功",
        f"产品已添加到预览列表\n"
        f"客户产品编号: {product_data.get('customer_code')}\n"
        f"数量: {product_data.get('quantity')}"
    )
```

- [ ] **步骤 2：语法检查**

```bash
cd e:\AI\TraeProject\PI-Manager-System\client
python -m py_compile widgets/order_import_dialog.py
```

预期：无错误。

- [ ] **步骤 3：Commit**

```bash
git add client/widgets/order_import_dialog.py
git commit -m "feat(client): update _add_single_product_to_preview for simplified fields"
```

---

### 任务 3：集成测试

**文件：**
- 测试：`client/widgets/single_order_dialog.py`
- 测试：`client/widgets/order_import_dialog.py`

- [ ] **步骤 1：运行 py_compile 检查**

```bash
cd e:\AI\TraeProject\PI-Manager-System\client
python -m py_compile widgets/single_order_dialog.py
python -m py_compile widgets/order_import_dialog.py
python -m py_compile main.py
```

预期：所有文件编译通过。

- [ ] **步骤 2：Commit**

```bash
git commit --allow-empty -m "test: single order dialog simplification smoke test"
```

---

## 自检

**1. 规格覆盖度：**
- ✅ 客户字段保留
- ✅ 产品搜索保留
- ✅ 客户产品编号保留
- ✅ OE号保留
- ✅ 数量保留
- ✅ 单价保留
- ✅ 产品描述移除
- ✅ 交货日期移除
- ✅ 备注移除

**2. 占位符扫描：** 无占位符

**3. 类型一致性：** `product_data` 结构与 `order_import_dialog.py` 的 `_add_single_product_to_preview` 方法一致

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-07-03-single-order-dialog-plan.md`。两种执行方式：

1. **子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

2. **内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

选哪种方式？
