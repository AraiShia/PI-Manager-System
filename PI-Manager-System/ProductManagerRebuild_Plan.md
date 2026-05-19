# 产品管理重构方案

## 一、需求分析

### 1.1 当前问题
- OE号作为主要筛选索引不够灵活
- 客户产品编号由客户控制，需要关联到客户
- 一个产品可能有多个OE号
- 需要按客户区分产品编号

### 1.2 核心变化

| 维度 | 现状 | 重构后 |
|-----|------|--------|
| 主要索引 | OE号 | 客户产品编号 |
| OE号 | 单个 | 多个（点击查看） |
| 客户关联 | 无 | 产品-客户关联表 |
| 显示 | 产品名 | 客户编号/产品编号 |

## 二、数据结构设计

### 2.1 产品基础表 (prd_product)
保持现有结构，增加 `is_active` 字段

### 2.2 产品-OE关联表 (prd_product_oe)
```sql
CREATE TABLE prd_product_oe (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,  -- FK到prd_product
    oe_number VARCHAR(100) NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,  -- 是否主OE
    created_at DATETIME DEFAULT NOW(),
    INDEX idx_oe_number (oe_number),
    INDEX idx_product_id (product_id)
);
```

### 2.3 产品-客户关联表 (prd_product_customer)
```sql
CREATE TABLE prd_product_customer (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,  -- FK到prd_product
    customer_id INT NOT NULL,  -- FK到crm_customer
    customer_product_code VARCHAR(100),  -- 客户给的产品编号
    customer_oe_number VARCHAR(100),  -- 客户认定的OE号
    price_usd DECIMAL(15,4),
    price_rmb DECIMAL(15,4),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME,
    UNIQUE KEY uk_product_customer (product_id, customer_id),
    INDEX idx_customer_id (customer_id),
    INDEX idx_customer_product_code (customer_product_code)
);
```

### 2.4 OE号显示逻辑

```python
def get_oe_display(oe_list):
    """
    OE号显示逻辑:
    - 1个OE: 直接显示 (如: "12710304 /M365")
    - 多个OE: 显示 "多OE号"，点击弹窗显示完整列表
    """
    if len(oe_list) == 0:
        return ""
    elif len(oe_list) == 1:
        return oe_list[0]['oe_number']
    else:
        return "多OE号"  # 点击显示弹窗
```

### 2.5 客户产品编号显示逻辑

```python
def get_customer_product_code(customer_code, full_code):
    """
    显示取客户号后面的所有字符
    例如: customer_code="ZOA", full_code="ZOA-S01260006"
    显示: "-S01260006" 或直接显示 "S01260006"
    """
    if full_code and customer_code:
        return full_code.replace(customer_code, "", 1).lstrip("-")
    return full_code
```

## 三、订单总表索引调整

### 3.1 列索引调整

| 列名 | 原索引 | 新索引 | 说明 |
|-----|-------|-------|------|
| 订单日期 | 0 | 0 | |
| ORDER NO. | 1 | 1 | |
| 客户产品编号 | 2 | 2 | 改为从prd_product_customer获取 |
| OE号 | 3 | 3 | 改为显示主OE或"多OE号" |
| 客户需求备注 | 4 | 4 | |
| 产品名称 | 5 | 5 | |
| 图片 | 6 | 6 | |
| 客户型号 | 7 | 7 | |
| OE号.1 | 8 | 8 | 辅助显示 |

### 3.2 新增显示字段

- 客户产品编号（显示取客户号后的字符）
- OE号列表（点击查看完整列表）
- 客户关联价格

## 四、API调整

### 4.1 新增API

```
GET /api/products/customers  - 获取所有产品-客户关联
GET /api/products/{id}/oes   - 获取产品的所有OE号
GET /api/products/customer-list - 按客户筛选产品
POST /api/product-customer   - 创建产品-客户关联
PUT /api/product-customer/{id}  - 更新关联信息
```

### 4.2 订单总表数据获取调整

```python
# 原逻辑
product = products.get(product_id)
oe_number = product.get('oe_number', '')

# 新逻辑
# 1. 按客户获取产品关联信息
customer_product = api.get_product_customer(product_id, customer_id)
# 2. 获取OE列表
oe_list = api.get_product_oes(product_id)
# 3. 显示
display_oe = get_oe_display(oe_list)
display_code = get_customer_product_code(customer_code, customer_product.get('customer_product_code'))
```

## 五、实施计划

### 第一阶段：数据库结构
1. 创建 prd_product_oe 表
2. 创建 prd_product_customer 表
3. 数据迁移（将现有oe_number拆分到新表）

### 第二阶段：后端API
1. 实现OE关联的CRUD
2. 实现产品-客户关联的CRUD
3. 修改订单总表数据获取API

### 第三阶段：前端
1. 修改产品列表显示
2. 修改订单总表列显示
3. 实现OE列表弹窗
4. 实现客户产品编号选择

## 六、注意事项

1. **数据迁移**: 将现有 `prd_product.oe_number` 迁移到 `prd_product_oe`
2. **兼容性**: 保留旧字段用于回退
3. **唯一性**: 产品-客户组合唯一
4. **显示**: 客户编号显示取客户号后的字符