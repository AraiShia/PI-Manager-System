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

> 💡 双击订单总表任意列（包括以下6列），均可弹出 `OrderSummaryEditDialog` 编辑对话框

| 列号 | 列名 | 新数据来源 | 说明 | 可编辑 |
|:---:|:---|:---|:---|:---:|
| 29 | 包装方式 | `po_purchase_order_item_package.packing_type` | 新关联表 | ✅ |
| 30 | 采购选项/名称 | `po_purchase_order_item.purchase_channel` | 采购订单已有字段 | ✅ |
| 32 | 工厂编号 | `po_purchase_order_item.factory_code` | 采购订单已有字段 | ✅ |
| 33 | 纸箱尺寸 | `po_purchase_order_item_package.carton_l/w/h` | 新关联表 | ✅ |
| 34 | 打包规格 | `po_purchase_order_item_package.units_per_carton` | 新关联表 | ✅ |
| 37 | 整箱毛重 | `po_purchase_order_item.gross_weight_kg` | 采购订单已有字段 | ✅ |

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

### 3.2 智能回填逻辑（自动填充历史数据）

当用户选择客户+产品组合时，系统自动查找该组合的历史包装规格并填充。

#### 触发时机

- 用户在订单总表编辑对话框中选择/切换客户
- 用户在订单总表编辑对话框中选择/切换产品
- 同时满足 customer_id + product_id 时触发

#### 回填规则

| 条件 | 结果 |
|:---|:---|
| 找到历史记录 | 自动填充，显示提示 "已自动填充上次的包装规格" |
| 未找到历史记录 | 保持为空，显示提示 "暂无历史包装规格，请手动填写" |

**不设置回退方案：** 严格跟随"客户-产品-订单"模式，确保数据来源清晰。

#### 查询逻辑

```python
# 查找最近一次的历史包装规格
条件: customer_id = A AND product_id = B
排序: po_purchase_order_item_package.created_at DESC
取: 第一条记录
```

#### 注意事项

1. **允许修改：** 自动填充只是默认值，用户可以修改
2. **跨供应商：** 如果同一产品换了供应商，仍使用最近一次的数据
3. **性能考虑：** 可在选择客户/产品时异步查询，不阻塞 UI
4. **初次订单：** 未找到历史记录时，保持为空，用户手动填写

---

## 四、API 接口补充

### 4.1 新增智能回填接口

| 方法 | 路径 | 说明 |
|:---:|:---|:---|
| GET | `/purchase-items/history-package` | 根据客户+产品获取历史包装规格 |

#### GET /purchase-items/history-package?customer_id={id}&product_id={id}

**Query Parameters:**
- `customer_id` (required): 客户 ID，必须为正整数
- `product_id` (required): 产品 ID，必须为正整数

**参数校验：**
- 如果 `customer_id` 或 `product_id` 缺失或非正整数，返回 `400 Bad Request`
  ```json
  { "detail": "缺少必填参数: customer_id" }
  ```

**Response - 有历史数据时:**
```json
{
  "found": true,
  "package": {
    "packing_type": "纸箱",
    "units_per_carton": 50,
    "carton_length_cm": 40,
    "carton_width_cm": 30,
    "carton_height_cm": 20
  },
  "source": "po_item_id: 123",
  "created_at": "2026-05-28T10:00:00"
}
```

**Response - 无历史数据时（正常返回，非错误）:**
```json
{
  "found": false,
  "package": null
}
```

**Response - 参数校验失败时:**
```json
{
  "detail": "缺少必填参数: customer_id"
}
```

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

4. **智能回填验收:**
   - ✅ 同一客户+产品再次下单时，自动填充历史包装规格
   - ✅ 填充后用户可以修改
   - ✅ 未找到历史记录时，使用空值

5. **订单总表交互验收:**
   - ✅ 双击订单总表任意列，可弹出编辑对话框（OrderSummaryEditDialog）
   - ✅ 编辑对话框支持编辑所有 41 列数据
   - ✅ 保存后自动刷新订单总表显示

---

## 七、订单总表双击交互

### 7.1 双击打开编辑对话框（智能 Tab 定位）

在订单总表（`order_detail_table`）中，双击任意单元格可弹出编辑对话框，并自动定位到对应的 Tab：

```
订单总表界面
┌─────────────────────────────────────────────────────────────────────┐
│  0   │  1   │  2   │  3   │ ... │  29  │  30  │ ... │  41  │
│ 日期 │ PI号 │ 客户 │ OE号 │     │ 包装方式 │ 采购选项 │     │ 开票情况 │
├─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│ 05-28│ A001 │ 张三 │ OE001│ ... │ 纸箱    │ 1688    │ ... │ 已开票   │
│ 05-27│ A002 │ 李四 │ OE002│ ... │ 托盘    │ 1688    │ ... │ 未开票   │
│      │      │      │      │     │  ← 双击任意单元格 →       │
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘

        ↓ 双击 列29(包装方式)
        ┌─────────────────────────────────────────────┐
        │        OrderSummaryEditDialog              │
        │  ┌───────────────────────────────────────┐  │
        │  │ 📋 订单信息 │ 👤 客户 │ 📦 产品 │ ... │  │
        │  ├───────────────────────────────────────┤  │
        │  │         自动定位到 Tab4(采购信息)      │  │
        │  │         滚动到包装规格字段            │  │
        │  └───────────────────────────────────────┘  │
        │              [取消]  [保存]               │
        └─────────────────────────────────────────────┘
```

### 7.2 列号 → Tab 映射表

根据列所属的数据表，自动判断打开对应的 Tab：

| 列号 | 列名 | 数据来源表 | 定位 Tab |
|:---:|:---|:---|:---:|
| 0 | 订单日期 | `pi_proforma_invoice` | Tab1 |
| 1 | PI号 | `pi_proforma_invoice` | Tab1 |
| 2 | 客户编号 | `crm_customer` | Tab2 |
| 3 | OE号 | `pi_proforma_invoice_item` | Tab1 |
| 4 | 客户需求备注 | `pi_proforma_invoice_item` | Tab1 |
| 5 | 产品名称 | `prd_product` | Tab3 |
| 6 | 图片 | `prd_product` | Tab3 |
| 7 | 客户型号 | `pi_proforma_invoice_item` | Tab1 |
| 8 | OE号.1 | `pi_proforma_invoice_item` | Tab1 |
| 9 | 数量 | `pi_proforma_invoice_item` | Tab1 |
| 10 | 报价 | `pi_proforma_invoice_item` | Tab1 |
| 11 | 合计金额 | (计算字段) | Tab1 |
| 12 | 客户最新回复 | `customer_replies` | Tab1 |
| 13 | 客户预付款 | `ar_customer_payment` | Tab5 |
| 14 | 待收尾款 | (计算字段) | Tab5 |
| 15 | 预估美金报价 | (计算字段) | Tab4 |
| 16 | 预估毛利率 | (计算字段) | Tab4 |
| 17 | 采购价格 | `po_purchase_order` | Tab4 |
| 18 | 运费 | `po_purchase_order` | Tab4 |
| 19 | 杂费 | `po_purchase_order` | Tab4 |
| 20 | 总金额 | `pi_proforma_invoice` | Tab1 |
| 21 | 工厂简称 | `sup_supplier` | Tab4 |
| 22 | 店铺链接 | `sup_supplier` | Tab4 |
| 23 | 交货日期 | `po_purchase_order` | Tab4 |
| 24 | 是否已收货 | `sh_shipment` | Tab5 |
| 25 | 工厂订金 | `ap_supplier_payment` | Tab5 |
| 26 | 工厂尾款 | `ap_supplier_payment` | Tab5 |
| 27 | 入库操作 | `inv_inventory` | Tab5 |
| 28 | 入库数量 | `inv_inventory` | Tab5 |
| 29 | 包装方式 | `po_purchase_order_item_package` | Tab4 |
| 30 | 采购选项/名称 | `po_purchase_order_item` | Tab4 |
| 31 | 产品细节 | `prd_product` | Tab3 |
| 32 | 工厂编号 | `po_purchase_order_item` | Tab4 |
| 33 | 纸箱尺寸 | `po_purchase_order_item_package` | Tab3 |
| 34 | 打包规格 | `po_purchase_order_item_package` | Tab3 |
| 35 | 箱数 | (计算字段) | Tab3 |
| 36 | 预估体积 | (计算字段) | Tab3 |
| 37 | 整箱毛重 | `po_purchase_order_item` | Tab3 |
| 38 | 总重量 | (计算字段) | Tab3 |
| 39 | 品牌 | `prd_product` | Tab3 |
| 40 | 开票情况 | `order_file` | Tab5 |

**默认 Tab 规则：** 如果某列没有精确匹配，根据数据来源的主表判断：
- PI 相关列 → Tab1
- 客户相关列 → Tab2
- 产品相关列 → Tab3
- 采购相关列 → Tab4
- 财务相关列 → Tab5

### 7.3 触发逻辑（智能 Tab 定位）

```python
class OrderSummaryView:
    # 列号 → Tab 索引映射
    COLUMN_TO_TAB = {
        # 订单信息
        0: 0, 1: 0, 3: 0, 4: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 20: 0,
        # 客户信息
        2: 1,
        # 产品信息
        5: 2, 6: 2, 31: 2, 33: 2, 34: 2, 35: 2, 36: 2, 37: 2, 38: 2, 39: 2,
        # 采购信息
        17: 3, 18: 3, 19: 3, 21: 3, 22: 3, 23: 3, 29: 3, 30: 3, 32: 3,
        # 付款信息
        13: 4, 14: 4, 24: 4, 25: 4, 26: 4, 27: 4, 28: 4, 40: 4,
    }

    def _setup_order_detail_table(self):
        self.order_detail_table.itemDoubleClicked.connect(
            self._on_order_row_double_clicked
        )

    def _on_order_row_double_clicked(self, item):
        row = item.row()
        col = item.column()
        pi_item_id = self._get_pi_item_id(row)

        # 获取完整订单数据
        order_data = self._get_order_full_data(pi_item_id)

        # 确定目标 Tab
        target_tab = self.COLUMN_TO_TAB.get(col, 0)  # 默认 Tab1

        # 弹出编辑对话框，指定默认 Tab
        dialog = OrderSummaryEditDialog(order_data, self.api_client, self)
        dialog.set_default_tab(target_tab)  # 设置默认 Tab

        if dialog.exec_() == QDialog.Accepted:
            self.load_order_summary()


class OrderSummaryEditDialog(QDialog):
    def __init__(self, order_data, api_client, parent=None):
        super().__init__(parent)
        self.order_data = order_data
        self.api_client = api_client
        self._default_tab = 0  # 默认 Tab1
        self._setup_ui()

    def set_default_tab(self, tab_index):
        self._default_tab = tab_index

    def _setup_ui(self):
        tabs = QTabWidget()
        tabs.addTab(self._create_order_tab(), "📋 订单信息")    # Tab 0
        tabs.addTab(self._create_customer_tab(), "👤 客户信息")  # Tab 1
        tabs.addTab(self._create_product_tab(), "📦 产品信息")  # Tab 2
        tabs.addTab(self._create_purchase_tab(), "🏭 采购信息")  # Tab 3
        tabs.addTab(self._create_payment_tab(), "💰 付款信息")  # Tab 4

        # 智能定位到目标 Tab
        if 0 <= self._default_tab < tabs.count():
            tabs.setCurrentIndex(self._default_tab)
```

---

## 八、前端编辑界面

在 `OrderSummaryEditDialog` 的采购 Tab 中，需要增加包装规格编辑区域：

```
┌─────────────────────────────────────────────────────────────┐
│ 采购信息                                                     │
├─────────────────────────────────────────────────────────────┤
│ 供应商: [下拉选择]                                           │
│ 采购价: [____] 运费: [____] 杂费: [____]                     │
│                                                             │
│ ┌─ 包装规格 ─────────────────────────────────────────────┐   │
│ │ 包装方式: [请选择 ▼]                                    │   │
│ │ 每箱数量: [____]                                        │   │
│ │ 纸箱尺寸: 长 [__] × 宽 [__] × 高 [__] (cm)              │   │
│ │ 整箱毛重: [____] kg                                     │   │
│ │                                                         │   │
│ │ ℹ️ 暂无历史包装规格，请手动填写                          │   │
│ └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 8.1 提示交互设计

| 场景 | 提示样式 | 文本 |
|:---|:---|:---|
| 无历史数据 | 灰色信息提示 | ℹ️ 暂无历史包装规格，请手动填写 |
| 有历史数据 | 绿色成功提示 | ✓ 已自动填充上次的包装规格（可修改） |
| 加载中 | 灰色加载提示 | ⏳ 正在获取历史包装规格... |

### 8.2 智能回填触发逻辑

```python
class OrderSummaryEditDialog:
    def __init__(self):
        self._packing_hint_label = QLabel()  # 提示标签
        self._packing_hint_label.setStyleSheet("color: gray;")
        self._packing_hint_label.hide()

    def on_customer_changed(self, customer_id):
        self._try_auto_fill_packing_spec()

    def on_product_changed(self, product_id):
        self._try_auto_fill_packing_spec()

    def _try_auto_fill_packing_spec(self):
        if not (self.customer_id and self.product_id):
            return

        # 显示加载提示
        self._show_hint("⏳ 正在获取历史包装规格...", is_loading=True)

        # 异步调用 API
        self._fetch_history_package(
            customer_id=self.customer_id,
            product_id=self.product_id,
            callback=self._on_package_received
        )

    def _on_package_received(self, result):
        if result.get("found") and result.get("package"):
            # 有历史数据，填充并显示绿色提示
            self._fill_packing_spec_fields(result["package"])
            self._show_hint("✓ 已自动填充上次的包装规格（可修改）", is_success=True)
        else:
            # 无历史数据，显示灰色提示
            self._show_hint("ℹ️ 暂无历史包装规格，请手动填写", is_info=True)
            self._clear_packing_spec_fields()
```

---

## 九、实现计划

| 序号 | 任务 | 涉及文件 | 优先级 |
|:---:|:---|:---|:---:|
| 1 | 创建数据库迁移脚本 | `backend/migrations/` | P0 |
| 2 | 新增 Model | `backend/models/purchase.py` | P0 |
| 3 | 新增 Schema | `backend/schemas/purchase.py` | P0 |
| 4 | 新增 CRUD 函数 | `backend/crud/purchase.py` | P0 |
| 5 | 新增 API 路由（CRUD + 智能回填） | `backend/routers/purchase.py` | P0 |
| 6 | 更新订单总表数据获取逻辑 | `client/main.py` | P1 |
| 7 | 更新订单总表编辑对话框（智能回填） | `client/widgets/order_summary_edit_dialog.py` | P1 |
| 8 | 更新文档数据来源映射 | `docs/业务全流程图_文件导入需求.html` | P2 |
| 9 | 新增订单总表双击编辑功能 | `client/main.py` | P1 |