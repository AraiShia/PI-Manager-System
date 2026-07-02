# 全面去除临时产品业务设计文档

## 1. 背景与目标

### 1.1 背景
当前系统中存在"临时产品"业务概念：
- 订单导入时，无 Model（客户产品编号）的产品会自动创建为临时产品（`is_temporary=True`）
- PI 明细中包含临时产品项（`item.is_temporary=True`）
- 用户需要双击临时产品项，通过转正对话框将临时产品转为正式产品
- 临时产品在 UI 中有特殊标记、筛选条件和操作入口

### 1.2 目标
全面去除临时产品业务：
- 新流程中不再产生临时产品
- 无 Model 产品时直接创建正式客户产品
- 移除所有临时产品相关的 UI 提示、标记、筛选、转正功能
- 保留历史临时产品数据，但不再特殊处理
- 数据库 `is_temporary` 字段保留但废弃使用

## 2. 设计原则

1. **数据库字段保留，业务逻辑废弃**
   - `PrdCustomerProduct.is_temporary` 和 `PiProformaInvoiceItem.is_temporary` 字段保留
   - 新创建记录全部设为 `False`
   - 代码中不再根据 `is_temporary` 做分支判断

2. **订单导入统一创建正式客户产品**
   - 无 Model 的产品不再生成临时产品
   - 直接生成正式客户产品，使用现有自动编号规则
   - 导入流程不再提示"临时产品转正"

3. **移除临时产品专用 API**
   - 删除创建临时产品接口
   - 删除临时产品转正相关接口
   - 删除临时产品列表查询接口

4. **移除前端临时产品 UI**
   - 不再显示临时产品标记（颜色、图标、标签）
   - 不再提供"转正"操作入口
   - 移除临时产品筛选条件

5. **历史数据兼容**
   - 旧的临时产品记录保留在数据库中
   - 界面不再特殊显示它们，视为普通正式产品处理

## 3. 后端修改点

### 3.1 数据模型
- 保留 `is_temporary` 字段，但不再新增迁移脚本
- 所有新创建记录的 `is_temporary` 默认设为 `False`

### 3.2 `backend/routers/order_import.py`
- 修改 `_auto_match_entities` 函数
- 无 Model 产品时，直接调用 `create_customer_product` 创建正式产品
- 删除临时产品创建分支
- 移除 `is_temporary` 相关标记

### 3.3 `backend/crud/customer_product.py`
- 删除 `find_or_create_temp_customer_product`
- 删除 `convert_temporary_to_official`
- 删除 `update_and_confirm_temporary`
- 删除 `get_temporary_products`
- 普通查询函数中移除 `is_temporary` 筛选参数

### 3.4 `backend/crud/pi.py`
- 移除 PI item 中的临时产品分支判断
- 移除 `temp_data` 相关字段的返回（或保留为空）
- 简化 item 详情字典

### 3.5 `backend/routers/customer_product.py`
- 删除临时产品转正相关路由
- 删除临时产品列表查询路由
- 删除创建临时产品相关路由

### 3.6 `backend/routers/product.py` / `product_compat.py`
- 删除 `POST /products/temporary` 等临时产品相关端点

### 3.7 Schemas
- `backend/schemas/pi.py`
- `backend/schemas/pi_detail.py`
- `backend/schemas/customer_product.py`
- `backend/schemas/order_import.py`

移除 `is_temporary`、`temp_data`、`temporary_reason` 等字段返回

## 4. 前端修改点

### 4.1 `client/api/client.py`
- 删除 `create_temporary_product`
- 删除 `confirm_temporary_product`
- 删除临时产品相关 API 方法

### 4.2 `client/services/order_service.py`
- 删除导入时标记 `is_temporary = True` 的逻辑
- 所有产品统一视为正式产品

### 4.3 `client/widgets/customer_product_dialog.py`
- 删除临时产品转正相关代码
- 删除 `temp_data` 解析逻辑
- 简化产品编辑对话框

### 4.4 `client/main.py`
- 删除 `_handle_temporary_product_edit`
- 删除 `_on_temp_product_confirmed`
- 删除 `_show_temporary_readonly_dialog`
- 删除双击临时产品弹转正对话框的逻辑
- 删除 `is_temporary` 判断分支

### 4.5 `client/widgets/order_import_dialog.py`
- 删除临时产品相关状态显示
- 删除临时产品确认/转正相关 UI
- 简化导入确认流程

### 4.6 其他 UI 组件
- `client/widgets/order_summary/order_detail_panel.py`
- `client/widgets/order_summary/order_summary_tab.py`
- `client/widgets/order_summary/order_list_panel.py`
- `client/widgets/order_summary/constants.py`
- `client/widgets/purchase_dialog.py`
- `client/widgets/wizard_confirm_dialog.py`
- `client/widgets/status_indicator.py`
- `client/widgets/order_summary_edit_dialog.py`

移除：
- 临时产品颜色标记
- 临时产品筛选条件
- 临时产品状态指示
- 转正按钮/菜单

## 5. 数据流变化

### 5.1 当前流程（有临时产品）

```
Excel 导入
  ↓
无 Model 产品
  ↓
创建临时客户产品 (is_temporary=True)
  ↓
生成 PI 明细 (item.is_temporary=True)
  ↓
用户双击 PI 明细
  ↓
弹出转正对话框
  ↓
确认后调用转正 API
  ↓
临时产品 → 正式产品
```

### 5.2 新流程（去除临时产品）

```
Excel 导入
  ↓
无 Model 产品
  ↓
直接创建正式客户产品 (is_temporary=False)
  ↓
生成 PI 明细 (item.is_temporary=False)
  ↓
用户双击 PI 明细
  ↓
直接打开普通产品编辑/查看（无转正流程）
```

### 5.3 关键代码路径

1. **导入时产品匹配**：`backend/routers/order_import.py::_auto_match_entities`
2. **客户产品创建**：`backend/crud/customer_product.py::create_customer_product`
3. **PI 明细生成**：`backend/crud/pi.py` 中 item 转 dict 的逻辑
4. **前端双击处理**：`client/main.py` 中双击行逻辑
5. **产品编辑**：`client/widgets/customer_product_dialog.py`

## 6. 风险与兼容性

### 6.1 历史数据兼容性 ✅
- `is_temporary=True` 的旧记录保留在数据库中
- 由于代码不再读取该字段，旧记录会被当作普通记录处理
- 不会破坏已有 PI、订单、客户产品数据

### 6.2 已有 API 调用 ⚠️
- 如果有外部系统调用了临时产品相关 API，会返回 404
- 需要确认是否有外部依赖

### 6.3 前端界面变化 ⚠️
- 用户不再看到"临时产品"概念
- 旧临时产品在界面上不再特殊标记
- 需要在更新说明中告知客户

### 6.4 订单导入行为变化 ✅
- 无 Model 产品直接创建正式客户产品
- 编号规则复用现有自动编号逻辑

### 6.5 测试重点
- 无 Model 产品的订单导入
- 已有 PI 明细的查看和编辑
- 客户产品列表/搜索
- 双击 PI 行打开编辑对话框

### 6.6 回滚方案
- 如果需要回滚，恢复代码即可
- 数据库字段未删除，不影响回滚

## 7. 方案选择

经过评估，选择**方案二：清理行为+废弃 API**。

理由：
1. 符合"保留数据库字段"的选择
2. 能真正去除临时产品业务，不只是改变行为
3. 风险可控，不会破坏历史数据
4. 代码可维护性最好
