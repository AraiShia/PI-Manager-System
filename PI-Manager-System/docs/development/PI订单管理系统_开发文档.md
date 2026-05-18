# PI订单管理系统 - 开发文档

> 版本：v1.0
> 日期：2026-04-30
> 状态：草稿

---

## 一、项目概述

### 1.1 项目背景
B2B汽车配件外贸企业需要一套完整的订单管理系统，覆盖从产品管理、客户管理、供应商管理、报价、PI下单、采购、出货、收付款到库存的全链路闭环。

### 1.2 系统定位
- **系统名称**：PI订单管理系统
- **系统类型**：B2B外贸企业订单管理系统
- **部署方式**：私有化部署（多租户分部门）
- **目标用户**：业务员、财务、仓库管理员、部门主管

### 1.3 核心功能模块

| 模块 | 功能描述 | 优先级 |
|-----|---------|--------|
| 产品管理 | 产品基础信息、OE号、价格、图片管理 | P0 |
| 客户管理 | 客户档案、收货地址、联系人、特殊要求 | P0 |
| 供应商管理 | 供应商档案、发票类型、供货周期 | P0 |
| PI管理 | 核心单据，贯穿采购、出货、收付款全流程 | P0 |
| 采购管理 | 采购合同、入库操作、1688采购 | P1 |
| 出货管理 | 出货登记、CI发票、PL装箱单 | P1 |
| 收付款管理 | 客户收款、供应商付款、水单管理 | P1 |
| 库存管理 | 实时库存、库存流水、库龄分析 | P1 |
| 报价单管理 | 报价单生成、历史价格参考 | P2 |
| 系统设置 | 部门管理、编号规则、用户权限 | P2 |

---

## 二、技术架构

### 2.1 技术栈

#### 后端
| 层级 | 技术选型 | 说明 |
|-----|---------|------|
| 运行环境 | Node.js 20 LTS | 稳定可靠 |
| 框架 | NestJS | 模块化企业级框架 |
| ORM | Prisma | 类型安全、简洁的数据库操作 |
| 数据库 | MySQL 8.0 | 主从复制方案 |
| 缓存 | Redis 7.x | 会话缓存、数据缓存 |
| 队列 | Bull (Redis) | 异步任务、通知提醒 |
| 文件存储 | MinIO / 阿里云OSS | 文件、图片存储 |

#### 前端
| 层级 | 技术选型 | 说明 |
|-----|---------|------|
| 框架 | Vue 3 + Composition API | 响应式、类型安全 |
| UI库 | Element Plus | 企业级组件库 |
| 状态管理 | Pinia | Vue3专用状态管理 |
| 路由 | Vue Router 4 | 路由管理 |
| HTTP | Axios | API请求 |
| 图表 | ECharts | 数据可视化 |
| 表格 | AG Grid / Element Plus Table | 复杂表格 |

#### DevOps
| 层级 | 技术选型 | 说明 |
|-----|---------|------|
| 容器化 | Docker + Docker Compose | 开发/生产环境一致 |
| CI/CD | GitLab CI / Jenkins | 自动化构建部署 |
| 监控 | Prometheus + Grafana | 系统监控 |
| 日志 | ELK Stack | 日志收集分析 |

### 2.2 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        客户端层                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Web浏览器  │  │  移动端H5   │  │   API调用   │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        网关层 (Nginx)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  静态资源    │  │  API代理    │  │  SSL终结    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        服务层 (K8s/Docker Swarm)                 │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    API服务 (NestJS)                      │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │ 产品模块 │ │ 客户模块 │ │ PI模块  │ │ 采购模块 │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │ 出货模块 │ │ 库存模块 │ │ 报表模块 │ │ 系统模块 │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Web服务    │  │  文件服务   │  │  任务队列   │             │
│  │  (静态资源)  │  │  (MinIO)    │  │  (Bull)     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据层                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   MySQL     │  │   Redis     │  │  MinIO/OSS  │             │
│  │  (主从复制)  │  │  (缓存)     │  │  (文件存储)  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      Controller层 (接口层)                       │
│  - HTTP请求处理                                                  │
│  - 参数校验                                                      │
│  - 权限验证                                                      │
│  - 统一响应格式                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service层 (业务逻辑层)                      │
│  - 业务逻辑处理                                                  │
│  - 事务管理                                                      │
│  - 业务规则校验                                                  │
│  - 事件发布                                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Repository层 (数据访问层)                   │
│  - 数据库操作                                                    │
│  - 缓存读写                                                     │
│  - 复杂查询                                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Source (数据源)                        │
│  - MySQL                                                        │
│  - Redis                                                        │
│  - MinIO/OSS                                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、数据库设计（概要）

### 3.1 多数据库策略
采用**独立数据库**方案，每个部门独立数据库，实现数据完全隔离。

| 部门 | 数据库名 |
|-----|---------|
| 维那(W) | wny_pimain |
| 索英普(S) | syy_pimain |
| 马迪那(M) | mdn_pimain |
| 银达(D) | ydd_pimain |

### 3.2 核心表结构

详见 [PI订单管理系统_数据库设计_v2.md](./PI订单管理系统_数据库设计_v2.md)

### 3.3 编号规则

| 单据类型 | 规则 | 示例 |
|---------|------|------|
| 系统商品编号 | `部门+类别+年份+序号` | SA01260001 |
| PI号 | `部门+客户+年月日+识别号` | SA012612011 |
| 采购单号 | `V + PI号 + 供应商号` | VSA012612011-001 |
| 报价单号 | `Q + PI号` | QSA012612011-1 |

---

## 四、模块设计

### 4.1 产品管理模块

#### 核心功能
- 产品CRUD（Create, Read, Update, Delete）
- OE号/客户号/工厂编号管理
- 包装体积自动计算
- 图片管理（主图+细节图）
- 批量导入导出（Excel）

#### 关键业务逻辑
```
新增产品时：
1. 自动生成系统编号（部门+类别+年份+序号）
2. 验证OE号唯一性
3. 计算每箱体积 = 长×宽×高/1000000
4. 记录操作日志
```

#### API设计

| 方法 | 路径 | 描述 |
|-----|------|------|
| GET | /api/products | 获取产品列表（分页+筛选） |
| GET | /api/products/:id | 获取产品详情 |
| POST | /api/products | 新增产品 |
| PUT | /api/products/:id | 更新产品 |
| DELETE | /api/products/:id | 删除产品 |
| POST | /api/products/:id/images | 上传产品图片 |
| DELETE | /api/products/:id/images/:imageId | 删除图片 |
| POST | /api/products/import | 批量导入 |
| GET | /api/products/export | 导出Excel |

#### 请求/响应示例

```typescript
// POST /api/products
// Request
{
  "deptId": "S",
  "oeNumber": "OE-12345",
  "factoryCode": "FAC-001",
  "brand": "Brand A",
  "detailDesc": "发动机零件，高精度",
  "supplierId": 1,
  "categoryId": 1,
  "exwPriceIncl": 10.50,
  "exwPriceExcl": 9.50,
  "cartonLengthCm": 40,
  "cartonWidthCm": 30,
  "cartonHeightCm": 20,
  "unitsPerCarton": 50,
  "grossWeightKg": 15.5
}

// Response
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "productCode": "SA01260001",
    "oeNumber": "OE-12345",
    "cartonVolumeM3": 0.024,
    ...
  }
}
```

---

### 4.2 客户管理模块

#### 核心功能
- 客户CRUD
- 收货地址管理（多地址）
- 联系人管理
- 特殊要求管理（PI时自动带出）
- 客户禁用/启用

#### API设计

| 方法 | 路径 | 描述 |
|-----|------|------|
| GET | /api/customers | 获取客户列表 |
| GET | /api/customers/:id | 获取客户详情（含地址、联系人） |
| POST | /api/customers | 新增客户 |
| PUT | /api/customers/:id | 更新客户 |
| DELETE | /api/customers/:id | 删除客户 |
| GET | /api/customers/:id/addresses | 获取收货地址列表 |
| POST | /api/customers/:id/addresses | 新增收货地址 |
| PUT | /api/customers/:id/addresses/:addrId | 更新收货地址 |
| DELETE | /api/customers/:id/addresses/:addrId | 删除收货地址 |

---

### 4.3 供应商管理模块

#### 核心功能
- 供应商CRUD
- 供应商产品关联
- 发票类型/税点管理
- 采购统计

#### API设计

| 方法 | 路径 | 描述 |
|-----|------|------|
| GET | /api/suppliers | 获取供应商列表 |
| GET | /api/suppliers/:id | 获取供应商详情 |
| POST | /api/suppliers | 新增供应商 |
| PUT | /api/suppliers/:id | 更新供应商 |
| DELETE | /api/suppliers/:id | 删除供应商 |
| GET | /api/suppliers/:id/products | 获取供应商产品列表 |
| POST | /api/suppliers/:id/products | 关联产品到供应商 |
| GET | /api/suppliers/:id/statistics | 获取采购统计 |

---

### 4.4 PI管理模块（核心）

#### 核心功能
- PI单CRUD
- 付款阶段灵活配置（定金+N期尾款）
- 从报价单转入/直接新建
- 历史版本管理（保留≥3份）
- 自动带出上次购买价格
- 关联采购单、出货、收款

#### 关键业务逻辑

```
新建PI流程：
1. 选择客户 → 自动带出特殊要求
2. 添加产品 → 自动查询历史价格并填入
3. 配置付款阶段 → 可添加任意数量尾款
4. 保存/确认 → 生成PI号 → 触发后续流程

付款状态动态计算：
- 全部未付 → 待确认
- 定金已付 → 已付定金
- 部分尾款已付 → 部分尾款
- 全部付完 → 已完成
```

#### API设计

| 方法 | 路径 | 描述 |
|-----|------|------|
| GET | /api/pi | 获取PI列表（分页+状态筛选） |
| GET | /api/pi/:id | 获取PI详情 |
| GET | /api/pi/:id/versions | 获取PI版本历史 |
| POST | /api/pi | 新建PI |
| PUT | /api/pi/:id | 更新PI |
| POST | /api/pi/:id/confirm | 确认PI |
| POST | /api/pi/:id/clone | 复制PI |
| GET | /api/pi/:id/payments | 获取付款记录 |
| POST | /api/pi/:id/payments | 录入付款记录 |
| GET | /api/pi/price-history | 获取历史价格（按客户+产品） |
| GET | /api/pi/validate | 预览PI编号 |

#### 特殊要求自动带出逻辑

```typescript
// 获取客户特殊要求
async getCustomerSpecialRequirements(customerId: number) {
  const customer = await this.customerRepository.findById(customerId);
  return {
    specialRequire: customer.specialRequire,
    // 可能还包含从历史PI中提取的特殊要求
  };
}

// 新增PI时
const piData = {
  customerId,
  specialRequirements: await this.getCustomerSpecialRequirements(customerId)
};
```

---

### 4.5 采购管理模块

#### 核心功能
- 采购合同CRUD
- 采购单状态管理（已采购→待入库→已完成）
- 体积自动计算
- 1688采购记录
- 入库操作
- 采购跟催提醒

#### API设计

| 方法 | 路径 | 描述 |
|-----|------|------|
| GET | /api/purchase-orders | 获取采购单列表 |
| GET | /api/purchase-orders/:id | 获取采购单详情 |
| POST | /api/purchase-orders | 新建采购单 |
| PUT | /api/purchase-orders/:id | 更新采购单 |
| POST | /api/purchase-orders/:id/confirm | 确认采购 |
| POST | /api/purchase-orders/:id/inbound | 入库登记 |
| GET | /api/purchase-orders/:id/inbound-records | 获取入库记录 |
| POST | /api/1688-purchases | 1688采购记录 |
| GET | /api/purchase-orders/statistics | 采购统计 |

#### 体积自动计算

```typescript
// 输入：数量 + 产品包装信息
// 输出：预计箱数 + 预计体积

function calculateVolume(quantity: number, unitsPerCarton: number, cartonVolumeM3: number) {
  const cartons = Math.ceil(quantity / unitsPerCarton);
  const totalVolume = cartons * cartonVolumeM3;
  return { cartons, totalVolume };
}
```

---

### 4.6 出货管理模块

#### 核心功能
- 出货登记（关联PI+库存校验）
- 库存批次选择（该PI下可用库存）
- 体积自动计算
- CI/PL文档生成
- 出货状态跟踪

#### API设计

| 方法 | 路径 | 描述 |
|-----|------|------|
| GET | /api/shipments | 获取出货列表 |
| GET | /api/shipments/:id | 获取出货详情 |
| POST | /api/shipments | 新建出货单 |
| PUT | /api/shipments/:id | 更新出货单 |
| POST | /api/shipments/:id/confirm | 确认出货（扣减库存） |
| GET | /api/shipments/:id/ci | 生成CI文档 |
| GET | /api/shipments/:id/pl | 生成PL文档 |
| GET | /api/shipments/inventory | 获取可出货库存（按PI筛选） |
| GET | /api/shipments/statistics | 出货统计 |

#### 库存扣减逻辑

```typescript
async confirmShipment(shipmentId: number) {
  const shipment = await this.shipmentRepository.findById(shipmentId);
  
  // 按批次扣减库存
  for (const item of shipment.items) {
    const inventory = await this.inventoryRepository.findByBatch(item.inventoryId);
    
    // 校验可出数量
    if (item.quantity > inventory.pendingQuantity) {
      throw new Error(`产品${item.productId}可出数量不足`);
    }
    
    // 更新库存
    inventory.pendingQuantity -= item.quantity;
    inventory.shippedQuantity += item.quantity;
    inventory.currentLocation = 'IN_TRANSIT'; // 在途
    
    await this.inventoryRepository.save(inventory);
    
    // 记录库存流水
    await this.inventoryLogRepository.create({
      productId: item.productId,
      customerId: inventory.customerId,
      piId: shipment.piId,
      changeType: 'SHIP',
      changeQuantity: -item.quantity,
      refType: 'SH',
      refId: shipmentId
    });
  }
  
  // 更新出货单状态
  shipment.status = 'SHIPPED';
  await this.shipmentRepository.save(shipment);
}
```
网站内容同步，规划性，
和社媒同步，养号

---

### 4.7 收付款管理模块

#### 核心功能
- 客户收款录入（水单上传）
- 供应商付款录入
- PI自动匹配
- 付款状态更新
- 逾期提醒

#### API设计

| 方法 | 路径 | 描述 |
|-----|------|------|
| GET | /api/receivables | 获取收款列表 |
| GET | /api/receivables/:id | 获取收款详情 |
| POST | /api/receivables | 录入收款 |
| POST | /api/receivables/:id/upload | 上传水单 |
| GET | /api/payables | 获取付款列表 |
| GET | /api/payables/:id | 获取付款详情 |
| POST | /api/payables | 录入付款 |
| GET | /api/payments/unmatched | 获取未匹配付款 |

---

### 4.8 库存管理模块

#### 核心功能
- 实时库存看板
- 库存明细（跟客户走）
- 库存流水账
- 库龄分析
- 库存预警
- 库存调拨

#### API设计

| 方法 | 路径 | 描述 |
|-----|------|------|
| GET | /api/inventory/dashboard | 库存看板数据 |
| GET | /api/inventory | 获取库存列表 |
| GET | /api/inventory/:id | 获取库存详情 |
| GET | /api/inventory/logs | 库存流水 |
| GET | /api/inventory/aging | 库龄分析 |
| GET | /api/inventory/warnings | 库存预警 |
| POST | /api/inventory/transfer | 库存调拨 |

---

## 五、业务流程

### 5.1 PI完整生命周期

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   1. 报价阶段                                                    │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐                  │
│   │ 客户询价  │────►│ 历史价格 │────►│ 报价单   │                  │
│   │          │     │ 自动带出  │     │          │                  │
│   └─────────┘     └─────────┘     └────┬────┘                  │
│                                        │                        │
│                                        ▼                        │
│   2. PI阶段                             │                        │
│   ┌─────────────────────────────────────────────────────┐       │
│   │  选择客户 ──► 自动带出特殊要求                          │       │
│   │      │                                                │       │
│   │      ▼                                                │       │
│   │  添加产品 ──► 历史价格+备注自动填入                      │       │
│   │      │                                                │       │
│   │      ▼                                                │       │
│   │  配置付款阶段（定金+N期尾款）                           │       │
│   │      │                                                │       │
│   │      ▼                                                │       │
│   │  确认PI ──► 生成PI号 ──► 通知采购                      │       │
│   └─────────────────────────────────────────────────────┘       │
│                                        │                        │
│                                        ▼                        │
│   3. 采购阶段                            │                        │
│   ┌─────────────────────────────────────────────────────┐       │
│   │  创建采购单（关联PI）                                 │       │
│   │      │                                                │       │
│   │      ▼                                                │       │
│   │  确认采购 ──► 采购单状态=已采购                         │       │
│   │      │                                                │       │
│   │      ▼                                                │       │
│   │  入库验收 ──► 采购单状态=已完成 ──► 库存增加             │       │
│   └─────────────────────────────────────────────────────┘       │
│                                        │                        │
│                                        ▼                        │
│   4. 出货阶段                            │                        │
│   ┌─────────────────────────────────────────────────────┐       │
│   │  出货登记（关联PI+校验库存）                           │       │
│   │      │                                                │       │
│   │      ▼                                                │       │
│   │  确认出货 ──► 库存扣减 ──► 生成CI/PL                   │       │
│   └─────────────────────────────────────────────────────┘       │
│                                        │                        │
│                                        ▼                        │
│   5. 收付款阶段                          │                        │
│   ┌─────────────────────────────────────────────────────┐       │
│   │  定金/尾款录入 ──► PI状态更新                          │       │
│   │      │                                                │       │
│   │      ▼                                                │       │
│   │  全部付完 ──► PI状态=已完成                            │       │
│   └─────────────────────────────────────────────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 库存流转

```
供应商 ──► 采购入库 ──► 供应商仓 ──► 出货 ──► 在途 ──► 客户处
                │                                             
                │ 库存记录（change_type）                     
                ▼                                             
         INV_INVENTORY_LOG                              
         1:采购入库 / 2:出货 / 3:在途变更 / 4:到达签收
```

---

## 六、编号生成规则

### 6.1 编号生成服务

```typescript
// 编号生成服务
@Injectable()
export class NumberGeneratorService {
  
  async generateProductCode(deptId: string, categoryId: number): Promise<string> {
    const deptCode = this.getDeptCode(deptId);
    const categoryCode = this.getCategoryCode(categoryId);
    const year = new Date().getFullYear().toString().slice(-2);
    const sequence = await this.getNextSequence('PRODUCT');
    
    return `${deptCode}${categoryCode}${year}${String(sequence).padStart(4, '0')}`;
  }
  
  async generatePINo(deptId: string, customerCode: string): Promise<string> {
    const deptCode = this.getDeptCode(deptId);
    const date = new Date();
    const dateStr = `${date.getFullYear().toString().slice(-2)}${String(date.getMonth()+1).padStart(2,'0')}${String(date.getDate()).padStart(2,'0')}`;
    
    // 查找当天该客户已生成的PI数量+1作为识别号
    const existingCount = await this.countTodayPI(deptId, customerCode);
    const identifier = existingCount + 1;
    
    return `${deptCode}${customerCode}${dateStr}${identifier}`;
  }
  
  async generatePONo(piNo: string, supplierCode: string): Promise<string> {
    const supplierNo = supplierCode.padStart(3, '0');
    const existingCount = await this.countPOByPI(piNo);
    const sequence = existingCount + 1;
    
    return `V${piNo}-${supplierNo}${String(sequence).padStart(2, '0')}`;
  }
  
  async generateQuoteNo(piNo: string): Promise<string> {
    const existingCount = await this.countQuoteByPI(piNo);
    const sequence = existingCount + 1;
    
    return `Q${piNo}-${sequence}`;
  }
}
```

### 6.2 序号重置规则

- **重置频率**：按年重置（每年1月1日）
- **重置方式**：自动重置，也可手动重置
- **历史追溯**：编号历史记录表保留所有已生成编号

---

## 七、权限设计

### 7.1 角色定义

| 角色 | 权限描述 |
|-----|---------|
| 管理员 | 全部权限 |
| 部门主管 | 本部门全部权限 |
| 业务员 | 产品、客户、PI、报价、出货 |
| 财务 | 收款、付款、报表 |
| 仓库 | 采购、入库、库存 |

### 7.2 数据隔离策略

```typescript
// 部门数据隔离中间件
@Injectable()
export class DeptIsolationInterceptor implements NestInterceptor {
  async intercept(context: ExecutionContext, next: CallHandler) {
    const request = context.switchToHttp().getRequest();
    const user = request.user;
    
    // 所有查询自动加上部门过滤
    if (user && user.deptId) {
      request.query.deptId = user.deptId;
      if (request.body) {
        request.body.deptId = user.deptId;
      }
    }
    
    return next.handle();
  }
}
```

---

## 八、通知系统

### 8.1 通知类型

| 类型 | 触发场景 | 通知方式 |
|-----|---------|---------|
| PI确认 | 新建PI确认 | 系统通知+邮件 |
| 付款到期 | 付款阶段到期前3天 | 系统通知 |
| 采购跟催 | 采购单逾期未入库 | 系统通知 |
| 库存预警 | 库存低于安全线 | 系统通知 |
| 逾期提醒 | 客户逾期未付款 | 系统通知+邮件 |

### 8.2 通知队列

```typescript
// 使用Bull队列处理通知
export const notificationQueue = new Queue('notification');

notificationQueue.add('pi_confirmed', {
  piId: 1,
  piNo: 'SA012612011',
  customerName: 'A客户',
  notifyUsers: ['user1', 'user2']
}, {
  delay: 0, // 立即发送
  attempts: 3,
  backoff: { type: 'exponential', delay: 5000 }
});
```

---

## 九、部署方案

### 9.1 Docker Compose 配置

```yaml
version: '3.8'

services:
  api:
    build:
      context: ./server
  dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DB_HOST=mysql
      - REDIS_HOST=redis
    depends_on:
      - mysql
      - redis
    restart: unless-stopped

  web:
    build:
      context: ./web
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - api
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=xxx
      - MYSQL_DATABASE=pimain
    volumes:
      - mysql_data:/var/lib/mysql
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  minio:
    image: minio/minio
    environment:
      - MINIO_ROOT_USER=xxx
      - MINIO_ROOT_PASSWORD=xxx
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    restart: unless-stopped

volumes:
  mysql_data:
  redis_data:
  minio_data:
```

### 9.2 环境变量配置

```bash
# Server
NODE_ENV=production
PORT=3000

# Database
DB_HOST=mysql
DB_PORT=3306
DB_USERNAME=root
DB_PASSWORD=xxx
DB_NAME=pimain

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# MinIO
MINIO_ENDPOINT=minio
MINIO_PORT=9000
MINIO_ACCESS_KEY=xxx
MINIO_SECRET_KEY=xxx
MINIO_BUCKET=pi-files

# JWT
JWT_SECRET=xxx
JWT_EXPIRES_IN=7d

# 通知
SMTP_HOST=smtp.xxx.com
SMTP_PORT=465
SMTP_USER=xxx
SMTP_PASSWORD=xxx
```

### 9.3 健康检查

```bash
# API健康检查
curl -f http://localhost:3000/health

# 数据库连接检查
curl -f http://localhost:3000/health/db

# Redis连接检查
curl -f http://localhost:3000/health/redis
```

---

## 十、监控与日志

### 10.1 日志规范

```typescript
// 统一日志格式
{
  "timestamp": "2026-04-30T09:28:00.000Z",
  "level": "info",
  "service": "pi-api",
  "traceId": "abc123",
  "userId": 1,
  "deptId": "S",
  "action": "PI_CREATED",
  "data": {
    "piId": 1,
    "piNo": "SA012612011"
  },
  "duration": 150
}
```

### 10.2 监控指标

| 指标 | 描述 | 告警阈值 |
|-----|------|---------|
| API响应时间 | P99 < 500ms | > 1s |
| API错误率 | < 0.1% | > 1% |
| 数据库连接池 | 正常使用 | > 80% |
| CPU使用率 | < 70% | > 90% |
| 内存使用率 | < 80% | > 90% |
| 磁盘使用率 | < 70% | > 85% |

---

## 十一、开发规范

### 11.1 Git分支管理

```
main (生产环境)
  │
  ├── develop (开发主分支)
  │     │
  │     ├── feature/xxx (功能分支)
  │     ├── bugfix/xxx (修复分支)
  │     └── release/xxx (发布分支)
```

### 11.2 代码审查清单

- [ ] 代码符合ESLint规范
- [ ] 单元测试覆盖率 > 80%
- [ ] API有Swagger文档
- [ ] 敏感信息不硬编码
- [ ] 业务逻辑有注释
- [ ] 错误处理完善
- [ ] 日志记录完整

### 11.3 提交信息规范

```
<type>(<scope>): <subject>

Types:
- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- style: 代码格式
- refactor: 重构
- test: 测试
- chore: 构建/工具

Examples:
- feat(pi): 新增PI管理模块
- fix(inventory): 修复库存计算bug
- docs(api): 更新API文档
```

---

## 十二、文档清单

| 文档 | 位置 | 说明 |
|-----|------|------|
| 需求文档 | PI订单管理系统_功能拆解.md | 功能需求 |
| 原型设计 | PI订单管理系统_原型设计.md | UI/UX设计 |
| 数据库设计 | PI订单管理系统_数据库设计_v2.md | 表结构设计 |
| 开发文档 | PI订单管理系统_开发文档.md | 本文档 |
| 测试用例 | PI订单管理系统_测试用例.md | 测试用例 |
| API文档 | /api-docs | Swagger在线文档 |

---

*文档版本：v1.0 | 编写日期：2026-04-30*