# 全面去除临时产品业务实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 全面去除 PI Manager 中的临时产品业务，使无 Model 的产品直接创建为正式客户产品，并移除所有相关的 UI 标记、转正流程和专用 API。

**架构：** 保留数据库 `is_temporary` 字段但废弃使用；后端订单导入流程改为直接创建正式客户产品；删除临时产品专用 CRUD、路由和 Schema 字段；前端移除临时产品状态标记、转正对话框和相关 API 调用。

**技术栈：** Python 3.11 / FastAPI / SQLAlchemy / PySide6

---

## 文件清单

### 后端修改文件

| 文件 | 职责 |
|------|------|
| `backend/routers/order_import.py` | 订单导入核心逻辑；无 Model 时改创建正式产品；删除临时产品路由 |
| `backend/crud/customer_product.py` | 删除临时产品相关 CRUD 函数；移除 `is_temporary` 筛选参数 |
| `backend/crud/pi.py` | 移除 PI item 详情中的临时产品分支和 `temp_data` 字段 |
| `backend/routers/customer_product.py` | 删除临时产品转正/列表路由 |
| `backend/routers/product.py` | 删除临时产品转正端点 |
| `backend/routers/product_compat.py` | 删除临时产品兼容端点 |
| `backend/schemas/order_import.py` | 移除 `auto_create_temporary` 等字段 |
| `backend/schemas/pi.py` | 移除 `is_temporary` 字段 |
| `backend/schemas/pi_detail.py` | 移除 `is_temporary` / `temporary_reason` 字段 |
| `backend/schemas/customer_product.py` | 移除 `is_temporary` 字段 |

### 前端修改文件

| 文件 | 职责 |
|------|------|
| `client/api/client.py` | 删除临时产品相关 API 方法 |
| `client/services/order_service.py` | 删除 `is_temporary` 标记逻辑 |
| `client/main.py` | 删除临时产品双击转正处理 |
| `client/widgets/customer_product_dialog.py` | 删除临时产品转正相关代码 |
| `client/widgets/order_import_dialog.py` | 删除临时产品 UI 提示 |
| `client/widgets/order_summary/order_detail_panel.py` | 清理临时产品状态指示 |
| `client/widgets/order_summary/order_summary_tab.py` | 清理临时产品筛选/标记 |
| `client/widgets/order_summary/order_list_panel.py` | 清理临时产品标记 |
| `client/widgets/order_summary/constants.py` | 清理临时产品相关常量 |
| `client/widgets/purchase_dialog.py` | 清理临时产品引用 |
| `client/widgets/wizard_confirm_dialog.py` | 清理临时产品引用 |
| `client/widgets/status_indicator.py` | 清理临时产品引用 |

---

## 任务 1：后端 - 修改订单导入，无 Model 时创建正式产品

**文件：**
- 修改：`backend/routers/order_import.py:879-950`
- 修改：`backend/schemas/order_import.py:210-211`
- 测试：运行后端并导入无 Model 的 Excel

- [ ] **步骤 1：移除 `auto_create_temporary` 字段**

在 `backend/schemas/order_import.py` 中，从预览/导入请求模型中删除以下字段：

```python
# 删除以下字段
auto_create_temporary: bool = Field(default=False, description="True 时未匹配项静默创建 temp 产品（导入场景）")
customer_id: Optional[int] = Field(default=None, ge=1, description="客户ID（auto_create_temporary=True 时必填）")
```

> 注意：保留真正用于导入的其他字段，只删除 `auto_create_temporary` 和配套的 `customer_id`（如果该 `customer_id` 仅用于临时产品创建）。需要检查该 `customer_id` 是否还有其他用途。

- [ ] **步骤 2：修改 `_auto_match_entities` 调用正式产品创建**

在 `backend/routers/order_import.py` 中，找到以下代码：

```python
elif request.auto_create_temporary:
    product, created = find_or_create_temp_customer_product(db, cust_id, row)
```

替换为直接调用 `create_customer_product`：

```python
else:
    # 无 Model 时直接创建正式客户产品
    from schemas.customer_product import CustomerProductCreate
    cp_data = CustomerProductCreate(
        customer_id=cust_id,
        customer_model=row.get('customer_model') or row.get('model') or '',
        customer_product_code=row.get('customer_model') or row.get('model') or '',
        product_name=row.get('product_name') or row.get('detail_desc') or '',
        detail_desc=row.get('detail_desc') or '',
        oe_number=row.get('oe_number') or None,
    )
    product = create_customer_product(db, cp_data)
```

- [ ] **步骤 3：删除临时产品导入注释和校验**

删除 `backend/routers/order_import.py:879-893` 附近关于 `auto_create_temporary` 的注释和校验代码。

- [ ] **步骤 4：运行后端导入测试**

```bash
cd backend
uvicorn main:app --reload
```

在客户端或通过 Swagger (`/docs`) 调用导入接口，上传一份包含无 Model 产品的 Excel，确认：
- 导入成功
- 无 Model 行在 `prd_customer_product` 中创建的记录 `is_temporary=False`

- [ ] **步骤 5：Commit**

```bash
git add backend/routers/order_import.py backend/schemas/order_import.py
git commit -m "feat(backend): create official customer product when model missing"
```

---

## 任务 2：后端 - 删除订单导入中的临时产品路由

**文件：**
- 修改：`backend/routers/order_import.py:1067-1079`
- 修改：`backend/routers/order_import.py:1414-1430`

- [ ] **步骤 1：删除 `create_temporary_product` 路由**

删除以下端点及内部实现：

```python
@router.post("/temporary")
async def create_temporary_product(...)
```

- [ ] **步骤 2：删除 `confirm_temporary_product` 路由**

删除以下端点及内部实现：

```python
@router.post("/temporary/{product_id}/confirm")
async def confirm_temporary_product(...)
```

- [ ] **步骤 3：启动后端验证无报错**

```bash
cd backend
python -c "from main import app; print('OK')"
```

- [ ] **步骤 4：Commit**

```bash
git add backend/routers/order_import.py
git commit -m "feat(backend): remove temporary product routes from order_import"
```

---

## 任务 3：后端 - 删除临时产品 CRUD 函数

**文件：**
- 修改：`backend/crud/customer_product.py:203-309`
- 修改：`backend/crud/customer_product.py:394-499`
- 修改：`backend/crud/customer_product.py:570-590`
- 修改：`backend/crud/customer_product.py:285-304`

- [ ] **步骤 1：删除 `find_or_create_temp_customer_product`**

删除 `backend/crud/customer_product.py:203-309` 的完整函数。

- [ ] **步骤 2：删除 `convert_temporary_to_official`**

删除 `backend/crud/customer_product.py:394-442` 的完整函数。

- [ ] **步骤 3：删除 `update_and_confirm_temporary`**

删除 `backend/crud/customer_product.py:444-499` 的完整函数。

- [ ] **步骤 4：删除 `get_temporary_products`**

删除 `backend/crud/customer_product.py:570-590` 的完整函数。

- [ ] **步骤 5：移除 `get_customer_products` 的 `is_temporary` 参数**

在 `backend/crud/customer_product.py:285` 附近，修改函数签名：

```python
# 修改前
def get_customer_products(
    db: Session,
    customer_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    is_temporary: Optional[bool] = None,
) -> Tuple[List[PrdCustomerProduct], int]:

# 修改后
def get_customer_products(
    db: Session,
    customer_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[List[PrdCustomerProduct], int]:
```

并删除以下筛选代码：

```python
if is_temporary is not None:
    query = query.filter(PrdCustomerProduct.is_temporary == is_temporary)
```

- [ ] **步骤 6：验证后端启动无导入错误**

```bash
cd backend
python -c "from crud.customer_product import get_customer_products; print('OK')"
```

- [ ] **步骤 7：Commit**

```bash
git add backend/crud/customer_product.py
git commit -m "feat(backend): remove temporary product CRUD helpers"
```

---

## 任务 4：后端 - 删除 customer_product 路由中的临时产品端点

**文件：**
- 修改：`backend/routers/customer_product.py:1-30`
- 修改：`backend/routers/customer_product.py:170-230`

- [ ] **步骤 1：删除临时产品函数导入**

```python
# 删除
from crud.customer_product import (
    convert_temporary_to_official,
    get_temporary_products,
    update_and_confirm_temporary,
)
```

- [ ] **步骤 2：删除临时产品列表路由**

删除约 `backend/routers/customer_product.py:170-179` 的临时产品列表接口。

- [ ] **步骤 3：删除创建临时产品路由**

删除约 `backend/routers/customer_product.py:179-193` 的 `create_temporary_product` 接口。

- [ ] **步骤 4：删除转正路由**

删除约 `backend/routers/customer_product.py:194-230` 的两个转正接口。

- [ ] **步骤 5：验证后端启动无报错**

```bash
cd backend
python -c "from main import app; print('OK')"
```

- [ ] **步骤 6：Commit**

```bash
git add backend/routers/customer_product.py
git commit -m "feat(backend): remove temporary product endpoints from customer_product router"
```

---

## 任务 5：后端 - 删除 product / product_compat 中的临时产品端点

**文件：**
- 修改：`backend/routers/product.py:1-10`
- 修改：`backend/routers/product.py:200-210`
- 修改：`backend/routers/product_compat.py:1-30`
- 修改：`backend/routers/product_compat.py:175-195`
- 修改：`backend/crud/product.py:204-280`

- [ ] **步骤 1：删除 product.py 中的临时产品导入和端点**

在 `backend/routers/product.py` 中：

```python
# 删除导入
from crud.product import confirm_temporary_product
```

删除 `confirm_temporary_product` 相关端点。

- [ ] **步骤 2：删除 product_compat.py 中的临时产品兼容端点**

在 `backend/routers/product_compat.py` 中：

```python
# 删除导入
from crud.customer_product import update_and_confirm_temporary
```

删除约 `backend/routers/product_compat.py:175-195` 的兼容端点。

- [ ] **步骤 3：删除 crud/product.py 中的临时产品函数**

删除 `create_temporary_product` 和 `confirm_temporary_product` 函数。

- [ ] **步骤 4：验证后端启动无报错**

```bash
cd backend
python -c "from main import app; print('OK')"
```

- [ ] **步骤 5：Commit**

```bash
git add backend/routers/product.py backend/routers/product_compat.py backend/crud/product.py
git commit -m "feat(backend): remove temporary product endpoints from product routers"
```

---

## 任务 6：后端 - 移除 PI item 详情中的临时产品分支

**文件：**
- 修改：`backend/crud/pi.py:320-345`
- 修改：`backend/crud/pi.py:440-515`
- 修改：`backend/crud/pi.py:1470-1510`

- [ ] **步骤 1：简化 `is_temporary` 判断**

在 `backend/crud/pi.py:320-345` 附近，将临时产品判断替换为：

```python
is_temporary = False
temp_data = {}
```

- [ ] **步骤 2：移除 `temp_data` 相关字段返回**

在构建 `detail` 字典时，删除以下字段：

```python
"is_temporary": is_temporary,
"temporary_reason": temp_data.get("reason") if is_temporary else None,
"temp_data": temp_data if is_temporary else {},
"product_feature": temp_data.get("feature") if is_temporary else None,
"customer_reply": temp_data.get("customer_reply") if is_temporary else None,
"customer_prepayment": temp_data.get("prepayment") if is_temporary else None,
"remaining_payment": temp_data.get("remaining_payment") if is_temporary else None,
```

改为直接使用 item 自身字段或 `None`：

```python
"is_temporary": False,
"temporary_reason": None,
"temp_data": {},
"product_feature": getattr(item, 'product_feature', None),
"customer_reply": getattr(item, 'customer_reply', None),
"customer_prepayment": float(item.customer_prepayment) if getattr(item, 'customer_prepayment', None) is not None else None,
"remaining_payment": float(item.remaining_payment) if getattr(item, 'remaining_payment', None) is not None else None,
```

- [ ] **步骤 3：删除 PI 创建/更新中的临时产品转正调用**

在 `backend/crud/pi.py:1470-1510` 附近，删除对 `update_and_confirm_temporary` 的调用及相关逻辑。

- [ ] **步骤 4：验证 PI 详情接口**

启动后端，调用 PI 详情接口，确认返回中不再包含 `is_temporary`、`temporary_reason`、`temp_data` 字段。

- [ ] **步骤 5：Commit**

```bash
git add backend/crud/pi.py
git commit -m "feat(backend): remove temporary product branches from PI item detail"
```

---

## 任务 7：后端 - 移除 Schemas 中的临时产品字段

**文件：**
- 修改：`backend/schemas/pi.py:21`
- 修改：`backend/schemas/pi.py:101`
- 修改：`backend/schemas/pi_detail.py:12-13`
- 修改：`backend/schemas/customer_product.py:74`
- 修改：`backend/schemas/customer_product.py:98`
- 修改：`backend/schemas/customer_product.py:121`
- 修改：`backend/schemas/order_import.py`

- [ ] **步骤 1：移除 `pi.py` 中的 `is_temporary` 字段**

删除 `backend/schemas/pi.py:21` 和 `:101` 的 `is_temporary` 字段定义。

- [ ] **步骤 2：移除 `pi_detail.py` 中的临时产品字段**

删除：

```python
is_temporary: Optional[bool] = False              # 临时产品标志
temporary_reason: Optional[str] = None             # 原因说明
```

- [ ] **步骤 3：移除 `customer_product.py` 中的 `is_temporary` 字段**

删除该 schema 中所有 `is_temporary` 字段定义。

- [ ] **步骤 4：移除 `order_import.py` 中的临时产品相关字段**

检查并删除 `auto_create_temporary` 和仅用于临时产品的字段。

- [ ] **步骤 5：启动后端验证无 Pydantic 错误**

```bash
cd backend
python -c "from main import app; print('OK')"
```

- [ ] **步骤 6：Commit**

```bash
git add backend/schemas/
git commit -m "feat(backend): remove temporary product fields from schemas"
```

---

## 任务 8：前端 - 删除 API Client 中的临时产品方法

**文件：**
- 修改：`client/api/client.py:336-339`

- [ ] **步骤 1：删除临时产品 API 方法**

删除：

```python
def create_temporary_product(self, data: dict) -> dict:
    return self.post("/products/temporary", data)

def confirm_temporary_product(self, product_id: int, data: dict) -> dict:
    return self.post(f"/products/{product_id}/confirm", data)
```

- [ ] **步骤 2：验证客户端可导入**

```bash
cd client
python -c "from api.client import APIClient; print('OK')"
```

- [ ] **步骤 3：Commit**

```bash
git add client/api/client.py
git commit -m "feat(client): remove temporary product API methods"
```

---

## 任务 9：前端 - 删除 order_service 中的临时产品标记

**文件：**
- 修改：`client/services/order_service.py:218-231`

- [ ] **步骤 1：删除 `is_temporary` 标记逻辑**

将以下两段代码：

```python
for item in items:
    if not item.get('product_id') or item.get('product_id') == 0:
        item['is_temporary'] = True
    elif 'is_temporary' not in item:
        item['is_temporary'] = False
```

简化为：

```python
for item in items:
    item['is_temporary'] = False
```

或直接删除整个 `for` 循环（如果后续代码不依赖 `is_temporary` 存在）。

- [ ] **步骤 2：验证服务可导入**

```bash
cd client
python -c "from services.order_service import OrderService; print('OK')"
```

- [ ] **步骤 3：Commit**

```bash
git add client/services/order_service.py
git commit -m "feat(client): remove is_temporary flag in order_service"
```

---

## 任务 10：前端 - 删除 main.py 中的临时产品双击处理

**文件：**
- 修改：`client/main.py:3938-4145`

- [ ] **步骤 1：简化双击行判断**

将：

```python
item_is_temporary = bool(item.get('is_temporary', False))
is_temp = item_is_temporary or not item.get('product_id') or item.get('product_id') == 0
print(f"[DEBUG] DoubleClick row={row}: is_temp={is_temp}, product_id={item.get('product_id')}, is_temporary={item.get('is_temporary')}")
if is_temp:
    self._handle_temporary_product_edit(row, column, item, order)
    return
```

改为直接进入普通编辑流程（删除临时产品分支，保留原有的普通编辑逻辑）。

- [ ] **步骤 2：删除 `_handle_temporary_product_edit` 方法**

删除 `client/main.py:4021-4140` 的完整方法。

- [ ] **步骤 3：删除 `_show_temporary_readonly_dialog` 方法**

删除 `client/main.py:4142-4145` 的完整方法。

- [ ] **步骤 4：验证客户端可启动**

```bash
cd client
python -c "from main import main; print('OK')"
```

- [ ] **步骤 5：Commit**

```bash
git add client/main.py
git commit -m "feat(client): remove temporary product double-click handling"
```

---

## 任务 11：前端 - 删除 customer_product_dialog 中的转正逻辑

**文件：**
- 修改：`client/widgets/customer_product_dialog.py:425-1155`

- [ ] **步骤 1：删除临时产品状态判断**

删除或简化基于 `is_temporary` 的 UI 分支，例如：

```python
is_temp = self.product.get('is_temporary', False)
```

- [ ] **步骤 2：删除 `_parse_temp_data` 方法**

删除 `client/widgets/customer_product_dialog.py:1032-1050` 附近的 `_parse_temp_data` 方法。

- [ ] **步骤 3：删除 `confirm_temporary_product` API 调用**

删除约 `client/widgets/customer_product_dialog.py:1145-1155` 的转正 API 调用代码。

- [ ] **步骤 4：简化保存逻辑**

确保保存时只调用普通的产品更新接口。

- [ ] **步骤 5：验证对话框可导入**

```bash
cd client
python -c "from widgets.customer_product_dialog import CustomerProductDialog; print('OK')"
```

- [ ] **步骤 6：Commit**

```bash
git add client/widgets/customer_product_dialog.py
git commit -m "feat(client): remove temporary product conversion from customer_product_dialog"
```

---

## 任务 12：前端 - 删除 order_import_dialog 中的临时产品 UI

**文件：**
- 修改：`client/widgets/order_import_dialog.py`

- [ ] **步骤 1：删除临时产品状态显示**

搜索 `is_temporary`、`temp`、`临时` 关键字，删除相关 QLabel、QTableWidget 列、颜色标记。

- [ ] **步骤 2：删除临时产品确认/转正按钮**

删除与临时产品转正/确认相关的按钮及其槽函数。

- [ ] **步骤 3：验证导入对话框可导入**

```bash
cd client
python -c "from widgets.order_import_dialog import OrderImportDialog; print('OK')"
```

- [ ] **步骤 4：Commit**

```bash
git add client/widgets/order_import_dialog.py
git commit -m "feat(client): remove temporary product UI from order_import_dialog"
```

---

## 任务 13：前端 - 清理其他 UI 组件中的临时产品引用

**文件：**
- 修改：`client/widgets/order_summary/order_detail_panel.py`
- 修改：`client/widgets/order_summary/order_summary_tab.py`
- 修改：`client/widgets/order_summary/order_list_panel.py`
- 修改：`client/widgets/order_summary/constants.py`
- 修改：`client/widgets/purchase_dialog.py`
- 修改：`client/widgets/wizard_confirm_dialog.py`
- 修改：`client/widgets/status_indicator.py`

- [ ] **步骤 1：逐个文件搜索并清理**

对每个文件执行：

```bash
cd client
python -c "
import re
files = [
    'widgets/order_summary/order_detail_panel.py',
    'widgets/order_summary/order_summary_tab.py',
    'widgets/order_summary/order_list_panel.py',
    'widgets/order_summary/constants.py',
    'widgets/purchase_dialog.py',
    'widgets/wizard_confirm_dialog.py',
    'widgets/status_indicator.py',
]
for f in files:
    with open(f, 'r', encoding='utf-8') as fp:
        content = fp.read()
    if 'is_temporary' in content or 'temp_data' in content or 'temporary' in content.lower():
        print(f'Found in {f}')
"
```

- [ ] **步骤 2：删除临时产品相关常量**

在 `client/widgets/order_summary/constants.py` 中，删除临时产品颜色、文本等常量。

- [ ] **步骤 3：删除状态指示中的临时产品逻辑**

在 `client/widgets/status_indicator.py` 中，移除基于 `is_temporary` 的状态分支。

- [ ] **步骤 4：验证相关模块可导入**

```bash
cd client
python -c "
from widgets.order_summary.order_detail_panel import OrderDetailPanel
from widgets.order_summary.order_summary_tab import OrderSummaryTab
from widgets.order_summary.order_list_panel import OrderListPanel
from widgets.purchase_dialog import PurchaseDialog
from widgets.wizard_confirm_dialog import WizardConfirmDialog
from widgets.status_indicator import StatusIndicator
print('OK')
"
```

- [ ] **步骤 5：Commit**

```bash
git add client/widgets/
git commit -m "feat(client): clean up temporary product references across UI"
```

---

## 任务 14：集成测试 - 订单导入无 Model 产品

**文件：**
- 测试：`backend/routers/order_import.py`
- 测试数据：使用包含无 Model 产品的 Excel

- [ ] **步骤 1：准备测试 Excel**

创建一份测试 Excel，包含：
- 一行有 Model 的产品
- 一行无 Model 的产品

- [ ] **步骤 2：调用导入预览接口**

```bash
curl -X POST "http://localhost:8000/api/order-import/preview" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_no_model.xlsx"
```

确认预览成功，无 Model 行有 `customer_product_id` 或类似匹配结果。

- [ ] **步骤 3：确认数据库记录**

查询数据库：

```sql
SELECT id, customer_model, is_temporary FROM prd_customer_product WHERE customer_model LIKE 'TP%' ORDER BY id DESC LIMIT 5;
```

确认 `is_temporary = 0`。

- [ ] **步骤 4：Commit 测试文件（可选）**

```bash
git add test_no_model.xlsx
git commit -m "test: add sample excel for no-model import"
```

---

## 任务 15：集成测试 - 客户端 PI 列表与详情

**文件：**
- 运行：`client/main.py`

- [ ] **步骤 1：启动后端**

```bash
cd backend
uvicorn main:app --reload
```

- [ ] **步骤 2：启动客户端**

```bash
cd client
python main.py
```

- [ ] **步骤 3：验证以下场景**

1. 打开 PI 列表，双击任意 PI 行，能正常打开详情
2. 详情中无"临时产品"标记/颜色
3. 双击详情中的产品行，打开普通产品编辑对话框（非转正对话框）
4. 打开客户产品管理，搜索之前导入的无 Model 产品，能正常显示和编辑

- [ ] **步骤 4：记录测试结果**

在 `docs/superpowers/plans/2026-07-02-remove-temporary-product.md` 的任务 14/15 中勾选并记录结果。

---

## 自检清单

- [ ] 所有临时产品专用 CRUD 函数已删除
- [ ] 所有临时产品专用 API 路由已删除
- [ ] 所有 Schemas 中的 `is_temporary` / `temp_data` / `temporary_reason` 已移除
- [ ] 订单导入无 Model 时创建 `is_temporary=False` 的正式客户产品
- [ ] 前端不再显示临时产品标记和转正入口
- [ ] 后端启动无导入错误
- [ ] 前端启动无导入错误
- [ ] 导入测试通过
- [ ] PI 详情和编辑测试通过
