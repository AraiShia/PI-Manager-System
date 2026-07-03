# PI 导出动态行扩展设计

## 背景

当前 PI 导出模板（`template_pi.xlsx`）只能容纳最多 11 个产品，超过的产品会被截断。本设计实现动态行扩展，支持任意数量产品的 PI 导出。

## 设计目标

1. 产品明细区域支持动态扩展，无行数限制
2. TOTAL、SAY TOTAL、Remark、条款等区域始终在文档底部
3. 保持现有模板样式不变
4. 超过一定行数（如 50 行）时分页或提示

## 方案

采用动态插入行方案，根据产品数量动态计算各区域位置。

## 模板结构

```
A1-A3    : 公司抬头、PI NO、标题（固定）
A5-A9    : 买方/卖方信息（固定）
A10-J10  : 产品表头（固定）
A11+     : 产品明细（动态扩展，起始行=11）
TOTAL    : 动态插入行（在最后一个产品行+2）
Remark   : 动态插入行（在TOTAL行+2）
银行信息  : 固定在最后（或动态插入）
```

## 实现步骤

### 1. 修改 XlsxTemplateRenderer

新增 `dynamic_loop` 类型，支持动态插入行：

- 渲染完产品后，记录实际结束行
- 根据产品数量计算后续区域起始行
- 使用 `ws.insert_rows()` 动态插入空白行
- 将 TOTAL、Remark 等内容写入计算后的位置

### 2. 修改 pi_mapping.yaml

```yaml
- cell: A11
  type: dynamic_loop
  data_path: items
  template_row:
    A: item.product_name
    B: item.product_code
    C: item.photo
    D: item.detail_desc
    E: item.specification
    F: item.pcs_per_carton
    G: item.color
    H: item.quantity
    I: item.unit_price
    J:
      type: calc
      formula: "item.quantity * item.unit_price"

# TOTAL 行相对于产品结束行动态计算
- cell: "{TOTAL_ROW}"
  type: static
  value: "TOTAL:"

# 行数过多时分页
- max_items_per_page: 50
- auto_page_break: true
```

### 3. 行号计算公式

```
产品起始行 = 11
产品数量 = len(items)
产品结束行 = 产品起始行 + 产品数量 - 1
TOTAL行 = 产品结束行 + 2
Remark行 = TOTAL行 + 2
银行信息行 = Remark行 + 3
```

### 4. 分页处理（可选）

当产品数量超过 `max_items_per_page`（默认 50）时：
- 自动创建新 Sheet（Sheet2、Sheet3...）
- 每个 Sheet 包含：
  - 表头（公司信息）
  - 产品明细（最多 50 行）
  - 小计（该页 TOTAL）
- 最后一页包含 SAY TOTAL（全局汇总）

## 关键文件

| 文件 | 改动 |
|------|------|
| `backend/exporters/xlsx_template_renderer.py` | 新增 dynamic_loop 类型 |
| `backend/templates/xlsx_mapping/pi_mapping.yaml` | 修改为动态配置 |
| `backend/exporters/pi_exporter.py` | 调用新渲染逻辑 |

## 测试要点

1. 11 个产品：验证原逻辑正常
2. 15 个产品：验证行动态扩展
3. 60 个产品：验证分页
4. 1 个产品：验证最小边界
5. TOTAL/Remark 位置正确性
