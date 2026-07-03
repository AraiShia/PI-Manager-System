# 单品采购信息编辑表重构设计

## 背景

当前 `product_item_edit_dialog.py` 采用垂直卡片布局，字段分组不够紧凑。用户提供了目标 Excel 表单（`单品采购信息编辑表(1).xlsx`），需要将 Dialog 重构为 **紧凑横向表格布局**，完全符合 Excel 表单的结构。

## 设计目标

1. **完全符合 Excel 表单结构** — 列布局、行合并、单元格合并一一对应
2. **保留所有现有功能** — 数据加载、保存、图片上传、OE 号管理等
3. **提升可维护性** — 移除冗余字段，统一字段映射

## Excel 表单结构分析

### 区域划分

| 区域 | Excel 行 | 说明 |
|---|---|---|
| **头部** | 3-6 | 客户搜索、型号、图片、产品类别 |
| **产品信息** | 7-14 | 要求、颜色、OE 号、客户产品编号、S.NO.、供应商 |
| **销售细节** | 15-17 | QTY、报价、金额、客户需求、答复 |
| **采购信息** | 18-26 | 采购价、供应商、付款、包装规格 |
| **收货入库** | 27-30 | 入库信息、箱规明细 |
| **采购存档** | 31-32 | 合同、发票、运单（未来扩展） |

### 关键合并单元格（共 43 个）

```
头部：
  L3:N3    → 客户输入框（跨3列）
  Q3:R3    → 显示客户国家（跨2列）
  L5:M6    → 客户型号（跨2行2列）
  N5:N6    → 产品名称（跨2行）
  O5:R6    → 产品名称值（跨2行4列）
  K7:K8    → 产品要求标签
  L7:N8    → 产品要求值
  K9:K14   → OE号/OE-NO.列表
  N9:N14   → 客户产品编号
  Q9:Q10   → 我司产编号
  R9:R10   → S.NO.值
  O7:O8    → 产品颜色标签
  P7:R8    → 产品颜色值
  Q11:Q12  → 优选供应商标签
  R11:R12  → 供应商名
  Q13:Q14  → 产品名称标签
  R13:R14  → 产品名称值

销售细节：
  K15:K17  → 销售细节标签
  M15:N15  → 综合毛利额

采购信息：
  K18:K26  → 采购信息标签
  Q18:R18  → 开票情况标签
  L20:M20  → 供应商标签
  N20:O20  → 供应商名值
  P20:P21  → 采购备注标签
  Q20:R21  → 采购备注值
  L21:M21  → 供应商链接标签
  N21:O21  → 链接值
  L22:M22  → 采购方式标签
  N22:O22  → 采购方式值
  L23:M23  → 付款方式标签
  N23:O23  → 付款方式值
  P22:R23  → 付款1/2/未付款
  L24:M24  → 开票工厂标签
  Q24:R24  → 货源地

包装规格：
  L25:N25  → 纸箱包装标签（跨3列）
  T25:T26  → 预估包装信息
  T28:T30  → 箱规明细说明
```

### 颜色规范

| 元素 | 颜色 |
|---|---|
| 必填标签文字 | #FF0000（红色） |
| 一般标签文字 | 默认色 |
| 灰色背景行 | 浅灰（销售/采购区域） |
| 分组标题 | 灰色背景 + 标签文字 |

## 实现方案

### 技术选型

使用 `QTableWidget` 作为主容器，通过以下特性实现：

1. **`setSpan(row, col, rowSpan, colSpan)`** — 合并单元格
2. **`setCellWidget(row, col, widget)`** — 单元格内嵌 widget
3. **`setItem(row, col, QTableWidgetItem)`** — 普通文本单元格
4. **Stylesheet** — 边框、背景、字体样式

### PySide 代码结构

```python
class SingleOrderDialog(QDialog):
    """单品采购信息编辑表 Dialog - 基于 Excel 表单布局"""

    def __init__(self, item, ...):
        super().__init__(parent)
        self.setWindowTitle("单品采购信息编辑表")
        self.setMinimumSize(1200, 900)
        self._init_table()
        self._apply_styles()
        self._populate_data(item)

    def _init_table(self):
        """初始化表格结构"""
        self.table = QTableWidget()
        self.table.setColumnCount(20)  # A-T 列（Excel 列）
        self.table.setRowCount(32)      # 1-32 行

        # 设置行高
        for row, height in ROW_HEIGHTS.items():
            self.table.setRowHeight(row, height)

        # 设置列宽
        for col, width in COLUMN_WIDTHS.items():
            self.table.setColumnWidth(col, width)

        # 合并单元格
        self._merge_cells()

        # 填充标签和控件
        self._fill_labels()
        self._fill_widgets()

    def _merge_cells(self):
        """合并单元格 — 完全对应 Excel"""
        merges = [
            (2, 11, 1, 3),   # L3:N3 客户输入框
            (2, 16, 1, 2),   # Q3:R3 显示客户国家
            # ... 43 个合并
        ]
        for row, col, rs, cs in merges:
            self.table.setSpan(row, col, rs, cs)
```

### 字段映射

| Excel 位置 | 字段名 | 数据路径 |
|---|---|---|
| K3 | customer_id | item.customer_id |
| L3 | customer_name | item.customer.name |
| L5 | customer_model | item.customer_model |
| O5 | product_name | item.product_name |
| O6 | product_name_en | item.product_name_en |
| L7 | p_details | item.detail_desc |
| P7 | p_color | item.color |
| K9 | oe_numbers | item.codes[].oe_number |
| N9 | customer_codes | item.codes[].customer_code |
| R9 | system_code | item.system_code |
| L16 | qty | item.quantity |
| M16 | unit_price | item.unit_price |
| N16 | total_price | item.total_price (= calc) |
| L18 | rmb_price | item.rmb_price |
| L20 | supplier_name | item.supplier.name |
| Q20 | purchase_notes | item.purchase_notes |
| L22 | purchase_method | item.purchase_method |
| L23 | payment_method | item.payment_method |
| L25 | carton_size | item.carton_size |
| O25 | packing_spec | item.units_per_carton |
| L27 | received_qty | item.received_qty |
| L28+ | carton_details | item.carton_details[] |

## 渲染步骤

1. **`__init__`** — 创建表格、设置行列数
2. **`_init_table`** — 设置固定行高列宽
3. **`_merge_cells`** — 执行 43 个合并操作
4. **`_fill_labels`** — 填充静态标签文本
5. **`_fill_widgets`** — 嵌入输入框、下拉框、按钮
6. **`_apply_styles`** — 应用 stylesheet
7. **`_populate_data`** — 填充已有数据
8. **`get_item`** — 收集用户输入返回

## 样式表

```css
QTableWidget {
    border: 1px solid #d1d5db;
    gridline-color: #d1d5db;
    background: white;
}
QTableWidget::item {
    padding: 0;
    border: 1px solid #d1d5db;
}
QLabel {
    padding: 4px 8px;
    background: transparent;
}
.required-label {
    color: #dc2626;
    font-weight: 600;
}
.group-label {
    background: #f3f4f6;
    color: #374151;
    font-weight: 600;
}
```

## 待实现文件

- `client/widgets/single_order_dialog.py` — 完全重写

## 测试要点

1. 32 行 × 20 列表格正确渲染
2. 43 个合并单元格位置正确
3. 输入框、下拉框在对应单元格内
4. 图片上传/预览功能正常
5. 保存后数据正确映射回 item
6. 销售毛利自动计算
7. 付款金额自动计算
