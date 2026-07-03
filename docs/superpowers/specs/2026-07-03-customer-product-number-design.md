# 客户产品编号与系统编号重构设计

## 背景

当前 `PrdCustomerProduct` 在创建时直接生成正式的系统编号，格式为 `{customer_code}{department_code}{category_code}{year}{seq}`。若创建时产品类目尚未确定，系统编号中类目部分会使用占位值，导致编号不准确。

本设计引入「临时系统编号」机制：产品刚创建时分配临时编号，类目锁定后重新生成正式编号。同时规范「客户产品编号」作为系统内指向商品的第二约束，格式为 `{customer_code}{customer_model}`。

## 设计目标

1. 系统编号始终是客户产品的第一约束（主标识）。
2. 客户产品编号 `{customer_code}{customer_model}` 是系统内第二约束。
3. 不论产品信息是否完整，创建时立即分配临时系统编号。
4. 产品类目首次锁定后，临时系统编号替换为正式系统编号，旧临时编号不保留。
5. 客户产品编号在 Dialog 打开时自动生成，提供一次修改机会，确认后锁定。

## 关键决策

- 临时系统编号格式：`TMP-{customer_code}-{6位序号}`。
- 正式系统编号格式：沿用现有 `{customer_code}{department_code}{category_code}{year}{6位序号}`。
- 临时/正式状态不新增数据库字段，通过 `system_code` 是否以 `TMP-` 开头判断。
- 客户产品编号唯一性：同一客户产品内唯一，不跨客户产品强制唯一。
- 缺少 `customer_model` 时，不生成客户产品编号，等待用户补全。

## 数据模型

不新增数据库表或字段，沿用现有模型：

- `PrdCustomerProduct.system_code`：系统编号，临时以 `TMP-` 开头，类目锁定后替换。
- `PrdCustomerProduct.customer_product_code`：保留旧兼容字段，不再作为第一约束。
- `PrdCustomerProductCode.code`：客户产品编号，由 `{customer_code}{customer_model}` 生成。
- 临时编号序列：通过查询 `PrdCustomerProduct.system_code like 'TMP-{customer_code}-%'` 获取最大序号后自增。

## 后端设计

### 新增/修改函数

#### `_generate_temp_system_code(db, customer_code) -> str`

- 查询 `PrdCustomerProduct.system_code like 'TMP-{customer_code}-%'` 获取当前最大序号。
- 返回 `TMP-{customer_code}-{seq:06d}`（seq = max_seq + 1）。
- 若查询不到则 seq = 1。

#### `create_customer_product(db, obj_in)`

- 忽略传入的 `system_code`，强制调用 `_generate_temp_system_code`。
- 保持其他字段逻辑不变。

#### `update_customer_product(db, db_obj, obj_in)`

- 保存前检测：原 `db_obj.category_id` 为空，且 `obj_in.category_id` 非空，且当前 `system_code` 以 `TMP-` 开头。
- 满足条件时调用现有 `_generate_system_code` 生成正式编号，覆盖 `system_code`。
- 其他字段按原逻辑更新。

### 路由与接口

- `POST /api/customer-products`：保持现有接口签名，内部使用临时编号。
- `PUT /api/customer-products/{id}`：保持现有接口签名，内部检测类目变化转换编号。
- 响应中增加 `is_system_code_temp` 派生字段（可选，便于前端展示标签）。

## 前端设计

### 客户产品 Dialog

#### 系统编号区

- 在基础信息区新增「系统编号」只读字段。
- 若 `system_code` 以 `TMP-` 开头，显示橙色/灰色「临时」标签。
- 类目锁定生成正式编号后，显示「正式」标签。

#### 客户产品编号区

- 字段名为「客户产品编号」，默认只读。
- **自动填充**：Dialog 打开时，若 `customer_code` 和 `customer_model` 均非空，且当前无客户产品编号，则自动显示 `{customer_code}{customer_model}`（未锁定）。
- **缺少 Model**：若 `customer_model` 为空，显示「未生成（缺少客户型号）」。
- **修改按钮**：按钮文案改为「修改编号」，仅当编号未最终锁定时可用。锁定状态通过「`codes` 列表中已存在主编号」判断：一旦保存过主编号，再次打开 Dialog 时该字段为只读，「修改编号」按钮禁用。
- **修改流程**：
  1. 点击「修改编号」→ 字段变为可编辑。
  2. 用户修改后点击「确认」。
  3. 弹出确认框：「确认使用此客户产品编号？确认后将不可再次修改」。
  4. 确认后字段恢复只读，按钮禁用。
- **保存确认**：点击 Dialog「保存」时，若客户产品编号有变更或首次生成，弹出确认框「确认保存客户产品编号？」；确认后才写入 `codes` 并调用后端保存。

### 类目锁定

- 沿用现有「大类+子类一次性编辑」逻辑。
- 用户首次设置大类、子类并保存时，后端自动将临时系统编号转换为正式编号。
- Dialog 保存后重新读取 `system_code`，刷新标签显示。

## 数据流

1. 订单导入创建客户产品 → 后端生成 `TMP-{customer_code}-{seq}`。
2. 用户打开客户产品 Dialog：
   - 若 `customer_model` 存在，自动显示 `{customer_code}{customer_model}`（未锁定）。
   - 若 `customer_model` 缺失，显示提示。
3. 用户首次设置大类+子类并保存 → 后端替换为正式系统编号。
4. 用户点击「修改编号」→ 编辑 → 确认 → 客户产品编号锁定。
5. 用户点击 Dialog「保存」→ 再次确认 → 编号写入 `codes` 并同步后端。

## 边界情况与错误处理

| 场景 | 处理 |
|---|---|
| 临时编号序列耗尽 | 使用时间戳兜底，避免阻塞创建。 |
| 正式编号生成失败 | 保持临时编号，返回错误提示管理员。 |
| 客户产品编号重复 | 前端本地校验 + 后端唯一性校验，双重拦截。 |
| 并发创建重复系统编号 | 数据库唯一索引 + 捕获异常后重试一次。 |
| 保存时取消确认 | 编号保持 Dialog 打开前状态，不写入后端。 |
| 客户型号后续补全 | 关闭并重新打开 Dialog 时按新 Model 生成。 |
| 旧数据迁移 | 已存在的非 `TMP-` 系统编号保持原样。 |

## 测试要点

1. 创建无类目的客户产品，验证 `system_code` 以 `TMP-` 开头。
2. 首次设置类目保存，验证 `system_code` 变为正式格式。
3. 打开 Dialog 自动生成 `customer_code + customer_model`。
4. 修改客户产品编号一次，保存后再次打开不可修改。
5. 缺少 `customer_model` 时，编号区显示提示，不生成空编号。
6. 验证 PI 订单项通过 `product_id` 引用，系统编号变更不影响历史订单。
7. 并发创建两个无类目客户产品，验证临时编号不重复。

## 方案对比

| 方案 | 优点 | 缺点 |
|---|---|---|
| A：最小改动（本设计） | 不新增字段，改动集中，与现有按钮/锁定体验一致 | 临时/正式状态通过前缀隐式判断 |
| B：显式状态字段 | 状态明确，便于查询过滤 | 需新增字段和迁移，与「不留痕」略有冗余 |
| C：仅前端触发 | 后端改动小 | 临时编号未落库，刷新后状态丢失 |

本设计采用方案 A。

## 待实现文件

- `backend/crud/customer_product.py`：新增/修改系统编号生成逻辑。
- `backend/routers/customer_product.py`：响应中派生临时状态字段（可选）。
- `client/widgets/customer_product_dialog.py`：系统编号显示、客户产品编号自动生成与修改锁定、保存确认。
