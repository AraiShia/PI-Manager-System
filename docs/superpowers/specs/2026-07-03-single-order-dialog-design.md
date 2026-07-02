# 单条新增 Dialog 简化设计

## 概述

简化 `SingleOrderDialog`，专注于快速录入核心字段，复杂字段后续在订单详情中编辑。

## 设计目标

- **精简字段**：只保留最核心的录入字段
- **快速录入**：减少操作步骤，提升录入效率
- **向后兼容**：保持与 `order_import_dialog.py` 的调用接口不变

## 字段设计

### 保留字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| 客户 | 下拉选择 | ✅ | - | 从客户列表选择，补充模式下预选中并锁定 |
| 产品搜索 | 输入搜索 | ⬜ | - | 输入OE号或名称搜索现有产品，自动填充字段 |
| 客户产品编号 | 文本输入 | ✅ | - | 客户提供的产品编号 |
| OE号 | 文本输入 | ✅ | - | 产品OE号 |
| 数量 | 数字输入 | ✅ | 1 | 产品数量 |
| 单价 | 数字输入 | ✅ | 0.01 | USD单价 |

### 移除字段

- 产品描述
- 交货日期
- 备注

这些字段后续在订单详情面板的 `ProductItemEditDialog` 中编辑。

## 交互流程

```
选择客户 → （可选）搜索产品 → 输入必填字段 → 保存
```

1. **选择客户**：从下拉列表选择客户（补充模式下自动预选中并锁定）
2. **搜索产品（可选）**：输入OE号或产品名称搜索，选择结果后自动填充 OE号、客户产品编号、单价
3. **输入字段**：手动输入或修改所有字段
4. **保存**：验证必填字段后提交

## 数据结构

### 输出（get_product_data 返回）

```python
{
    'customer_id': int,
    'product_id': int or None,  # 搜索到的产品ID，未搜索则为None
    'customer_code': str,       # 客户产品编号
    'oe_number': str,           # OE号
    'quantity': int,            # 数量
    'unit_price': float,        # 单价(USD)
}
```

## 模式支持

### import 模式

创建单条订单，调用 `/orders/single` API。

### supplement 模式

补充单条产品到预览列表，不直接调用API，由 `order_import_dialog.py` 的 `_add_single_product_to_preview` 处理。

## 与现有系统集成

### 调用方

- `order_import_dialog.py` 中的 `open_single_order_dialog()` 方法调用
- 保持接口不变：`SingleOrderDialog(api_client, parent, customer_id, mode)`

### 后续编辑

新增的产品在订单详情面板中通过 `ProductItemEditDialog` 编辑完整字段。

## 规格自检

- ✅ 无占位符
- ✅ 内部一致性：字段列表与交互流程一致
- ✅ 范围检查：聚焦于单条新增功能，不包含其他功能
- ✅ 模糊性检查：字段用途和交互流程明确

## 批准

设计已批准，可进入实现阶段。
