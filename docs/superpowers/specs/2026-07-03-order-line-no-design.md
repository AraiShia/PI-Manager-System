# 订单行号追踪与排序恢复设计

## 背景

订单从 Excel 导入后，用户需要能够：
1. 了解产品在原始 Excel 中的顺序
2. 解锁表格列进行排序操作
3. 排序错乱后能快速恢复到原始导入顺序

当前问题：
- 表格排序功能已禁用
- 无法追踪原始导入顺序
- 排序后无法恢复到原始状态

## 设计目标

1. 在"订单日期"列前新增"行号"列，显示原始 Excel 行号
2. 行号绑定产品 ID，排序不会改变绑定关系
3. 解锁其他列的排序功能
4. 点击行号列标题，按行号升序排列恢复到原始导入顺序

## 数据库设计

### 新增字段

**表：`pi_proforma_invoice_item`**

| 字段 | 类型 | 说明 |
|------|------|------|
| `line_no` | INT | 原始 Excel 行号，1-based。允许 NULL（历史数据兼容） |

### 迁移脚本

```sql
-- 2026-07-03: 新增 line_no 字段用于追踪原始导入顺序
ALTER TABLE pi_proforma_invoice_item
ADD COLUMN line_no INT DEFAULT NULL COMMENT '原始 Excel 行号，1-based';

-- 为 line_no 添加索引，提升排序查询性能
CREATE INDEX idx_pi_item_line_no ON pi_proforma_invoice_item(pi_id, line_no);

-- 历史数据兼容：line_no 为 NULL 时按 id 顺序处理
```

## 后端设计

### 1. 模型变更

**文件：`backend/models/pi.py`**

在 `PiProformaInvoiceItem` 类中新增字段：

```python
line_no = Column(Integer, nullable=True)  # 原始 Excel 行号，1-based
```

### 2. 导入逻辑变更

**文件：`backend/routers/order_import.py`**

在 `_create_pi_order` 函数中，创建 Item 时写入 `line_no`：

```python
# 创建Items时记录原始行号
for idx, item_data in enumerate(items, start=1):
    item = PiProformaInvoiceItem(
        ...
        line_no=idx,  # 1-based 行号
        ...
    )
```

### 3. 查询逻辑变更

**文件：`backend/routers/pi.py`**

获取订单详情时，按 `line_no` 排序返回：

```python
# 查询 PI Items 时按 line_no 排序，保持原始导入顺序
items = db.query(PiProformaInvoiceItem).filter(
    PiProformaInvoiceItem.pi_id == pi_id,
    PiProformaInvoiceItem.is_deleted == False
).order_by(PiProformaInvoiceItem.line_no.asc()).all()

# line_no 为 NULL 时（历史数据），按 id 排序
items = db.query(PiProformaInvoiceItem).filter(
    PiProformaInvoiceItem.pi_id == pi_id,
    PiProformaInvoiceItem.is_deleted == False
).order_by(
    PiProformaInvoiceItem.line_no.asc().nullslast()
).all()
```

### 4. Schema 变更

**文件：`backend/schemas/pi_detail.py`**

在 `PiItemResponse` 中新增 `line_no` 字段：

```python
class PiItemResponse(BaseModel):
    ...
    line_no: Optional[int] = None  # 原始 Excel 行号
```

## 前端设计

### 1. 常量变更

**文件：`client/widgets/order_summary/constants.py`**

在 `ORDER_DETAIL_HEADERS` 首位插入"行号"：

```python
ORDER_DETAIL_HEADERS = [
    "行号",                      # 0 新增
    "订单日期",                  # 1 原 0
    "ORDER NO.",                 # 2 原 1
    # ... 后续列索引 +1
]
```

更新 `LOCKED` 集合，包含新的行号列索引：

```python
LOCKED = {0, 3, 6, 7, 10, 11, 12, 18, 19, 20, 21, 22, 37, 41}
# 行号列索引为 0，永久锁定在第一列
```

### 2. 表格渲染变更

**文件：`client/widgets/order_summary/order_detail_panel.py`**

在 `_render_items` 方法中，每行首位显示行号：

```python
def _render_items(self, order, items):
    for row, item in enumerate(items):
        # ===== Col 0: 行号 =====
        line_no = item.get('line_no') or row + 1  # fallback 到数组索引
        self._table.setItem(row, 0, QTableWidgetItem(str(line_no)))
        self._table.item(row, 0).setTextAlignment(Qt.AlignCenter)
        self._table.item(row, 0).setForeground(QBrush(QColor(COLORS['readonly_fg'])))
        self._table.item(row, 0).setData(Qt.ItemDataRole.UserRole, 'readonly')
```

### 3. 排序交互

**文件：`client/widgets/order_summary/order_detail_panel.py`**

启用行号列排序，其他列也可排序：

```python
def _create_table(self):
    table = QTableWidget()
    table.setColumnCount(ORDER_DETAIL_COLUMN_COUNT)
    table.setHorizontalHeaderLabels(ORDER_DETAIL_HEADERS)

    # 行号列可排序，点击后按行号升序恢复原始顺序
    header = table.horizontalHeader()
    header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)  # 默认按行号排序
    header.sectionClicked.connect(self._on_header_clicked)

    # 其他列也启用排序
    table.setSortingEnabled(True)
```

排序恢复逻辑：

```python
def _on_header_clicked(self, col_index):
    """点击列标题排序"""
    if col_index == 0:  # 行号列
        # 按 line_no 升序排列（恢复到原始导入顺序）
        self._table.sortItems(col_index, Qt.SortOrder.AscendingOrder)
    # 其他列按默认行为排序

def reset_to_original_order(self):
    """恢复到原始导入顺序（按行号排序）"""
    self._table.sortItems(0, Qt.SortOrder.AscendingOrder)
```

## 数据流

```
Excel 导入
    ↓
backend/routers/order_import.py
    ↓ 创建 PI Items 时写入 line_no=idx
    ↓
数据库 pi_proforma_invoice_item.line_no
    ↓
前端加载订单详情
    ↓ 按 line_no 排序返回
order_detail_panel.py
    ↓
表格首位显示行号，用户可排序
    ↓ 排序错乱时点击行号列恢复
```

## 边界情况

| 场景 | 处理 |
|------|------|
| 历史数据（line_no 为 NULL） | 按 id 升序作为原始顺序 |
| 手动新增的产品 | line_no 为 NULL，按 id 排在最后 |
| 导入时 line_no 与 id 相同 | 行号显示 line_no 值 |
| 用户删除了某行 | 行号不变，保持连续性 |

## 实现清单

### 数据库
- [ ] 编写并执行数据库迁移脚本

### 后端
- [ ] `backend/models/pi.py`：PiProformaInvoiceItem 新增 line_no 字段
- [ ] `backend/schemas/pi_detail.py`：PiItemResponse 新增 line_no
- [ ] `backend/routers/order_import.py`：导入时写入 line_no
- [ ] `backend/routers/pi.py`：查询时按 line_no 排序

### 前端
- [ ] `client/widgets/order_summary/constants.py`：新增"行号"列，更新索引
- [ ] `client/widgets/order_summary/order_detail_panel.py`：渲染行号，启用排序
