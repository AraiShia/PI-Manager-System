# 包装规格关联表设计方案

**日期:** 2026-05-28
**状态:** 待用户审查

---

## 一、背景与目标

### 1.1 问题描述

订单总表中有 6 列包装规格相关字段（列 29-34, 37），当前数据来源为 `prd_product_supplier`（产品-供应商方案）。这种设计的问题是：

- **不跟随订单**: 产品-供应商方案是产品维度的数据，一个产品可能有多个供应商方案，但订单需要在创建时固定具体规格
- **数据不稳定**: 如果产品-供应商方案变更，已创建的订单数据也会受影响
- **客户-产品组合无法定制**: 无法针对特定客户-产品组合单独设置包装规格

### 1.2 目标

将这 6 列改为跟随"客户-产品-订单"的模式，即数据存储在采购订单明细项及其关联表中，与订单生命周期绑定。

---

## 二、数据模型设计

### 2.1 新的数据来源对照

| 列号 | 列名 | 新数据来源 | 说明 |
|:---:|:---|:---|:---|
| 29 | 包装方式 | `po_purchase_order_item_package.packing_type` | 新关联表 |
| 30 | 采购选项/名称 | `po_purchase_order_item.purchase_channel` | 采购订单已有字段 |
| 32 | 工厂编号 | `po_purchase_order_item.factory_code` | 采购订单已有字段 |
| 33 | 纸箱尺寸 | `po_purchase_order_item_package.carton_l/w/h` | 新关联表 |
| 34 | 打包规格 | `po_purchase_order_item_package.units_per_carton` | 新关联表 |
| 37 | 整箱毛重 | `po_purchase_order_item.gross_weight_kg` | 采购订单已有字段 |

### 2.2 新建表: `po_purchase_order_item_package`

```sql
CREATE TABLE po_purchase_order_item_package (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    po_item_id          BIGINT NOT NULL UNIQUE,        -- FK → po_purchase_order_item.id
    packing_type        VARCHAR(50),                   -- 包装方式: 纸箱/托盘/木箱/无
    units_per_carton    INT,                          -- 每箱数量/打包规格
    carton_length_cm    DECIMAL(10,2),                -- 纸箱长度(cm)
    carton_width_cm     DECIMAL(10,2),                -- 纸箱宽度(cm)
    carton_height_cm    DECIMAL(10,2),                -- 纸箱高度(cm)
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (po_item_id) REFERENCES po_purchase_order_item(id) ON DELETE CASCADE
);

COMMENT ON TABLE po_purchase_order_item_package IS '采购订单明细项包装规格关联表';
```

### 2.3 数据流关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                      数据归属关系                                 │
└─────────────────────────────────────────────────────────────────┘

    PI 订单 (pi_proforma_invoice)
         │
         │ 1:N
         ▼
    PI 明细项 (pi_proforma_invoice_item)
         │
         │ 1:N
         ▼
    采购订单 (po_purchase_order)
         │
         │ 1:N
         ▼
    采购明细项 (po_purchase_order_item) ◄─── 现有字段
    │                                          • factory_code
    │                                          • gross_weight_kg
    │                                          • cartons_estimated
    │                                          • volume_estimated_m3
    │
    │ 1:1 (关联表)
    ▼
    包装规格 (po_purchase_order_item_package) ◄─── 新建
    │                                          • packing_type
    │                                          • units_per_carton
    │                                          • carton_l/w/h
    │
    └── 数据跟随订单生命周期，订单完成后数据固定
```

---

## 三、功能设计

### 3.1 API 接口

| 方法 | 路径 | 说明 |
|:---:|:---|:---|
| GET | `/purchase-items/{id}/package` | 获取采购明细项的包装规格 |
| POST | `/purchase-items/{id}/package` | 创建/更新采购明细项的包装规格 |
| PUT | `/purchase-items/{id}/package` | 更新包装规格 |
| DELETE | `/purchase-items/{id}/package` | 删除包装规格 |

#### GET /purchase-items/{id}/package

**Response:**
```json
{
  "id": 1,
  "po_item_id": 100,
  "packing_type": "纸箱",
  "units_per_carton": 50,
  "carton_length_cm": 40,
  "carton_width_cm": 30,
  "carton_height_cm": 20,
  "created_at": "2026-05-28T10:00:00",
  "updated_at": "2026-05-28T10:00:00"
}
```

**特殊响应:** 如果未找到，返回 `null`（非 404）

#### POST /purchase-items/{id}/package

**Request:**
```json
{
  "packing_type": "纸箱",
  "units_per_carton": 50,
  "carton_length_cm": 40,
  "carton_width_cm": 30,
  "carton_height_cm": 20
}
```

**逻辑:** 如果已存在则更新，不存在则创建（upsert）

### 3.2 前端获取逻辑

在 `_build_order_summary_row` 函数中，需要：

1. 根据 `pi_item_id` 找到对应的采购明细项
2. 从采购明细项获取已有字段（factory_code, gross_weight_kg）
3. 调用 API 获取包装规格关联表数据（packing_type, units_per_carton, carton_l/w/h）

### 3.3 前端编辑界面

在 `OrderSummaryEditDialog` 的采购 Tab 中，需要增加包装规格编辑区域：

```
┌─────────────────────────────────────────────────────────────┐
│ 采购信息                                                     │
├─────────────────────────────────────────────────────────────┤
│ 供应商: [下拉选择]                                           │
│ 采购价: [____] 运费: [____] 杂费: [____]                    │
│                                                             │
│ ┌─ 包装规格 ─────────────────────────────────────────────┐ │
│ │ 包装方式: [纸箱 ▼]  每箱数量: [50]                      │ │
│ │ 纸箱尺寸: 长 [40] × 宽 [30] × 高 [20] (cm)             │ │
│ │ 整箱毛重: [15.5] kg                                     │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、实现计划

| 序号 | 任务 | 涉及文件 | 优先级 |
|:---:|:---|:---|:---:|
| 1 | 创建数据库迁移脚本 | `backend/migrations/` | P0 |
| 2 | 新增 Model | `backend/models/purchase.py` | P0 |
| 3 | 新增 Schema | `backend/schemas/purchase.py` | P0 |
| 4 | 新增 CRUD 函数 | `backend/crud/purchase.py` | P0 |
| 5 | 新增 API 路由 | `backend/routers/purchase.py` | P0 |
| 6 | 更新订单总表数据获取逻辑 | `client/main.py` | P1 |
| 7 | 更新订单总表编辑对话框 | `client/widgets/order_summary_edit_dialog.py` | P1 |
| 8 | 更新文档数据来源映射 | `docs/业务全流程图_文件导入需求.html` | P2 |

---

## 五、向后兼容

### 5.1 迁移策略

1. 新表 `po_purchase_order_item_package` 允许为空（po_item_id 唯一约束）
2. 订单总表读取时，如果包装规格为空，回退到 `prd_product_supplier` 的数据
3. 编辑保存时，只更新已设置的字段

### 5.2 数据迁移（可选）

如果有历史数据需要迁移，可以提供迁移脚本：
- 根据 `po_purchase_order_item.product_id` 找到对应的默认 `prd_product_supplier`
- 将包装规格复制到新表

---

## 六、验收标准

1. **功能验收:**
   - ✅ 创建采购订单时，可以设置包装规格
   - ✅ 编辑采购订单时，可以修改包装规格
   - ✅ 订单总表正确显示包装规格数据
   - ✅ 包装规格与订单生命周期绑定

2. **数据验收:**
   - ✅ 新建记录可以正常保存包装规格
   - ✅ 查询接口返回正确的包装规格数据
   - ✅ 空包装规格不影响订单总表显示

3. **兼容性验收:**
   - ✅ 历史订单在无包装规格时，回退显示产品-供应商方案的数据
   - ✅ 不影响其他模块的正常运行