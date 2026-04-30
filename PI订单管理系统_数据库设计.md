# PI订单管理系统 - 数据库结构设计

> 版本：v1.0
> 日期：2026-04-29

---

## 一、数据库设计策略

### 1.1 方案选择：独立数据库（推荐）

| 方案 | 优点 | 缺点 | 适用场景 |
|-----|------|------|---------|
| **独立数据库（推荐）** | 数据完全隔离、便于独立备份和恢复、故障不影响其他部门 | 服务器资源占用较高 | 部门数据量大、独立性要求高 |
| 共享数据库+部门字段隔离 | 资源利用率高 | 数据隔离性弱、备份恢复复杂 | 部门数据量小、关联查询多 |

**推荐采用独立数据库方案**，每个部门一个独立的数据库实例或schema。

### 1.2 数据库命名规范

```
部门前缀_业务模块

wny_pimain      -- 维那：PI订单主库
syy_pimain      -- 索英普：PI订单主库
mdn_pimain      -- 马迪那：PI订单主库
ydd_pimain      -- 银达：PI订单主库
```

### 1.3 公共基础数据（可选：共享库）

如需跨部门共享数据（如产品类别、地区编码等），可额外建立公共数据库：

```
pimain_public   -- 公共基础数据（产品类别、地区编码、币种等）
```

---

## 二、核心表结构

### 2.1 部门表（可选公共表）

```sql
-- 部门信息表
CREATE TABLE sys_department (
    dept_id       VARCHAR(10) PRIMARY KEY,  -- 部门编号：W/S/M/D
    dept_name     VARCHAR(50) NOT NULL,     -- 部门名称：维那/索英普/马迪那/银达
    db_name       VARCHAR(50) NOT NULL,     -- 对应数据库名
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    status        TINYINT DEFAULT 1         -- 1:正常 0:停用
);
```

### 2.2 产品表（核心基础表）

```sql
-- 产品主表
CREATE TABLE prd_product (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id             VARCHAR(10) NOT NULL,                    -- 部门编号
    product_code        VARCHAR(50) NOT NULL UNIQUE,             -- 系统编号，如 SA01260001
    oe_number           VARCHAR(100) NOT NULL,                   -- OE号
    factory_code        VARCHAR(100),                            -- 工厂编号
    brand               VARCHAR(100),                            -- 品牌
    detail_desc         VARCHAR(500) NOT NULL,                   -- 细节描述
    supplier_id         BIGINT,                                  -- 关联供应商
    exw_price_incl      DECIMAL(15,4),                          -- EXW含税价
    exw_price_excl      DECIMAL(15,4),                          -- EXW不含税价
    fob_price_incl      DECIMAL(15,4),                          -- FOB含税价
    fob_price_excl      DECIMAL(15,4),                          -- FOB不含税价
    freight             DECIMAL(15,4),                            -- 运费
    packing_fee         DECIMAL(15,4),                           -- 包装费
    purchase_channel    VARCHAR(100),                            -- 采购渠道
    length_cm           DECIMAL(10,2),                           -- 长度(cm)
    width_cm            DECIMAL(10,2),                           -- 宽度(cm)
    height_cm           DECIMAL(10,2),                           -- 高度(cm)
    weight_kg           DECIMAL(10,4),                           -- 重量(kg)
    category_id         INT,                                     -- 产品类别ID
    status              TINYINT DEFAULT 1,                       -- 1:启用 0:禁用
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_oe (oe_number),
    INDEX idx_dept (dept_id),
    INDEX idx_category (category_id)
);

-- 产品图片表
CREATE TABLE prd_product_image (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id      BIGINT NOT NULL,
    image_url       VARCHAR(500) NOT NULL,                      -- 图片URL
    image_type      TINYINT DEFAULT 1,                          -- 1:主图 2:细节图
    sort_order      INT DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 产品-客户号关联表（一个OE号可对应多个工厂的不同客户号）
CREATE TABLE prd_product_customer_code (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id      BIGINT NOT NULL,
    supplier_id     BIGINT,                                      -- 供应商ID（可空）
    customer_code   VARCHAR(100) NOT NULL,                       -- 工厂给客户分配的编号
    remark          VARCHAR(200),                                -- 备注
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 2.3 客户表

```sql
-- 客户主表
CREATE TABLE crm_customer (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    customer_code   VARCHAR(20) NOT NULL UNIQUE,                -- 客户编号，如 A01
    customer_name   VARCHAR(200) NOT NULL,                      -- 客户名称
    country         VARCHAR(100),                                -- 所在国家
    basic_require   TEXT,                                        -- 基本要求
    special_require TEXT,                                        -- 特殊要求（PI时自动带出）
    payment_terms   VARCHAR(100),                                -- 付款条款
    status          TINYINT DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_dept (dept_id),
    INDEX idx_country (country)
);

-- 客户收货地址表
CREATE TABLE crm_customer_address (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id     BIGINT NOT NULL,
    country         VARCHAR(100),                                -- 收货国家
    port            VARCHAR(200),                                -- 港口
    address_detail  VARCHAR(500),                                -- 详细地址
    is_default      TINYINT DEFAULT 0,                          -- 是否默认
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
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
-- 供应商主表
CREATE TABLE sup_supplier (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    supplier_code   VARCHAR(50) NOT NULL UNIQUE,                -- 供应商编号，如 11001
    supplier_name   VARCHAR(200) NOT NULL,
    region          VARCHAR(100),                                -- 地区
    source_location VARCHAR(200),                                -- 境内货源地
    invoice_type    TINYINT,                                     -- 1:增票 2:普票 3:不开发票
    tax_rate        DECIMAL(5,2),                                -- 税点
    supply_cycle_days INT,                                       -- 供货周期(天)
    return_policy   TEXT,                                        -- 退换货备注
    payment_terms   VARCHAR(100),                                -- 付款条款
    status          TINYINT DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_dept (dept_id),
    INDEX idx_region (region)
);

-- 供应商联系人表
CREATE TABLE sup_supplier_contact (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    supplier_id     BIGINT NOT NULL,
    name            VARCHAR(100),
    phone           VARCHAR(50),
    is_primary      TINYINT DEFAULT 0
);
```

### 2.5 报价单表

```sql
-- 报价单主表
CREATE TABLE quo_quote (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    quote_no        VARCHAR(50) NOT NULL UNIQUE,                -- 报价单号，如 QSA012612011-1
    customer_id     BIGINT NOT NULL,                             -- 关联客户
    total_amount    DECIMAL(15,4),                              -- 总金额
    currency        VARCHAR(10) DEFAULT 'USD',
    valid_until     DATE,                                        -- 有效期
    payment_terms   VARCHAR(100),
    remark          TEXT,
    status          TINYINT DEFAULT 1,                          -- 1:草稿 2:已发送 3:已确认 4:已过期
    created_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_dept (dept_id),
    INDEX idx_customer (customer_id),
    INDEX idx_status (status)
);

-- 报价单明细表
CREATE TABLE quo_quote_item (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    quote_id        BIGINT NOT NULL,
    product_id      BIGINT NOT NULL,                             -- 关联产品
    oe_number       VARCHAR(100),                               -- OE号
    customer_code   VARCHAR(100),                               -- 客户号
    quantity        DECIMAL(15,4) NOT NULL,
    unit_price      DECIMAL(15,4) NOT NULL,
    total_price     DECIMAL(15,4) NOT NULL,
    remark          VARCHAR(500)
);
```

### 2.6 PI单表（核心单据）

```sql
-- PI单主表
CREATE TABLE pi_proforma_invoice (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    pi_no           VARCHAR(50) NOT NULL UNIQUE,                 -- PI号，如 SA012612011
    customer_id     BIGINT NOT NULL,
    total_amount    DECIMAL(15,4),
    currency        VARCHAR(10) DEFAULT 'USD',
    deposit_amount  DECIMAL(15,4),                               -- 定金金额
    deposit_date    DATE,                                        -- 定金付款日期
    balance1_amount DECIMAL(15,4),                              -- 尾款1金额
    balance1_date   DATE,                                        -- 尾款1日期
    balance2_amount DECIMAL(15,4),                              -- 尾款2金额
    balance2_date   DATE,                                        -- 尾款2日期
    status          TINYINT DEFAULT 1,                           -- 1:待确认 2:已付定金 3:生产中 4:已出货 5:已完成
    created_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_dept (dept_id),
    INDEX idx_customer (customer_id),
    INDEX idx_status (status),
    INDEX idx_pi_no (pi_no)
);

-- PI单明细表
CREATE TABLE pi_proforma_invoice_item (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    pi_id               BIGINT NOT NULL,
    product_id          BIGINT NOT NULL,
    oe_number           VARCHAR(100),                            -- OE号
    customer_code       VARCHAR(100),                            -- 客户号（差异化：可在此调整）
    detail_desc         VARCHAR(500),                            -- 差异化描述（可调整）
    quantity            DECIMAL(15,4) NOT NULL,
    unit_price          DECIMAL(15,4) NOT NULL,                  -- 差异化单价（可调整）
    total_price         DECIMAL(15,4) NOT NULL,
    remark              TEXT
);

-- PI单版本历史表（保留至少3份）
CREATE TABLE pi_proforma_invoice_version (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    pi_id           BIGINT NOT NULL,
    version_no      INT NOT NULL,                                -- 版本号
    snapshot_data   JSON NOT NULL,                               -- 完整快照
    change_desc     VARCHAR(500),                                -- 变更说明
    created_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_pi (pi_id),
    INDEX idx_created (created_at)
);
```

### 2.7 采购单表

```sql
-- 采购合同主表
CREATE TABLE po_purchase_order (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    po_no           VARCHAR(50) NOT NULL UNIQUE,                 -- 采购单号，如 VSA012612011-001
    pi_id           BIGINT NOT NULL,                              -- 关联PI
    supplier_id     BIGINT NOT NULL,
    total_amount    DECIMAL(15,4),
    contract_date   DATE,
    status          TINYINT DEFAULT 1,                           -- 1:已采购(黄) 2:未入库验收(蓝) 3:已确认入库(黑)
    created_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_dept (dept_id),
    INDEX idx_pi (pi_id),
    INDEX idx_supplier (supplier_id),
    INDEX idx_status (status)
);

-- 采购合同明细表
CREATE TABLE po_purchase_order_item (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    po_id           BIGINT NOT NULL,
    pi_item_id      BIGINT,                                      -- 关联PI明细
    product_id      BIGINT NOT NULL,
    color_detail    VARCHAR(500),                                -- 颜色/细节
    quantity        DECIMAL(15,4) NOT NULL,
    unit_price      DECIMAL(15,4) NOT NULL,
    total_price     DECIMAL(15,4) NOT NULL
);

-- 1688采购记录表
CREATE TABLE po_1688_purchase (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    po_id           BIGINT,                                      -- 关联采购单
    pi_id           BIGINT,                                      -- 关联PI
    product_id      BIGINT,
    product_url     VARCHAR(500),                                 -- 1688链接
    freight         DECIMAL(15,4),                               -- 运费
    payment_method  VARCHAR(100),                                -- 支付方式
    gross_weight    DECIMAL(10,4),                               -- 毛重
    status          TINYINT DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 2.8 入库表

```sql
-- 入库主表
CREATE TABLE wh_stock_in (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    stock_in_no     VARCHAR(50) NOT NULL UNIQUE,                 -- 入库批次号
    po_id           BIGINT NOT NULL,                             -- 关联采购单
    check_status    TINYINT DEFAULT 1,                           -- 1:待验 2:合格 3:不合格
    check_remark    VARCHAR(500),
    check_date      DATETIME,
    created_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 入库明细表
CREATE TABLE wh_stock_in_item (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_in_id     BIGINT NOT NULL,
    product_id      BIGINT NOT NULL,
    quantity        DECIMAL(15,4) NOT NULL,                      -- 实际入库数量
    location        VARCHAR(100),                                -- 存放位置
    remark          VARCHAR(500)
);
```

### 2.9 出货表

```sql
-- 出货登记主表
CREATE TABLE sh_shipment (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    shipment_no     VARCHAR(50) NOT NULL UNIQUE,
    pi_id           BIGINT NOT NULL,
    shipment_date   DATE,
    ci_document     VARCHAR(500),                                -- CI文档路径
    pl_document     VARCHAR(500),                                -- PL文档路径
    payment_status  TINYINT DEFAULT 1,                          -- 1:未付 2:已付 3:部分付
    status          TINYINT DEFAULT 1,
    created_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 出货明细表
CREATE TABLE sh_shipment_item (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    shipment_id     BIGINT NOT NULL,
    product_id      BIGINT NOT NULL,
    quantity        DECIMAL(15,4) NOT NULL,
    location        VARCHAR(100),                                -- 存放位置
    remark          VARCHAR(500)
);
```

### 2.10 收付款表

```sql
-- 客户收款记录表
CREATE TABLE ar_customer_payment (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    receipt_no      VARCHAR(50) NOT NULL UNIQUE,                 -- 收款单号
    pi_id           BIGINT NOT NULL,
    customer_id     BIGINT NOT NULL,
    amount          DECIMAL(15,4) NOT NULL,                     -- 实收金额
    handling_fee    DECIMAL(15,4),                              -- 手续费
    payment_date    DATE NOT NULL,
    remittance_bank VARCHAR(200),                                -- 收汇银行
    currency        VARCHAR(10),                                 -- 收汇币种
    water_image     VARCHAR(500),                                -- 水单图片路径
    created_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 供应商付款记录表
CREATE TABLE ap_supplier_payment (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    payment_no      VARCHAR(50) NOT NULL UNIQUE,                 -- 付款单号
    po_id           BIGINT NOT NULL,
    supplier_id     BIGINT NOT NULL,
    deposit_amount  DECIMAL(15,4),                               -- 定金
    deposit_date    DATE,
    balance_amount  DECIMAL(15,4),                              -- 尾款
    balance_date    DATE,
    total_amount    DECIMAL(15,4),                              -- 应付总额
    paid_amount     DECIMAL(15,4),                              -- 已付金额
    unpaid_amount   DECIMAL(15,4),                              -- 未付金额
    status          TINYINT DEFAULT 1,                          -- 1:未付 2:部分付 3:已付清
    payment_proof   VARCHAR(500),                                -- 付款凭证
    created_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 2.11 库存表

```sql
-- 实时库存表
CREATE TABLE inv_inventory (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    product_id      BIGINT NOT NULL,
    customer_id     BIGINT,                                      -- 所属客户（可空）
    pi_id           BIGINT,                                      -- 对应PI
    po_id           BIGINT,                                      -- 对应采购单
    supplier_id     BIGINT,                                      -- 供应商
    purchase_price  DECIMAL(15,4),                               -- 采购单价
    quantity        DECIMAL(15,4) NOT NULL,                      -- 当前库存
    location        VARCHAR(100),                                -- 存放位置
    stock_in_date   DATE,                                        -- 入库日期
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_dept (dept_id),
    INDEX idx_product (product_id),
    INDEX idx_customer (customer_id),
    INDEX idx_location (location)
);

-- 库存流水账（进、出全程追溯）
CREATE TABLE inv_inventory_log (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10) NOT NULL,
    product_id      BIGINT NOT NULL,
    change_type     TINYINT NOT NULL,                            -- 1:采购入库 2:出货减 3:调拨 4:盘点调整
    change_quantity DECIMAL(15,4) NOT NULL,                      -- 变化数量（正负）
    before_quantity DECIMAL(15,4) NOT NULL,                      -- 变化前数量
    after_quantity  DECIMAL(15,4) NOT NULL,                     -- 变化后数量
    ref_type        VARCHAR(50),                                 -- 关联单据类型：PO/SH/...
    ref_id          BIGINT,                                      -- 关联单据ID
    remark          VARCHAR(500),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_dept (dept_id),
    INDEX idx_product (product_id),
    INDEX idx_created (created_at)
);
```

### 2.12 编号规则表

```sql
-- 编号规则配置表
CREATE TABLE sys_number_rule (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    rule_type       VARCHAR(50) NOT NULL UNIQUE,               -- 规则类型：PRODUCT/PI/PO/QUOTE
    rule_pattern    VARCHAR(200) NOT NULL,                     -- 规则表达式
    current_value   BIGINT DEFAULT 0,                           -- 当前序号值
    reset_frequency VARCHAR(20) DEFAULT 'YEAR',                -- 重置频率：YEAR/MONTH/NONE
    last_reset_date DATE,                                      -- 上次重置日期
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 编号历史记录（可追溯）
CREATE TABLE sys_number_history (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    rule_type       VARCHAR(50) NOT NULL,
    generated_no    VARCHAR(100) NOT NULL,
    related_id      BIGINT,                                     -- 关联单据ID
    related_type    VARCHAR(50),                                 -- 关联单据类型
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 2.13 操作日志表

```sql
-- 操作日志表
CREATE TABLE sys_operation_log (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    dept_id         VARCHAR(10),
    table_name      VARCHAR(100) NOT NULL,
    record_id       BIGINT NOT NULL,
    operation_type  VARCHAR(20) NOT NULL,                       -- INSERT/UPDATE/DELETE
    old_data        JSON,                                       -- 修改前的数据
    new_data        JSON,                                       -- 修改后的数据
    operator_id     BIGINT,
    operator_ip     VARCHAR(50),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_dept (dept_id),
    INDEX idx_table (table_name),
    INDEX idx_record (record_id),
    INDEX idx_created (created_at)
);
```

---

## 三、公共基础表（跨部门共享）

```sql
-- 产品类别表
CREATE TABLE pub_category (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    category_code   VARCHAR(20) NOT NULL UNIQUE,               -- 类别编号：C01/F01/B01
    category_name   VARCHAR(100) NOT NULL,                     -- 类别名称：发动机/椅子类
    parent_id       BIGINT,                                    -- 上级类别
    sort_order      INT DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 地区编码表（省市县）
CREATE TABLE pub_region (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    region_code     VARCHAR(20) NOT NULL UNIQUE,               -- 地区编码：1101
    region_name     VARCHAR(100) NOT NULL,                     -- 地区名称
    parent_code     VARCHAR(20),                                -- 上级编码
    level           TINYINT DEFAULT 1,                         -- 1:省 2:市 3:县
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 币种表
CREATE TABLE pub_currency (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    currency_code   VARCHAR(10) NOT NULL UNIQUE,               -- 币种代码：USD/EUR
    currency_name   VARCHAR(50),                                -- 币种名称
    exchange_rate   DECIMAL(15,4),                              -- 汇率（基准USD）
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

---

## 四、ER关系图（核心实体）

```
客户 (CRM_CUSTOMER)
    │
    │ 1:N（一个客户可有多个收货地址）
    ▼
收货地址 (CRM_CUSTOMER_ADDRESS)
    │
    │ 1:N
    ▼
PI单 (PI_PROFORMA_INVOICE) ←─────────────┐
    │                                    │
    │ N:1                                │ 关联历史价格
    ▼                                    │
产品 (PRD_PRODUCT) ◄─────────────── 报价单 (QUO_QUOTE)
    │                                        │
    │ 1:N（产品-客户号关联）                  │
    ▼                                        │
客户号 (PRD_PRODUCT_CUSTOMER_CODE)           │
    │                                        │
    │ N:1                                    │
    ▼                                        │
供应商 (SUP_SUPPLIER)                        │
    │                                        │
    │ 1:N                                    │
    ▼                                        ▼
采购单 (PO_PURCHASE_ORDER) ──► 入库 (WH_STOCK_IN)
    │                            │
    │                            │ 1:N
    │                            ▼
    │                       库存 (INV_INVENTORY)
    │                            │
    │ 1:N                        │
    ▼                            │
出货 (SH_SHIPMENT)               │
    │                            │
    └──────────┬────────────────┘
               │ 扣减库存
               ▼
        库存流水 (INV_INVENTORY_LOG)

收款 (AR_CUSTOMER_PAYMENT) ──► PI单（更新状态）
付款 (AP_SUPPLIER_PAYMENT) ──► 采购单（更新状态）
```

---

## 五、索引设计汇总

| 表名 | 索引字段 | 用途 |
|-----|---------|------|
| prd_product | dept_id, oe_number, category_id | 按部门/OE号/类别查询 |
| crm_customer | dept_id, country | 按部门/国家查询 |
| sup_supplier | dept_id, region | 按部门/地区查询 |
| pi_proforma_invoice | dept_id, customer_id, status, pi_no | 按部门/客户/状态查询 |
| po_purchase_order | dept_id, pi_id, supplier_id, status | 按部门/PI/供应商/状态查询 |
| inv_inventory | dept_id, product_id, customer_id, location | 按部门/产品/客户/仓库查询 |
| inv_inventory_log | dept_id, product_id, created_at | 按部门/产品/时间查询库存流水 |

---

## 六、技术建议

### 6.1 数据库选型
- **开发/测试环境**：MySQL 8.0
- **生产环境**：MySQL 8.0 主从复制 / Percona Aurora

### 6.2 连接池配置
- 每个部门独立连接池，避免相互影响
- 建议使用 HikariCP，最大连接数根据部门规模设置

### 6.3 备份策略
- 每日全量备份
- 实时增量备份（Binlog）
- 异地容灾备份

### 6.4 迁移注意事项
- 定期归档历史数据（超过2年的已完成PI可归档）
- 索引优化（避免全表扫描）

---

*文档版本：v1.0 | 整理日期：2026-04-29*
