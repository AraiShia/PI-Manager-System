# 订单内重复产品检测实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在售前预览阶段检测同一订单内重复产品并提示用户，导入后在订单详情面板高亮重复行。

**架构：** 新增纯函数工具模块 `client/utils/duplicate_detector.py` 负责提取判定键和分组；`OrderImportDialog` 在预览加载和单条新增后调用该模块刷新高亮与状态，并在导入前弹窗让用户选择继续/跳过/取消；`OrderDetailPanel` 在渲染订单详情时统计重复行并设置浅黄背景。

**技术栈：** PySide6, Python 3.x

---

## 文件清单

- **创建** `client/utils/duplicate_detector.py`：提供预览行与订单项的重复判定键提取、重复分组、去重索引计算。
- **创建** `tests/client/utils/test_duplicate_detector.py`：`duplicate_detector` 的单元测试。
- **修改** `client/widgets/order_import_dialog.py`：在预览表加载、单条新增、删除行后刷新重复高亮；导入前弹窗处理；补充模式不再自动跳过已存在产品。
- **修改** `client/widgets/order_summary/order_detail_panel.py`：在订单详情渲染后高亮重复行。

---

## 任务 1：创建重复检测工具模块及测试

**文件：**
- 创建：`client/utils/duplicate_detector.py`
- 创建：`tests/client/utils/test_duplicate_detector.py`

### 步骤 1：编写失败的测试

创建 `tests/client/utils/test_duplicate_detector.py`：

```python
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'client'))

from utils.duplicate_detector import (
    extract_preview_duplicate_key,
    find_preview_duplicates,
    filter_duplicate_indices,
)


class TestDuplicateDetector(unittest.TestCase):
    def test_dict_with_product_id(self):
        row = {'product_id': 5, 'customer_code': 'C001', 'oe_number': 'OE123'}
        key, display = extract_preview_duplicate_key(row)
        self.assertEqual(key, 'product_id:5')
        self.assertEqual(display, 'C001')

    def test_dict_without_product_id(self):
        row = {'customer_code': 'C001', 'oe_number': 'OE123'}
        key, display = extract_preview_duplicate_key(row)
        self.assertEqual(key, 'code_oe:C001|OE123')
        self.assertEqual(display, 'C001')

    def test_list_with_model(self):
        row = ['A', 'C001', '10']
        headers = ['No', 'Model', 'Qty']
        key, display = extract_preview_duplicate_key(row, headers=headers, model_col_idx=1)
        self.assertEqual(key, 'model:C001')
        self.assertEqual(display, 'C001')

    def test_empty_row_returns_empty_key(self):
        key, display = extract_preview_duplicate_key({})
        self.assertEqual(key, '')
        self.assertEqual(display, '')

    def test_find_duplicates(self):
        rows = [
            {'product_id': 1},
            {'product_id': 2},
            {'product_id': 1},
        ]
        dups = find_preview_duplicates(rows)
        self.assertEqual(len(dups), 1)
        self.assertEqual(dups[0]['indices'], [0, 2])
        self.assertFalse(dups[0]['external'])

    def test_external_existing_keys(self):
        rows = [{'product_id': 1}]
        dups = find_preview_duplicates(rows, existing_keys={'product_id:1'})
        self.assertEqual(len(dups), 1)
        self.assertEqual(dups[0]['indices'], [0])
        self.assertTrue(dups[0]['external'])

    def test_filter_duplicate_indices_keep_first(self):
        rows = [{'product_id': 1}, {'product_id': 2}, {'product_id': 1}]
        dups = find_preview_duplicates(rows)
        keep = filter_duplicate_indices(len(rows), dups)
        self.assertEqual(keep, [0, 1])

    def test_filter_duplicate_indices_skip_external(self):
        rows = [{'product_id': 1}]
        dups = find_preview_duplicates(rows, existing_keys={'product_id:1'})
        keep = filter_duplicate_indices(len(rows), dups)
        self.assertEqual(keep, [])


if __name__ == '__main__':
    unittest.main()
```

### 步骤 2：运行测试验证失败

运行：

```bash
python tests/client/utils/test_duplicate_detector.py
```

预期：失败，提示 `ModuleNotFoundError: No module named 'utils.duplicate_detector'` 或函数未定义。

### 步骤 3：实现工具模块

创建 `client/utils/duplicate_detector.py`：

```python
"""
重复产品检测工具

提供预览行与订单项的重复判定键提取、重复分组、去重索引计算。
"""
from typing import Any, Dict, List, Optional, Set, Tuple


def _normalize(value: Any) -> str:
    """将值规范化为去除首尾空格的字符串，None 返回空字符串。"""
    if value is None:
        return ""
    return str(value).strip()


def extract_preview_duplicate_key(
    row: Any,
    headers: Optional[List[str]] = None,
    model_col_idx: Optional[int] = None,
) -> Tuple[str, str]:
    """
    为预览表中的一行提取重复判定键和展示文本。

    返回 (key, display)。key 为空字符串表示无法判定（不参与重复统计）。
    """
    if isinstance(row, dict):
        product_id = row.get('product_id')
        if product_id is not None and _normalize(product_id):
            display = _normalize(row.get('customer_code') or row.get('oe_number') or product_id)
            return (f"product_id:{product_id}", display)

        code = _normalize(row.get('customer_code', ''))
        oe = _normalize(row.get('oe_number', ''))
        if code or oe:
            display = code or oe
            return (f"code_oe:{code}|{oe}", display)
        return ("", "")

    # Excel 原始行（list / tuple），按 Model/客户产品编号列判定
    if isinstance(row, (list, tuple)) and model_col_idx is not None:
        if 0 <= model_col_idx < len(row):
            model = _normalize(row[model_col_idx])
            if model:
                return (f"model:{model}", model)
    return ("", "")


def find_preview_duplicates(
    rows: List[Any],
    headers: Optional[List[str]] = None,
    model_col_idx: Optional[int] = None,
    existing_keys: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """
    查找预览行中的重复分组。

    Args:
        rows: 预览行列表，元素可以是 dict（手动新增）或 list（Excel 原始行）。
        headers: Excel 表头，用于定位 Model 列（可选）。
        model_col_idx: Model 列在 Excel 行中的索引（可选）。
        existing_keys: 已存在产品的判定键集合（如当前订单已有产品、客户-产品表已有 Model）。

    Returns:
        重复分组列表，每个分组包含：
        - key: 判定键
        - display: 展示文本
        - indices: 在 rows 中出现的索引列表
        - external: 是否仅因与 existing_keys 冲突而标记为重复
    """
    existing_keys = existing_keys or set()
    groups: Dict[str, Dict[str, Any]] = {}

    for idx, row in enumerate(rows):
        key, display = extract_preview_duplicate_key(row, headers, model_col_idx)
        if not key:
            continue
        if key not in groups:
            groups[key] = {
                "key": key,
                "display": display,
                "indices": [],
                "external": False,
            }
        groups[key]["indices"].append(idx)

    duplicates: List[Dict[str, Any]] = []
    for key, group in groups.items():
        if len(group["indices"]) >= 2:
            duplicates.append(group)
        elif key in existing_keys:
            group["external"] = True
            duplicates.append(group)

    duplicates.sort(key=lambda g: g["indices"][0] if g["indices"] else 0)
    return duplicates


def filter_duplicate_indices(
    row_count: int,
    duplicate_groups: List[Dict[str, Any]],
) -> List[int]:
    """
    计算选择"跳过重复行"后应保留的行索引。

    - 内部重复：保留第一次出现，跳过后续。
    - 与外部已存在产品冲突：跳过所有冲突行。
    """
    skip: Set[int] = set()
    for group in duplicate_groups:
        indices = group.get("indices", [])
        if not indices:
            continue
        if group.get("external"):
            skip.update(indices)
        else:
            skip.update(indices[1:])
    return [i for i in range(row_count) if i not in skip]
```

### 步骤 4：运行测试验证通过

运行：

```bash
python tests/client/utils/test_duplicate_detector.py
```

预期：所有 8 个测试通过。

### 步骤 5：Commit

```bash
git add client/utils/duplicate_detector.py tests/client/utils/test_duplicate_detector.py
git commit -m "feat(utils): add duplicate detector for preview rows" -m "- extract duplicate key by product_id, code/oe, or model" -m "- support external existing-key conflicts for supplement mode"
```

---

## 任务 2：在订单导入 Dialog 中集成重复检测

**文件：**
- 修改：`client/widgets/order_import_dialog.py`

### 步骤 1：导入工具函数

在 `client/widgets/order_import_dialog.py` 顶部添加导入：

```python
import os
import sys

# 使 utils 包可被导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.duplicate_detector import (
    extract_preview_duplicate_key,
    find_preview_duplicates,
    filter_duplicate_indices,
)
```

### 步骤 2：单条新增后立即检测并提示

修改 `_add_single_product_to_preview` 方法末尾（在 `QMessageBox.information` 之前或之后均可，推荐在成功提示之后）：

```python
# 新增：刷新重复高亮并提示
self._refresh_duplicate_highlight()
self._warn_if_duplicate_added()
```

新增方法：

```python
def _warn_if_duplicate_added(self):
    """单条新增后若造成重复，立即弹窗提示。"""
    duplicates = getattr(self, '_duplicate_groups', [])
    if not duplicates:
        return
    displays = [g['display'] for g in duplicates[:10]]
    msg = "检测到重复产品：\n" + "\n".join(f"- {d}" for d in displays)
    QMessageBox.information(self, "重复产品提示", msg)
```

### 步骤 3：实现预览表重复高亮

在 `OrderImportDialog` 中新增方法：

```python
def _refresh_duplicate_highlight(self):
    """刷新预览表中重复行的高亮与状态标签。"""
    if not self.preview_table or self.preview_table.rowCount() == 0:
        return

    rows = self.preview_data.get('rows', []) if self.preview_data else []
    headers = self.preview_data.get('headers', [])
    model_col_idx = self._find_model_column(headers) if headers else None

    existing_keys = self._build_existing_duplicate_keys()
    duplicates = find_preview_duplicates(rows, headers, model_col_idx, existing_keys)
    self._duplicate_groups = duplicates

    duplicate_indices = set()
    for group in duplicates:
        duplicate_indices.update(group['indices'])

    yellow = QColor("#fef3c7")
    white = QColor("#ffffff")
    for r in range(self.preview_table.rowCount()):
        bg = yellow if r in duplicate_indices else white
        for c in range(self.preview_table.columnCount()):
            item = self.preview_table.item(r, c)
            if item:
                item.setBackground(bg)

    self._refresh_preview_stats()


def _build_existing_duplicate_keys(self) -> set:
    """构建补充模式下已存在产品的判定键集合。"""
    existing_keys = set()
    if not self.is_supplement_mode:
        return existing_keys

    # 当前订单已有产品
    for item in (self._supplement_order_data or {}).get('items', []):
        product_id = item.get('product_id')
        if product_id:
            existing_keys.add(f"product_id:{product_id}")
        model = _normalize(item.get('model') or '')
        if model:
            existing_keys.add(f"model:{model}")

    # 客户-产品表已有 Model
    for model in (self._db_existing_models or {}).keys():
        model = _normalize(model)
        if model:
            existing_keys.add(f"model:{model}")

    return existing_keys
```

在 `OrderImportDialog` 的 `init` 中初始化：

```python
self._duplicate_groups = []
```

### 步骤 4：在状态标签中显示重复数量

修改 `_refresh_preview_stats` 方法，在统计文字中追加重复信息：

```python
def _refresh_preview_stats(self):
    """刷新预览统计信息"""
    total = self.preview_table.rowCount()
    duplicate_count = len(getattr(self, '_duplicate_groups', []))

    # ... 保留原有 temp_count / incomplete_count 统计逻辑 ...

    text = f"共 {total} 行数据"
    if duplicate_count > 0:
        text += f"（{duplicate_count} 个重复产品）"
    # ... 追加原有不完整/临时文字 ...

    self.preview_status_label.setText(text)
```

### 步骤 5：删除行后刷新重复高亮

修改 `_delete_preview_row` 方法，在末尾调用：

```python
self._refresh_duplicate_highlight()
```

### 步骤 6：Excel 加载与补充模式加载后刷新

修改 `on_preview_ready` 方法末尾（在 `self.preview_table.resizeColumnsToContents()` 之后）：

```python
self._refresh_duplicate_highlight()
```

### 步骤 7：补充模式不再自动跳过已存在产品

修改 `on_preview_ready` 中补充模式分支：

```python
if self.is_supplement_mode:
    # 不再自动过滤已存在产品，仅保留删除行过滤
    self._skipped_indices = set()
    display_rows = rows
    self.preview_data['rows'] = rows
    self.preview_data['total'] = len(rows)
    total = len(rows)
else:
    display_rows = rows
    self.preview_data['rows'] = rows
```

同时更新状态标签后缀，移除"已过滤重复商品"字样。

### 步骤 8：导入前确认重复

新增方法：

```python
def _confirm_and_filter_duplicates(self) -> bool:
    """
    导入前检测重复并弹窗让用户选择。

    Returns:
        True: 继续导入（可能已过滤重复行）
        False: 取消导入
    """
    rows = self.preview_data.get('rows', []) if self.preview_data else []
    if not rows:
        return True

    headers = self.preview_data.get('headers', [])
    model_col_idx = self._find_model_column(headers) if headers else None
    existing_keys = self._build_existing_duplicate_keys()
    duplicates = find_preview_duplicates(rows, headers, model_col_idx, existing_keys)

    if not duplicates:
        return True

    displays = [g['display'] for g in duplicates[:10]]
    msg = "检测到以下重复产品：\n" + "\n".join(f"- {d}" for d in displays)

    box = QMessageBox(self)
    box.setWindowTitle("检测到重复产品")
    box.setText(msg + "\n\n请选择处理方式：")
    continue_btn = box.addButton("继续导入", QMessageBox.AcceptRole)
    skip_btn = box.addButton("跳过重复行", QMessageBox.DestructiveRole)
    cancel_btn = box.addButton("取消", QMessageBox.RejectRole)
    box.exec()

    clicked = box.clickedButton()
    if clicked == cancel_btn:
        return False
    if clicked == skip_btn:
        keep = filter_duplicate_indices(len(rows), duplicates)
        self.preview_data['rows'] = [rows[i] for i in keep]
        self.preview_data['total'] = len(self.preview_data['rows'])
        self._rebuild_preview_table_from_rows()
        self._refresh_duplicate_highlight()
    return True


def _rebuild_preview_table_from_rows(self):
    """根据 self.preview_data['rows'] 重建预览表格（仅用于跳过重复行后）。"""
    rows = self.preview_data.get('rows', [])
    headers = self.preview_data.get('headers', [])
    self.preview_table.setRowCount(0)

    if not rows:
        return

    # 统一按原始列显示
    display_headers = ['行号'] + headers
    self.preview_table.setColumnCount(len(display_headers))
    self.preview_table.setHorizontalHeaderLabels(display_headers)

    self.preview_table.setRowCount(len(rows))
    for row_idx, row in enumerate(rows):
        self.preview_table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))
        if isinstance(row, (list, tuple)):
            for col_idx, value in enumerate(row):
                self.preview_table.setItem(
                    row_idx, col_idx + 1,
                    QTableWidgetItem(str(value) if value else "")
                )
        elif isinstance(row, dict):
            # 单条新增行展示字段顺序与 _add_single_product_to_preview 一致
            values = [
                row.get('customer_code', ''),
                row.get('oe_number', '') or '',
                str(row.get('quantity', 1)),
                f"${float(row.get('unit_price', 0)):.2f}" if row.get('unit_price') else '',
                '正式',
            ]
            for col_idx, value in enumerate(values):
                if col_idx + 1 < self.preview_table.columnCount():
                    self.preview_table.setItem(row_idx, col_idx + 1, QTableWidgetItem(value))

    self.preview_table.resizeColumnsToContents()
    self.preview_table.setColumnWidth(0, 50)
```

### 步骤 9：在导入入口调用确认

修改 `start_import` 方法开头，在原有确认弹窗之前插入：

```python
if not self._confirm_and_filter_duplicates():
    return
```

修改 `_start_supplement_import` 方法开头，同样在确认弹窗之前插入：

```python
if not self._confirm_and_filter_duplicates():
    return
```

### 步骤 10：运行前端编译检查

运行：

```bash
python -m py_compile client/widgets/order_import_dialog.py client/utils/duplicate_detector.py
```

预期：无语法错误。

### 步骤 11：Commit

```bash
git add client/widgets/order_import_dialog.py
git commit -m "feat(client): detect and highlight duplicate products in import preview" -m "- refresh highlight on single add, excel load, delete" -m "- prompt continue/skip/cancel before import" -m "- supplement mode no longer auto-skips existing products"
```

---

## 任务 3：在订单详情面板高亮重复行

**文件：**
- 修改：`client/widgets/order_summary/order_detail_panel.py`

### 步骤 1：新增重复行高亮方法

在 `OrderDetailPanel` 中新增方法：

```python
def _apply_duplicate_highlight(self):
    """高亮订单详情中重复出现的行（按 product_id，缺失时回退 customer_code+oe_number）。"""
    if not self._current_items:
        return

    pid_groups: Dict[Any, List[dict]] = {}
    fallback_groups: Dict[str, List[dict]] = {}

    for item in self._current_items:
        product_id = item.get('product_id')
        if product_id:
            pid_groups.setdefault(product_id, []).append(item)
        else:
            key = f"{item.get('customer_code', '')}|{item.get('oe_number', '')}"
            fallback_groups.setdefault(key, []).append(item)

    duplicate_pids = {pid for pid, items in pid_groups.items() if len(items) > 1}
    duplicate_fallbacks = {
        key for key, items in fallback_groups.items() if len(items) > 1
    }

    yellow = QBrush(QColor("#fef3c7"))
    red_name = QColor("#fff0f0").name().lower()

    for row in range(self._table.rowCount()):
        item0 = self._table.item(row, 0)
        # 跳过合计行
        if item0 and item0.text() == "📊 合计":
            continue

        if row >= len(self._current_items):
            continue

        item = self._current_items[row]
        product_id = item.get('product_id')
        fallback_key = f"{item.get('customer_code', '')}|{item.get('oe_number', '')}"
        is_duplicate = (
            product_id in duplicate_pids or fallback_key in duplicate_fallbacks
        )

        if not is_duplicate:
            continue

        for col in range(ORDER_DETAIL_COLUMN_COUNT):
            cell = self._table.item(row, col)
            if not cell:
                continue
            # 不覆盖已存在的红色背景（采购数量不匹配）
            bg_color = cell.background().color().name().lower()
            if bg_color == red_name:
                continue
            cell.setBackground(yellow)

        if item0:
            item0.setToolTip("该产品在订单中重复出现")
```

### 步骤 2：在渲染流程中调用

修改 `show_order_detail` 方法，在 `_fill_excel_41_columns` 循环结束后、`_add_summary_row` 之前调用：

```python
for idx, item in enumerate(self._current_items):
    row = self._table.rowCount()
    self._table.insertRow(row)
    self._fill_excel_41_columns(row, idx, item, order, currency)

# 新增：高亮重复行
self._apply_duplicate_highlight()

self._table.setSortingEnabled(False)

# 添加合计行
self._add_summary_row()
```

### 步骤 3：运行前端编译检查

运行：

```bash
python -m py_compile client/widgets/order_summary/order_detail_panel.py
```

预期：无语法错误。

### 步骤 4：Commit

```bash
git add client/widgets/order_summary/order_detail_panel.py
git commit -m "feat(client): highlight duplicate rows in order detail panel" -m "- use product_id primary key, fallback to customer_code+oe_number" -m "- preserve existing red mismatch highlight"
```

---

## 任务 4：集成验证

### 步骤 1：运行工具测试

```bash
python tests/client/utils/test_duplicate_detector.py
```

预期：8 个测试全部通过。

### 步骤 2：前端整体编译检查

```bash
python -m py_compile client/widgets/order_import_dialog.py client/widgets/order_summary/order_detail_panel.py client/utils/duplicate_detector.py
```

预期：无语法错误。

### 步骤 3：手动场景验证

1. **单条新增重复**：
   - 打开订单导入 → 选择客户 → 单条新增同一产品两次。
   - 第二次新增后应弹窗提示，预览表两行均浅黄高亮。

2. **Excel 重复**：
   - 准备 Excel，同一 Model 出现两行。
   - 加载预览后两行浅黄高亮，状态标签显示重复数量。
   - 点击导入，弹窗选择"跳过重复行"，仅保留第一行导入。

3. **补充模式重复**：
   - 打开补充商品，选择一个当前订单已存在的产品。
   - 预览表高亮，导入前弹窗提示与订单已有产品重复。

4. **订单详情高亮**：
   - 打开一个包含重复产品的订单。
   - 重复行浅黄背景，第一列 tooltip 提示"该产品在订单中重复出现"。

### 步骤 4：Commit（可选，若步骤 3 有改动则提交）

```bash
git add .
git commit -m "test: verify duplicate product detection scenarios"
```

---

## 自检

- ✅ **规格覆盖度**：
  - 预览阶段检测 → 任务 2（`_refresh_duplicate_highlight`、`_confirm_and_filter_duplicates`）。
  - 单条新增/Excel/补充模式 → 任务 2 步骤 2、6、7、9。
  - 不再自动跳过补充模式已存在产品 → 任务 2 步骤 7。
  - 导入后订单详情高亮 → 任务 3。
  - 用户自行抉择（继续/跳过/取消）→ 任务 2 步骤 8。
- ✅ **占位符扫描**：无 TODO、无"适当"、无"后续实现"。
- ✅ **类型一致性**：`extract_preview_duplicate_key`、`find_preview_duplicates`、`filter_duplicate_indices` 签名在任务 1 定义，任务 2/3 使用一致。
