# PI订单管理系统 - 数据库结构设计

> 版本：v2.0（同步所有更新）
> 日期：2026-04-29

---

## 一、数据库设计策略

### 1.1 方案选择：独立数据库（推荐）

| 方案 | 优点 | 缺点 | 适用场景 |
|-----|------|------|---------|
| **独立数据库（推荐）** | 数据完全隔离、便于独立备份和恢复、故障不影响其他部门 | 服务器资源占用较高 | 部门数据量大、独立性要求高 |
| 共享数据库+部门字段隔离 | 资源利用率高 | 数据隔离性弱、备份恢复复杂 | 部门数据量小、关联查询多 |

### 1.2 数据库命名规范

| 部门 | 数据库名 |
|-----|---------|
| 维那(W) | wny_pimain |
| 索英普(S) | syy_pimain |
| 马迪那(M) | mdn_pimain |
| 银达(D) | ydd_pimain |

---

## 二、核心表结构（★已同步所有更新）

### 2.1 部门表

```sql
CREATE TABLE sys_department (
    dept_id       VARCHAR(10) PRIMARY KEY,  -- W/S/M/D
    dept_name     VARCHAR(50) NOT NULL,
    db_name       VARCHAR(50) NOT NULL,
    created_at    DATETIME,
    status        TINYINT DEFAULT 1
);
```

### 2.2 产品表（★已更新：新增包装体积字段）

```sql
CREATE TABLE prd_product (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id             VARCHAR(10) NOT NULL,
    product_code        VARCHAR(50) NOT NULL UNIQUE,  -- 系统编号，如 SA01260001
    oe_number           VARCHAR(100) NOT NULL,       -- OE号（产品唯一标识）
    factory_code        VARCHAR(100),               -- 工厂编号
    brand               VARCHAR(100),               -- 品牌
    detail_desc         VARCHAR(500) NOT NULL,      -- 细节描述
    supplier_id         BIGINT,                      -- 主要供应商
    exw_price_incl      DECIMAL(15,4),              -- EXW含税价
    exw_price_excl      DECIMAL(15,4),              -- EXW不含税价
    fob_price_incl      DECIMAL(15,4),              -- FOB含税价
    fob_price_excl      DECIMAL(15,4),              -- FOB不含税价
    freight             DECIMAL(15,4),
    packing_fee         DECIMAL(15,4),
    purchase_channel    VARCHAR(100),
    
    -- ★ 包装体积计算（新增）
    carton_length_cm    DECIMAL(10,2),              -- 纸箱长度(cm)
    carton_width_cm     DECIMAL(10,2),              -- 纸箱宽度(cm)
    carton_height_cm    DECIMAL(10,2),              -- 纸箱高度(cm)
    units_per_carton    INT,                        -- 每箱数量 ★必填
    carton_volume_m3    DECIMAL(12,6),              -- 每箱体积(m³)=长×宽×高/1000000
    gross_weight_kg     DECIMAL(10,4),              -- 每箱毛重(kg)
    
    -- 尺寸/重量（单品）
    length_cm           DECIMAL(10,2),
    width_cm            DECIMAL(10,2),
    height_cm           DECIMAL(10,2),
    weight_kg           DECIMAL(10,4),
    
    category_id         INT,
    status              TINYINT DEFAULT 1,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_oe (oe_number),
    INDEX idx_dept (dept_id)
);

-- 产品图片表
CREATE TABLE prd_product_image (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id      BIGINT NOT NULL,
    image_url       VARCHAR(500) NOT NULL,
    image_type      TINYINT DEFAULT 1,  -- 1:主图 2:细节图
    sort_order      INT DEFAULT 0
);

-- 产品-客户号关联表（一个OE号可对应多个工厂的不同客户号）
CREATE TABLE prd_product_customer_code (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id      BIGINT NOT NULL,
    supplier_id     BIGINT,
    customer_code   VARCHAR(100) NOT NULL,  -- 工厂给客户分配的编号
    remark          VARCHAR(200)
);
```

### 2.3 客户表

```sql
CREATE TABLE crm_customer (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    customer_code   VARCHAR(20) NOT NULL UNIQUE,  -- 客户编号，如 A01
    customer_name   VARCHAR(200) NOT NULL,
    country         VARCHAR(100),
    basic_require   TEXT,
    special_require TEXT,  -- ★ 特殊要求，PI时自动带出
    payment_terms   VARCHAR(100),
    status          TINYINT DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 客户收货地址表
CREATE TABLE crm_customer_address (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id     BIGINT NOT NULL,
    country         VARCHAR(100),
    port            VARCHAR(200),
    address_detail  VARCHAR(500),
    is_default      TINYINT DEFAULT 0
);

-- 客户联系人表
CREATE TABLE crm_customer_contact (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id     BIGINT NOT NULL,
    name            VARCHAR(100),
    phone           VARCHAR(50),
    email           VARCHAR(100),
    position        VARCHAR(100),
    is_primary      TINYINT DEFAULT 0
);
```

### 2.4 供应商表

```sql
CREATE TABLE sup_supplier (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    supplier_code   VARCHAR(50) NOT NULL UNIQUE,
    supplier_name   VARCHAR(200) NOT NULL,
    region          VARCHAR(100),
    source_location VARCHAR(200),
    invoice_type    TINYINT,  -- 1:增票 2:普票 3:不开发票
    tax_rate        DECIMAL(5,2),
    supply_cycle_days INT,
    return_policy   TEXT,
    payment_terms   VARCHAR(100),
    status          TINYINT DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE sup_supplier_contact (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    supplier_id     BIGINT NOT NULL,
    name            VARCHAR(100),
    phone           VARCHAR(50),
    is_primary      TINYINT DEFAULT 0
);
```

### 2.5 报价单表（★版本管理：保留≥5份）

```sql
CREATE TABLE quo_quote (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    quote_no        VARCHAR(50) NOT NULL UNIQUE,
    customer_id     BIGINT NOT NULL,
    total_amount    DECIMAL(15,4),
    currency        VARCHAR(10) DEFAULT 'USD',
    valid_until     DATE,
    payment_terms   VARCHAR(100),
    remark          TEXT,
    status          TINYINT DEFAULT 1,  -- 1:草稿 2:已发送 3:已确认 4:已过期
    created_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE quo_quote_item (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    quote_id        BIGINT NOT NULL,
    product_id      BIGINT NOT NULL,
    oe_number       VARCHAR(100),
    customer_code   VARCHAR(100),
    quantity        DECIMAL(15,4) NOT NULL,
    unit_price      DECIMAL(15,4) NOT NULL,
    total_price     DECIMAL(15,4) NOT NULL,
    remark          VARCHAR(500)
);
```

### 2.6 PI单表（★已更新：灵活付款阶段 + 价格历史）

```sql
-- PI单主表（★移除固定尾款字段）
CREATE TABLE pi_proforma_invoice (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    pi_no           VARCHAR(50) NOT NULL UNIQUE,  -- PI号
    customer_id     BIGINT NOT NULL,
    total_amount    DECIMAL(15,4),
    currency        VARCHAR(10) DEFAULT 'USD',
    status          TINYINT DEFAULT 1,  -- 1:待确认 2:已付定金 3:部分尾款 4:已完成（动态计算）
    created_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_customer (customer_id),
    INDEX idx_status (status)
);

-- PI单明细（★支持差异化定价和备注）
CREATE TABLE pi_proforma_invoice_item (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    pi_id               BIGINT NOT NULL,
    product_id          BIGINT NOT NULL,
    oe_number           VARCHAR(100),
    customer_code       VARCHAR(100),   -- 差异化：可调整
    detail_desc         VARCHAR(500),   -- 差异化描述
    quantity            DECIMAL(15,4) NOT NULL,
    unit_price          DECIMAL(15,4) NOT NULL,  -- 差异化单价
    total_price         DECIMAL(15,4) NOT NULL,
    remark              TEXT
);

-- ★ PI付款阶段表（灵活尾款，次数不固定）
CREATE TABLE pi_payment_stage (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    pi_id           BIGINT NOT NULL,
    stage_type      VARCHAR(20) NOT NULL,  -- 'deposit' 定金 / 'balance' 尾款
    stage_no        INT,                    -- 尾款序号：1,2,3...（定金此字段为空）
    amount          DECIMAL(15,4) NOT NULL,
    due_date        DATE,
    paid_date       DATE,                   -- NULL=未付
    status          TINYINT DEFAULT 1,      -- 1:待付 2:已付
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_pi (pi_id)
);

-- ★ PI单版本历史表（保留≥3份）
CREATE TABLE pi_proforma_invoice_version (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    pi_id           BIGINT NOT NULL,
    version_no      INT NOT NULL,
    snapshot_data   JSON NOT NULL,
    change_desc     VARCHAR(500),
    created_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_pi (pi_id)
);

-- ★ PI单明细历史价格表（保留≥3份，用于新PI自动带出上次价格）
CREATE TABLE pi_price_history (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    customer_id     BIGINT NOT NULL,
    product_id      BIGINT NOT NULL,
    pi_id           BIGINT NOT NULL,
    pi_item_id      BIGINT,
    unit_price      DECIMAL(15,4) NOT NULL,
    remark          TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_customer_product (customer_id, product_id),
    INDEX idx_created (created_at)
);
```

### 2.7 采购单表

```sql
CREATE TABLE po_purchase_order (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    po_no           VARCHAR(50) NOT NULL UNIQUE,
    pi_id           BIGINT NOT NULL,
    supplier_id     BIGINT NOT NULL,
    total_amount    DECIMAL(15,4),
    contract_date   DATE,
    status          TINYINT DEFAULT 1,  -- 1:已采购(黄) 2:待入库(蓝) 3:已完成(黑)
    created_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_pi (pi_id),
    INDEX idx_supplier (supplier_id)
);

-- ★ 采购明细（新增体积自动计算字段）
CREATE TABLE po_purchase_order_item (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    po_id               BIGINT NOT NULL,
    pi_item_id          BIGINT,
    product_id          BIGINT NOT NULL,
    color_detail        VARCHAR(500),
    quantity            DECIMAL(15,4) NOT NULL,
    unit_price          DECIMAL(15,4) NOT NULL,
    total_price         DECIMAL(15,4) NOT NULL,
    
    -- ★ 体积自动计算（输入数量后自动计算）
    cartons_estimated   DECIMAL(12,2),   -- 预计箱数 = quantity / units_per_carton
    volume_estimated_m3 DECIMAL(12,6),    -- 预计总体积 = cartons_estimated * carton_volume_m3
    gross_weight_kg    DECIMAL(12,4)     -- 预计毛重 = cartons_estimated * gross_weight_kg
);

-- 1688采购记录表
CREATE TABLE po_1688_purchase (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    po_id           BIGINT,
    pi_id           BIGINT,
    product_id      BIGINT,
    product_url     VARCHAR(500),
    freight         DECIMAL(15,4),
    payment_method  VARCHAR(100),
    gross_weight    DECIMAL(10,4)
);
```

### 2.8 出货表（★新增体积计算）

```sql
CREATE TABLE sh_shipment (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    shipment_no     VARCHAR(50) NOT NULL UNIQUE,
    pi_id           BIGINT NOT NULL,
    shipment_date   DATE,
    ci_document     VARCHAR(500),  -- CI文档路径（三联）
    pl_document     VARCHAR(500),  -- PL文档路径（三联）
    payment_status  TINYINT DEFAULT 1,
    status          TINYINT DEFAULT 1,
    created_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_pi (pi_id)
);

-- ★ 出货明细（新增体积字段）
CREATE TABLE sh_shipment_item (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    shipment_id     BIGINT NOT NULL,
    product_id      BIGINT NOT NULL,
    quantity        DECIMAL(15,4) NOT NULL,
    
    -- ★ 出货时计算体积
    cartons_shipped    DECIMAL(12,2),   -- 出货箱数
    volume_shipped_m3  DECIMAL(12,6),    -- 出货总体积
    
    remark          VARCHAR(500)
);
```

### 2.9 收付款表

```sql
-- 客户收款记录
CREATE TABLE ar_customer_payment (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    receipt_no      VARCHAR(50) NOT NULL UNIQUE,
    pi_id           BIGINT NOT NULL,
    customer_id     BIGINT NOT NULL,
    amount          DECIMAL(15,4) NOT NULL,
    handling_fee    DECIMAL(15,4),
    payment_date    DATE NOT NULL,
    remittance_bank VARCHAR(200),
    currency       VARCHAR(10),
    water_image     VARCHAR(500),  -- 水单图片路径
    created_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 供应商付款记录
CREATE TABLE ap_supplier_payment (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    payment_no      VARCHAR(50) NOT NULL UNIQUE,
    po_id           BIGINT NOT NULL,
    supplier_id     BIGINT NOT NULL,
    deposit_amount  DECIMAL(15,4),
    deposit_date    DATE,
    balance_amount  DECIMAL(15,4),
    balance_date    DATE,
    total_amount    DECIMAL(15,4),
    paid_amount     DECIMAL(15,4),
    unpaid_amount   DECIMAL(15,4),
    status          TINYINT DEFAULT 1,
    payment_proof   VARCHAR(500),
    created_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 2.10 库存表（★已更新：跟客户走，不囤货）

```sql
-- ★ 实时库存表（跟客户走，不囤货）
CREATE TABLE inv_inventory (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id             VARCHAR(10) NOT NULL,
    product_id          BIGINT NOT NULL,
    customer_id         BIGINT NOT NULL,         -- ★ 必填，跟客户走
    pi_id               BIGINT,                   -- 对应PI
    po_id               BIGINT,                   -- 对应采购单
    supplier_id         BIGINT,                  -- 供应商
    
    -- 数量追踪
    total_quantity      DECIMAL(15,4) NOT NULL,  -- 总采购量
    shipped_quantity    DECIMAL(15,4) DEFAULT 0, -- 已出货量
    pending_quantity    DECIMAL(15,4) DEFAULT 0,  -- 待出货（自动=total-shipped）
    
    purchase_price      DECIMAL(15,4),           -- 采购单价
    
    -- ★ 货物位置（供应商仓/在途/客户处，不在公司仓）
    current_location    VARCHAR(200),            -- 货物当前位置
    location_desc       VARCHAR(500),            -- 位置描述
    
    purchase_date       DATE,                    -- 采购日期
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_customer (customer_id),
    INDEX idx_product (product_id),
    INDEX idx_location (current_location)
);

-- 库存流水账（全程追溯）
CREATE TABLE inv_inventory_log (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    product_id      BIGINT NOT NULL,
    customer_id     BIGINT NOT NULL,
    pi_id           BIGINT,
    
    change_type     TINYINT NOT NULL,  -- 1:采购入库 2:出货 3:在途变更 4:到达签收
    change_quantity DECIMAL(15,4) NOT NULL,  -- 正数=增加，负数=减少
    before_quantity DECIMAL(15,4) NOT NULL,
    after_quantity  DECIMAL(15,4) NOT NULL,
    
    ref_type        VARCHAR(50),  -- PO/SH/PI
    ref_id          BIGINT,
    remark          VARCHAR(500),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_customer (customer_id),
    INDEX idx_product (product_id)
);
```

### 2.11 编号规则表

```sql
CREATE TABLE sys_number_rule (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    rule_type       VARCHAR(50) NOT NULL UNIQUE,  -- PRODUCT/PI/PO/QUOTE
    rule_pattern    VARCHAR(200) NOT NULL,
    current_value   BIGINT DEFAULT 0,
    reset_frequency VARCHAR(20) DEFAULT 'YEAR',
    last_reset_date DATE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE sys_number_history (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    rule_type       VARCHAR(50) NOT NULL,
    generated_no    VARCHAR(100) NOT NULL,
    related_id      BIGINT,
    related_type    VARCHAR(50),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 2.12 操作日志表

```sql
CREATE TABLE sys_operation_log (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10),
    table_name      VARCHAR(100) NOT NULL,
    record_id       BIGINT NOT NULL,
    operation_type  VARCHAR(20) NOT NULL,  -- INSERT/UPDATE/DELETE
    old_data        JSON,
    new_data        JSON,
    operator_id     BIGINT,
    operator_ip     VARCHAR(50),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 三、公共基础表（跨部门共享）

```sql
CREATE TABLE pub_category (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    category_code   VARCHAR(20) NOT NULL UNIQUE,  -- C01/F01/B01
    category_name   VARCHAR(100) NOT NULL,
    parent_id       BIGINT,
    sort_order      INT DEFAULT 0
);

CREATE TABLE pub_region (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    region_code     VARCHAR(20) NOT NULL UNIQUE,
    region_name     VARCHAR(100) NOT NULL,
    parent_code     VARCHAR(20),
    level           TINYINT DEFAULT 1  -- 1:省 2:市 3:县
);

CREATE TABLE pub_currency (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    currency_code   VARCHAR(10) NOT NULL UNIQUE,
    currency_name   VARCHAR(50),
    exchange_rate   DECIMAL(15,4),
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

---

## 四、E-R图（★已更新）

### 4.1 数据流向总图

```plaintext
                    ┌──────────────────────────────────────────────────────┐
                    │                      报价阶段                         │
                    │  ┌──────────┐    ┌──────────┐    ┌──────────┐       │
                    │  │ 客户询价  │───►│ 历史价格  │───►│ 报价单    │       │
                    │  └──────────┘    │ 自动带出  │    └────┬─────┘       │
                    │                 └──────────┘         │              │
                    └────────────────────│────────────────┘              │
                                         │                              │
                                         ▼                              │
                    ┌──────────────────────────────────────────────────┤
                    │                      PI阶段                          │
                    │  ┌──────────────┐    ┌──────────────┐               │
                    │  │ 选择客户+产品 │───►│ 上次购买价格 │               │
                    │  │              │    │ +备注自动填充 │               │
                    │  └──────────────┘    └───────┬──────┘               │
                    │                              │                       │
                    │  ┌──────────────┐    ┌───────┴──────┐    ┌─────────┐ │
                    │  │ 付款阶段配置  │───►│ PI单(核心单据)│    │ 特殊要求│ │
                    │  │ 灵活配置      │    │              │    │ 自动带出│ │
                    │  │ deposit+     │    └───────┬──────┘    └─────────┘ │
                    │  │ balance1/2/3 │            │                       │
                    │  └──────────────┘            │                       │
                    │                              │                       │
                    │        ┌─────────────────────┼─────────────────────┐ │
                    │        ▼                     ▼                     ▼ │
                    │  ┌──────────┐    ┌──────────────┐    ┌──────────┐   │
                    │  │ 收款记录  │    │ 采购合同     │    │ 出货登记  │   │
                    │  │ (定金/   │    │ (对应供应商) │    │ CI/PL   │   │
                    │  │ 尾款1/2/3│    └──────┬───────┘    └──────────┘   │
                    │  └────┬─────┘            │                            │
                    └───────┼───────────────────┼────────────────────────────┘
                            │                   │
                            │ 采购确认           │ 采购后货物状态更新
                            ▼                   ▼
                    ┌───────────────────────────────────────────────┐
                    │              采购完成阶段                     │
                    │                                               │
                    │  ★ 不入库，货物位置直接更新为：               │
                    │    供应商仓 ──► 在途 ──► 客户处              │
                    │                                               │
                    │  INV_INVENTORY 更新：                         │
                    │  + customer_id (必填，跟客户走)               │
                    │  + total_quantity += 采购数量                 │
                    │  + current_location = 供应商仓               │
                    │  + change_type = 1 (采购入库)                │
                    │                                               │
                    └───────────────────────────────────────────────┘
                                         │
                                         │ 出货时
                                         ▼
                    ┌───────────────────────────────────────────────┐
                    │              出货阶段                         │
                    │                                               │
                    │  出货时：                                      │
                    │  1. 筛选该客户+该PI的未出完库存                │
                    │  2. 选择批次 + 输入本次出货数量                │
                    │  3. 自动：                                    │
                    │     - pending_quantity -= 出货数量            │
                    │     - shipped_quantity += 出货数量             │
                    │     - current_location = 在途/客户处          │
                    │     - 记录库存流水 (change_type=2 出货)       │
                    │  4. 自动计算出货体积                          │
                    │                                               │
                    └───────────────────────────────────────────────┘
```

### 4.2 核心E-R：PI付款阶段灵活设计

```plaintext
┌─────────────────────────────────────────────────────────────────┐
│             PI付款阶段完全灵活设计                                │
│                                                                 │
│   PI_PAYMENT_STAGE（付款阶段表）                                 │
│   + id: BIGINT                                                 │
│   + pi_id (FK) ──────────────────────────┐                     │
│   + stage_type: VARCHAR(20)             │                     │
│     ★ 'deposit' = 定金                  │                     │
│     ★ 'balance' = 尾款                  │                     │
│   + stage_no: INT                       │                     │
│     ★ NULL = 定金（只有一个）            │                     │
│     ★ 1,2,3... = 尾款序号               │                     │
│   + amount: DECIMAL                     │                     │
│   + due_date: DATE                       │                     │
│   + paid_date: DATE (NULL=未付)           │                     │
│   + status: TINYINT (1:待付 2:已付)       │                     │
│   └───────────────────────────────────────┘                     │
│              ▲                                                   │
│              │ N:1                                               │
│              │                                                   │
│   ┌──────────┴──────────┐                                        │
│   │ PI_PROFORMA_INVOICE│                                        │
│   │   PI单主表           │─────────────────────────────────────┘
│   │ PK: pi_id          │ 1:N
│   │ + pi_no             │
│   │ + customer_id (FK)  │
│   │ + total_amount      │
│   │ + status ★动态计算  │
│   └─────────────────────┘

付款场景示例：

场景A（定金+一次尾款）：
┌────────────────────────────────────────┐
│ stage_type  │ stage_no │ amount │ 状态 │
├────────────────────────────────────────┤
│ deposit    │ NULL    │ 30%   │ 已付 │
│ balance    │ 1       │ 70%   │ 待付 │
└────────────────────────────────────────┘

场景B（定金分两期，尾款三期）：
┌────────────────────────────────────────┐
│ stage_type  │ stage_no │ amount │ 状态 │
├────────────────────────────────────────┤
│ deposit    │ NULL    │ 20%   │ 已付 │
│ deposit    │ NULL    │ 10%   │ 已付 │
│ balance    │ 1       │ 30%   │ 已付 │
│ balance    │ 2       │ 30%   │ 待付 │
│ balance    │ 3       │ 10%   │ 待付 │
└────────────────────────────────────────┘

场景C（无定金，直接尾款）：
┌────────────────────────────────────────┐
│ stage_type  │ stage_no │ amount │ 状态 │
├────────────────────────────────────────┤
│ balance    │ 1       │ 50%   │ 已付 │
│ balance    │ 2       │ 50%   │ 待付 │
└────────────────────────────────────────┘
```

---

## 五、表间关系速查表（★已更新）

| 主表 | 从表 | 关系 | 说明 |
|-----|------|------|------|
| CRM_CUSTOMER | CRM_CUSTOMER_ADDRESS | 1:N | 一个客户多个收货地址 |
| CRM_CUSTOMER | CRM_CUSTOMER_CONTACT | 1:N | 一个客户多个联系人 |
| CRM_CUSTOMER | PI_PROFORMA_INVOICE | 1:N | 一个客户多个PI单 |
| PI_PROFORMA_INVOICE | PI_PAYMENT_STAGE | 1:N | 一个PI多个付款阶段（灵活） |
| PI_PROFORMA_INVOICE | PI_PROFORMA_INVOICE_ITEM | 1:N | 一个PI多个明细 |
| PI_PROFORMA_INVOICE | PI_PROFORMA_INVOICE_VERSION | 1:N | 一个PI多个版本（≥3份）|
| PI_PROFORMA_INVOICE | PI_PRICE_HISTORY | 1:N | 一个PI多个价格历史 |
| PI_PROFORMA_INVOICE | PO_PURCHASE_ORDER | 1:N | 一个PI可拆多个采购单 |
| PI_PROFORMA_INVOICE | SH_SHIPMENT | 1:N | 一个PI可分多批发货 |
| PI_PROFORMA_INVOICE | AR_CUSTOMER_PAYMENT | 1:N | 一个PI多次收款 |
| PRD_PRODUCT | PRD_PRODUCT_IMAGE | 1:N | 一个产品多张图片 |
| PRD_PRODUCT | PRD_PRODUCT_CUSTOMER_CODE | 1:N | 一个产品多个客户号 |
| PRD_PRODUCT | PI_PROFORMA_INVOICE_ITEM | 1:N | 一个产品可出现在多个PI明细 |
| PRD_PRODUCT | INV_INVENTORY | 1:N | 一个产品多条库存（按客户分）|
| SUP_SUPPLIER | PO_PURCHASE_ORDER | 1:N | 一个供应商多个采购单 |
| SUP_SUPPLIER | AP_SUPPLIER_PAYMENT | 1:N | 一个供应商多次付款 |
| PO_PURCHASE_ORDER | PO_PURCHASE_ORDER_ITEM | 1:N | 一个采购单多个明细 |
| PO_PURCHASE_ORDER | AP_SUPPLIER_PAYMENT | 1:N | 一个采购单多次付款 |
| SH_SHIPMENT | SH_SHIPMENT_ITEM | 1:N | 一个出货多个明细 |
| SHIPMENT_ITEM | INV_INVENTORY | N:1 | 出货扣减库存（按客户） |
| INV_INVENTORY | INV_INVENTORY_LOG | 1:N | 库存变动记录流水 |

---

## 六、关键业务规则汇总（★新增）

### 6.1 版本管理规则
| 单据类型 | 保留历史版本 |
|---------|------------|
| 报价单 | ≥5份 |
| PI单 | ≥3份 |
| PI明细价格+备注 | ≥3份 |

### 6.2 库存跟客户规则
- **库存必填customer_id**，跟客户走，不囤货
- 货物位置：供应商仓 → 在途 → 客户处
- 不存在公司自有仓库

### 6.3 付款阶段灵活规则
- **定金**：stage_type='deposit'，stage_no=NULL（最多一个）
- **尾款**：stage_type='balance'，stage_no=1,2,3...（次数不固定）
- PI状态根据付款阶段动态计算

### 6.4 新PI自动带出规则
- 选择客户+产品 → 自动填入该客户上一次购买该产品的**单价+备注**
- 数据来源：pi_price_history 表

### 6.5 体积计算规则
- 产品录入：填写纸箱尺寸 + 每箱数量 → 自动计算每箱体积
- 采购时：输入数量 → 自动计算预计箱数和总体积
- 出货时：输入数量 → 自动计算出货箱数和体积

---

## 七、技术建议

### 7.1 数据库选型
- 开发/测试：MySQL 8.0
- 生产：MySQL 8.0 主从复制 或 Percona Aurora

### 7.2 备份策略
- 每日全量备份
- 实时增量备份（Binlog）
- 异地容灾备份

---

*文档版本：v2.0 | 整理日期：2026-04-29 | 变更：同步所有业务规则更新*
