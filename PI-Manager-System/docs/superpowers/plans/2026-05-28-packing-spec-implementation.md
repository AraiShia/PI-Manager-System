# 包装规格关联表实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将订单总表6列包装规格数据（列29-34/37）从"产品-供应商方案"改为跟随"客户-产品-订单"模式，并实现智能回填和智能Tab定位功能。

**架构：** 新建 `po_purchase_order_item_package` 关联表存储包装规格，通过 API 暴露 CRUD 接口，前端在编辑对话框中实现智能回填（根据客户+产品自动填充历史数据）和智能Tab定位（双击任意列打开对应Tab）。

**技术栈：** Python/FastAPI（后端）、PyQt5/Python（前端）、SQLite/MySQL（数据库）

---

## 一、文件结构

### 后端文件

| 操作 | 文件路径 | 职责 |
|:---:|:---|:---|
| 创建 | `backend/models/purchase_package.py` | 包装规格数据模型 |
| 修改 | `backend/models/__init__.py` | 导出新模型 |
| 创建 | `backend/schemas/purchase_package.py` | Pydantic Schema |
| 修改 | `backend/schemas/__init__.py` | 导出新 Schema |
| 创建 | `backend/crud/purchase_package.py` | CRUD 操作 |
| 修改 | `backend/crud/__init__.py` | 导出新 CRUD |
| 创建 | `backend/routers/purchase_package.py` | API 路由 |
| 修改 | `backend/routers/__init__.py` | 注册新路由 |
| 创建 | `backend/migrations/xxx_add_purchase_item_package.sql` | 数据库迁移脚本 |

### 前端文件

| 操作 | 文件路径 | 职责 |
|:---:|:---|:---|
| 修改 | `client/main.py` | 智能Tab定位、订单总表双击编辑 |
| 修改 | `client/widgets/order_summary_edit_dialog.py` | 包装规格编辑、智能回填 |
| 修改 | `client/api/client.py` | 新增 API 调用方法 |
| 修改 | `client/api/cached_client.py` | 新增 API 调用方法 |

### 文档文件

| 操作 | 文件路径 | 职责 |
|:---:|:---|:---|
| 修改 | `docs/业务全流程图_文件导入需求.html` | 更新数据来源映射（已完成） |

---

## 二、实现任务

### 任务 1：后端 - 数据库迁移脚本

**文件：**
- 创建：`backend/migrations/2026_05_28_add_purchase_item_package.sql`

- [ ] **步骤 1：编写数据库迁移 SQL 脚本**

```sql
-- =====================================================
-- 迁移脚本：创建采购订单明细项包装规格关联表
-- 日期：2026-05-28
-- =====================================================

CREATE TABLE IF NOT EXISTS `po_purchase_order_item_package` (
    `id`                  BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `po_item_id`          BIGINT NOT NULL COMMENT '采购明细项ID FK → po_purchase_order_item.id',
    `packing_type`        VARCHAR(50) COMMENT '包装方式: 纸箱/托盘/木箱/无',
    `units_per_carton`    INT COMMENT '每箱数量/打包规格',
    `carton_length_cm`    DECIMAL(10,2) COMMENT '纸箱长度(cm)',
    `carton_width_cm`     DECIMAL(10,2) COMMENT '纸箱宽度(cm)',
    `carton_height_cm`    DECIMAL(10,2) COMMENT '纸箱高度(cm)',
    `created_at`          DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY `uk_po_item_id` (`po_item_id`),
    FOREIGN KEY (`po_item_id`) REFERENCES `po_purchase_order_item`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采购订单明细项包装规格关联表';

-- 创建索引优化查询
CREATE INDEX `idx_po_item_package_created` ON `po_purchase_order_item_package`(`created_at`);
```

- [ ] **步骤 2：验证 SQL 语法**

检查脚本语法是否正确，确保可以独立执行。

- [ ] **步骤 3：Commit**

```bash
git add backend/migrations/2026_05_28_add_purchase_item_package.sql
git commit -m "feat: add purchase item package migration script"
```

---

### 任务 2：后端 - 新增数据模型

**文件：**
- 创建：`backend/models/purchase_package.py`
- 修改：`backend/models/__init__.py:1-20`（添加导出）

- [ ] **步骤 1：编写 Model 代码**

```python
# backend/models/purchase_package.py
from sqlalchemy import Column, BigInteger, Integer, DECIMAL, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class PoPurchaseOrderItemPackage(Base):
    """采购订单明细项包装规格关联表"""
    __tablename__ = "po_purchase_order_item_package"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    po_item_id = Column(BigInteger, ForeignKey("po_purchase_order_item.id", ondelete="CASCADE"), 
                        nullable=False, unique=True, comment="采购明细项ID")
    packing_type = Column(String(50), comment="包装方式: 纸箱/托盘/木箱/无")
    units_per_carton = Column(Integer, comment="每箱数量/打包规格")
    carton_length_cm = Column(DECIMAL(10,2), comment="纸箱长度(cm)")
    carton_width_cm = Column(DECIMAL(10,2), comment="纸箱宽度(cm)")
    carton_height_cm = Column(DECIMAL(10,2), comment="纸箱高度(cm)")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关系
    po_item = relationship("PoPurchaseOrderItem", backref="package")
```

- [ ] **步骤 2：更新 __init__.py 导出**

```python
# backend/models/__init__.py
# 在文件开头添加新模型导出

from .purchase_package import PoPurchaseOrderItemPackage

__all__ = [
    # ... 其他模型 ...
    "PoPurchaseOrderItemPackage",
]
```

- [ ] **步骤 3：Commit**

```bash
git add backend/models/purchase_package.py backend/models/__init__.py
git commit -m "feat: add PoPurchaseOrderItemPackage model"
```

---

### 任务 3：后端 - 新增 Schema

**文件：**
- 创建：`backend/schemas/purchase_package.py`
- 修改：`backend/schemas/__init__.py`（添加导出）

- [ ] **步骤 1：编写 Schema 代码**

```python
# backend/schemas/purchase_package.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PurchasePackageBase(BaseModel):
    """包装规格基础 Schema"""
    packing_type: Optional[str] = Field(None, description="包装方式: 纸箱/托盘/木箱/无")
    units_per_carton: Optional[int] = Field(None, description="每箱数量/打包规格")
    carton_length_cm: Optional[float] = Field(None, description="纸箱长度(cm)")
    carton_width_cm: Optional[float] = Field(None, description="纸箱宽度(cm)")
    carton_height_cm: Optional[float] = Field(None, description="纸箱高度(cm)")


class PurchasePackageCreate(PurchasePackageBase):
    """创建包装规格请求"""
    po_item_id: int = Field(..., description="采购明细项ID")


class PurchasePackageUpdate(PurchasePackageBase):
    """更新包装规格请求"""
    pass


class PurchasePackageResponse(PurchasePackageBase):
    """包装规格响应"""
    id: int
    po_item_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HistoryPackageResponse(BaseModel):
    """历史包装规格查询响应"""
    found: bool = Field(..., description="是否找到历史记录")
    package: Optional[PurchasePackageBase] = Field(None, description="包装规格数据")
    source: Optional[str] = Field(None, description="来源说明")
    created_at: Optional[datetime] = Field(None, description="历史记录创建时间")
```

- [ ] **步骤 2：更新 __init__.py 导出**

```python
# backend/schemas/__init__.py
from .purchase_package import (
    PurchasePackageBase,
    PurchasePackageCreate,
    PurchasePackageUpdate,
    PurchasePackageResponse,
    HistoryPackageResponse,
)

__all__ = [
    # ... 其他 schema ...
    "PurchasePackageBase",
    "PurchasePackageCreate",
    "PurchasePackageUpdate",
    "PurchasePackageResponse",
    "HistoryPackageResponse",
]
```

- [ ] **步骤 3：Commit**

```bash
git add backend/schemas/purchase_package.py backend/schemas/__init__.py
git commit -m "feat: add purchase package schemas"
```

---

### 任务 4：后端 - 新增 CRUD 操作

**文件：**
- 创建：`backend/crud/purchase_package.py`
- 修改：`backend/crud/__init__.py`（添加导出）

- [ ] **步骤 1：编写 CRUD 代码**

```python
# backend/crud/purchase_package.py
from sqlalchemy.orm import Session
from typing import Optional, List
from models.purchase_package import PoPurchaseOrderItemPackage
from models.purchase import PoPurchaseOrderItem
from schemas.purchase_package import (
    PurchasePackageCreate,
    PurchasePackageUpdate,
    PurchasePackageResponse,
    HistoryPackageResponse,
)


def get_package_by_po_item(db: Session, po_item_id: int) -> Optional[PoPurchaseOrderItemPackage]:
    """根据采购明细项ID获取包装规格"""
    return db.query(PoPurchaseOrderItemPackage).filter(
        PoPurchaseOrderItemPackage.po_item_id == po_item_id
    ).first()


def create_or_update_package(db: Session, po_item_id: int, 
                             package_data: PurchasePackageCreate) -> PoPurchaseOrderItemPackage:
    """创建或更新包装规格（upsert）"""
    existing = get_package_by_po_item(db, po_item_id)
    
    if existing:
        # 更新现有记录
        for key, value in package_data.model_dump(exclude_unset=True).items():
            if key != "po_item_id" and hasattr(existing, key):
                setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # 创建新记录
        db_package = PoPurchaseOrderItemPackage(
            po_item_id=po_item_id,
            **{k: v for k, v in package_data.model_dump().items() if k != "po_item_id"}
        )
        db.add(db_package)
        db.commit()
        db.refresh(db_package)
        return db_package


def delete_package(db: Session, po_item_id: int) -> bool:
    """删除包装规格"""
    package = get_package_by_po_item(db, po_item_id)
    if package:
        db.delete(package)
        db.commit()
        return True
    return False


def get_history_package(db: Session, customer_id: int, product_id: int) -> Optional[HistoryPackageResponse]:
    """根据客户+产品获取历史包装规格（最近一次）"""
    # 查找最近一条包含包装规格的采购明细项
    # 关联: po_item.pi_item.customer_id AND po_item.product_id
    result = (
        db.query(PoPurchaseOrderItemPackage, PoPurchaseOrderItem, PoPurchaseOrderItem.pi_id)
        .join(PoPurchaseOrderItem, PoPurchaseOrderItemPackage.po_item_id == PoPurchaseOrderItem.id)
        .join(PiProformaInvoiceItem, PoPurchaseOrderItem.pi_item_id == PiProformaInvoiceItem.id)
        .filter(PiProformaInvoiceItem.customer_id == customer_id)
        .filter(PoPurchaseOrderItem.product_id == product_id)
        .order_by(PoPurchaseOrderItemPackage.created_at.desc())
        .first()
    )
    
    if result:
        package, po_item, _ = result
        return HistoryPackageResponse(
            found=True,
            package={
                "packing_type": package.packing_type,
                "units_per_carton": package.units_per_carton,
                "carton_length_cm": float(package.carton_length_cm) if package.carton_length_cm else None,
                "carton_width_cm": float(package.carton_width_cm) if package.carton_width_cm else None,
                "carton_height_cm": float(package.carton_height_cm) if package.carton_height_cm else None,
            },
            source=f"po_item_id: {package.po_item_id}",
            created_at=package.created_at
        )
    
    return HistoryPackageResponse(found=False, package=None)
```

> **注意：** 上述 CRUD 需要导入 `PiProformaInvoiceItem` 模型，如果不在同一文件需要添加导入。

- [ ] **步骤 2：更新 __init__.py 导出**

```python
# backend/crud/__init__.py
from .purchase_package import (
    get_package_by_po_item,
    create_or_update_package,
    delete_package,
    get_history_package,
)

__all__ = [
    # ... 其他 crud ...
    "get_package_by_po_item",
    "create_or_update_package",
    "delete_package",
    "get_history_package",
]
```

- [ ] **步骤 3：Commit**

```bash
git add backend/crud/purchase_package.py backend/crud/__init__.py
git commit -m "feat: add purchase package CRUD operations"
```

---

### 任务 5：后端 - 新增 API 路由

**文件：**
- 创建：`backend/routers/purchase_package.py`
- 修改：`backend/routers/__init__.py`（注册路由）

- [ ] **步骤 1：编写 Router 代码**

```python
# backend/routers/purchase_package.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from schemas.purchase_package import (
    PurchasePackageCreate,
    PurchasePackageUpdate,
    PurchasePackageResponse,
    HistoryPackageResponse,
)
from crud import purchase_package as crud_package

router = APIRouter(prefix="/purchase-items", tags=["采购包装规格"])


@router.get("/{po_item_id}/package", response_model=Optional[PurchasePackageResponse])
def get_package(po_item_id: int, db: Session = Depends(get_db)):
    """获取采购明细项的包装规格"""
    package = crud_package.get_package_by_po_item(db, po_item_id)
    return package


@router.post("/{po_item_id}/package", response_model=PurchasePackageResponse)
def create_or_update_package(
    po_item_id: int,
    package_data: PurchasePackageCreate,
    db: Session = Depends(get_db)
):
    """创建或更新采购明细项的包装规格（upsert）"""
    if package_data.po_item_id != po_item_id:
        raise HTTPException(status_code=400, detail="po_item_id 不匹配")
    return crud_package.create_or_update_package(db, po_item_id, package_data)


@router.put("/{po_item_id}/package", response_model=PurchasePackageResponse)
def update_package(
    po_item_id: int,
    package_data: PurchasePackageUpdate,
    db: Session = Depends(get_db)
):
    """更新包装规格"""
    existing = crud_package.get_package_by_po_item(db, po_item_id)
    if not existing:
        raise HTTPException(status_code=404, detail="包装规格不存在")
    # 使用 upsert 逻辑更新
    create_data = PurchasePackageCreate(po_item_id=po_item_id, **package_data.model_dump(exclude_unset=True))
    return crud_package.create_or_update_package(db, po_item_id, create_data)


@router.delete("/{po_item_id}/package")
def delete_package(po_item_id: int, db: Session = Depends(get_db)):
    """删除包装规格"""
    success = crud_package.delete_package(db, po_item_id)
    if not success:
        raise HTTPException(status_code=404, detail="包装规格不存在")
    return {"message": "删除成功"}


@router.get("/history-package", response_model=HistoryPackageResponse)
def get_history_package(
    customer_id: int = Query(..., description="客户ID，必须为正整数", ge=1),
    product_id: int = Query(..., description="产品ID，必须为正整数", ge=1),
    db: Session = Depends(get_db)
):
    """根据客户+产品获取历史包装规格（智能回填接口）"""
    if customer_id <= 0 or product_id <= 0:
        raise HTTPException(status_code=400, detail="缺少必填参数或参数无效")
    return crud_package.get_history_package(db, customer_id, product_id)
```

- [ ] **步骤 2：注册路由**

```python
# backend/routers/__init__.py
from .purchase_package import router as purchase_package_router

def register_routers(app):
    # ... 其他路由注册 ...
    app.include_router(purchase_package_router)
```

- [ ] **步骤 3：Commit**

```bash
git add backend/routers/purchase_package.py backend/routers/__init__.py
git commit -m "feat: add purchase package API routes"
```

---

### 任务 6：前端 - API Client 新增方法

**文件：**
- 修改：`client/api/client.py`（添加包装规格 API 调用）
- 修改：`client/api/cached_client.py`（添加包装规格 API 调用）

- [ ] **步骤 1：在 client.py 添加 API 方法**

```python
# client/api/client.py

class ApiClient:
    # ... 现有方法 ...

    def get_purchase_item_package(self, po_item_id: int) -> Optional[dict]:
        """获取采购明细项的包装规格"""
        try:
            response = self._get(f"/purchase-items/{po_item_id}/package")
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"获取包装规格失败: {e}")
            return None

    def save_purchase_item_package(self, po_item_id: int, package_data: dict) -> bool:
        """保存采购明细项的包装规格"""
        try:
            response = self._post(f"/purchase-items/{po_item_id}/package", package_data)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"保存包装规格失败: {e}")
            return False

    def get_history_package(self, customer_id: int, product_id: int) -> Optional[dict]:
        """获取历史包装规格（智能回填）"""
        try:
            response = self._get(f"/purchase-items/history-package?customer_id={customer_id}&product_id={product_id}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"获取历史包装规格失败: {e}")
            return None
```

- [ ] **步骤 2：在 cached_client.py 添加相同方法（带缓存）**

```python
# client/api/cached_client.py

class CachedApiClient(ApiClient):
    # ... 现有方法 ...

    def get_history_package(self, customer_id: int, product_id: int) -> Optional[dict]:
        """获取历史包装规格（带缓存）"""
        cache_key = f"history_package_{customer_id}_{product_id}"
        # 缓存5分钟
        cached = self._cache_get(cache_key, ttl=300)
        if cached:
            return cached
        
        result = super().get_history_package(customer_id, product_id)
        if result:
            self._cache_set(cache_key, result)
        return result
```

- [ ] **步骤 3：Commit**

```bash
git add client/api/client.py client/api/cached_client.py
git commit -m "feat: add purchase package API client methods"
```

---

### 任务 7：前端 - 订单总表智能 Tab 定位

**文件：**
- 修改：`client/main.py:5800-5900`（添加智能 Tab 定位逻辑）

- [ ] **步骤 1：添加列号→Tab 映射常量**

```python
# client/main.py

class MainWindow:
    # 列号 → Tab 索引映射（智能 Tab 定位）
    COLUMN_TO_TAB = {
        # Tab0: 订单信息
        0: 0, 1: 0, 3: 0, 4: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 20: 0,
        # Tab1: 客户信息
        2: 1,
        # Tab2: 产品信息
        5: 2, 6: 2, 31: 2, 33: 2, 34: 2, 35: 2, 36: 2, 37: 2, 38: 2, 39: 2,
        # Tab3: 采购信息
        17: 3, 18: 3, 19: 3, 21: 3, 22: 3, 23: 3, 29: 3, 30: 3, 32: 3,
        # Tab4: 付款信息
        13: 4, 14: 4, 24: 4, 25: 4, 26: 4, 27: 4, 28: 4, 40: 4,
    }
```

- [ ] **步骤 2：修改订单总表双击事件处理**

```python
# client/main.py

def _on_order_detail_double_clicked(self, item):
    """订单总表单元格双击事件 - 智能 Tab 定位"""
    row = item.row()
    col = item.column()
    pi_item_id = self._get_pi_item_id(row)
    
    if not pi_item_id:
        return
    
    # 获取完整订单数据
    order_data = self._get_order_full_data(pi_item_id)
    
    # 确定目标 Tab（智能定位）
    target_tab = self.COLUMN_TO_TAB.get(col, 0)  # 默认 Tab0
    
    # 弹出编辑对话框，指定默认 Tab
    from widgets.order_summary_edit_dialog import OrderSummaryEditDialog
    dialog = OrderSummaryEditDialog(order_data, self.api_client, self)
    dialog.set_default_tab(target_tab)
    
    if dialog.exec_() == QDialog.Accepted:
        self.load_order_summary()
```

- [ ] **步骤 3：Commit**

```bash
git add client/main.py
git commit -m "feat: add smart tab navigation for order summary"
```

---

### 任务 8：前端 - 包装规格编辑和智能回填

**文件：**
- 修改：`client/widgets/order_summary_edit_dialog.py`

- [ ] **步骤 1：在 OrderSummaryEditDialog 中添加包装规格编辑区域**

```python
# client/widgets/order_summary_edit_dialog.py

class OrderSummaryEditDialog(QDialog):
    def __init__(self, order_data, api_client, parent=None):
        super().__init__(parent)
        self.order_data = order_data
        self.api_client = api_client
        self._default_tab = 0
        self._packing_hint_label = None
        self._setup_ui()

    def set_default_tab(self, tab_index):
        self._default_tab = tab_index

    def _create_purchase_tab(self) -> QWidget:
        """创建采购信息 Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # ... 现有字段（供应商、采购价等）...
        
        # ===== 包装规格区域 =====
        group = QGroupBox("包装规格")
        group_layout = QGridLayout(group)
        
        # 包装方式
        group_layout.addWidget(QLabel("包装方式:"), 0, 0)
        self._packing_type_combo = QComboBox()
        self._packing_type_combo.addItems(["请选择", "纸箱", "托盘", "木箱", "无"])
        group_layout.addWidget(self._packing_type_combo, 0, 1)
        
        # 每箱数量
        group_layout.addWidget(QLabel("每箱数量:"), 0, 2)
        self._units_per_carton = QSpinBox()
        self._units_per_carton.setRange(0, 99999)
        group_layout.addWidget(self._units_per_carton, 0, 3)
        
        # 纸箱尺寸
        group_layout.addWidget(QLabel("纸箱尺寸(cm):"), 1, 0)
        self._carton_length = QSpinBox()
        self._carton_length.setRange(0, 999)
        self._carton_length.setSuffix(" 长")
        group_layout.addWidget(self._carton_length, 1, 1)
        
        self._carton_width = QSpinBox()
        self._carton_width.setRange(0, 999)
        self._carton_width.setSuffix(" 宽")
        group_layout.addWidget(self._carton_width, 1, 2)
        
        self._carton_height = QSpinBox()
        self._carton_height.setRange(0, 999)
        self._carton_height.setSuffix(" 高")
        group_layout.addWidget(self._carton_height, 1, 3)
        
        # 整箱毛重
        group_layout.addWidget(QLabel("整箱毛重:"), 2, 0)
        self._gross_weight = QDoubleSpinBox()
        self._gross_weight.setRange(0, 99999)
        self._gross_weight.setSuffix(" kg")
        group_layout.addWidget(self._gross_weight, 2, 1)
        
        # 提示标签
        self._packing_hint_label = QLabel()
        self._packing_hint_label.setStyleSheet("color: gray; font-size: 12px;")
        self._packing_hint_label.hide()
        group_layout.addWidget(self._packing_hint_label, 3, 0, 1, 4)
        
        layout.addWidget(group)
        return widget

    def _try_auto_fill_packing_spec(self):
        """尝试自动填充历史包装规格"""
        customer_id = self.order_data.get("customer_id")
        product_id = self.order_data.get("product_id")
        
        if not (customer_id and product_id):
            return
        
        # 显示加载提示
        self._show_packing_hint("⏳ 正在获取历史包装规格...", "gray")
        
        # 异步获取历史数据
        def on_result(result):
            if result and result.get("found") and result.get("package"):
                self._fill_packing_spec_fields(result["package"])
                self._show_packing_hint("✓ 已自动填充上次的包装规格（可修改）", "green")
            else:
                self._show_packing_hint("ℹ️ 暂无历史包装规格，请手动填写", "gray")
                self._clear_packing_spec_fields()
        
        self.api_client.get_history_package_async(
            customer_id, product_id, callback=on_result
        )

    def _show_packing_hint(self, text: str, color: str):
        """显示包装规格提示"""
        self._packing_hint_label.setText(text)
        if color == "green":
            self._packing_hint_label.setStyleSheet("color: #22c55e; font-size: 12px;")
        else:
            self._packing_hint_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        self._packing_hint_label.show()

    def _fill_packing_spec_fields(self, package: dict):
        """填充包装规格字段"""
        if package.get("packing_type"):
            self._packing_type_combo.setCurrentText(package["packing_type"])
        if package.get("units_per_carton"):
            self._units_per_carton.setValue(package["units_per_carton"])
        if package.get("carton_length_cm"):
            self._carton_length.setValue(int(package["carton_length_cm"]))
        if package.get("carton_width_cm"):
            self._carton_width.setValue(int(package["carton_width_cm"]))
        if package.get("carton_height_cm"):
            self._carton_height.setValue(int(package["carton_height_cm"]))

    def _clear_packing_spec_fields(self):
        """清空包装规格字段"""
        self._packing_type_combo.setCurrentIndex(0)
        self._units_per_carton.setValue(0)
        self._carton_length.setValue(0)
        self._carton_width.setValue(0)
        self._carton_height.setValue(0)
```

- [ ] **步骤 2：Commit**

```bash
git add client/widgets/order_summary_edit_dialog.py
git commit -m "feat: add packing spec editing and auto-fill in order dialog"
```

---

### 任务 9：前端 - API Client 异步方法

**文件：**
- 修改：`client/api/client.py`

- [ ] **步骤 1：添加异步 API 调用方法**

```python
# client/api/client.py

class ApiClient:
    # ... 现有方法 ...

    def get_history_package_async(self, customer_id: int, product_id: int, callback):
        """异步获取历史包装规格"""
        def worker():
            try:
                result = self.get_history_package(customer_id, product_id)
                # 在主线程调用回调
                QMetaObject.invokeMethod(
                    self._get_main_window(),
                    "_on_history_package_ready",
                    Qt.QueuedConnection,
                    Q_ARG(object, result)
                )
            except Exception as e:
                logger.error(f"获取历史包装规格失败: {e}")
        
        self._executor.submit(worker)
```

- [ ] **步骤 2：Commit**

```bash
git add client/api/client.py
git commit -m "feat: add async method for history package API"
```

---

## 三、规格覆盖度检查

| 规格章节 | 对应任务 | 状态 |
|:---|:---|:---:|
| 2.1 新的数据来源对照 | 任务1-5（后端）+ 任务6-8（前端） | ✅ |
| 2.2 新建表 | 任务1（数据库迁移） | ✅ |
| 3.2 智能回填逻辑 | 任务8（前端智能回填） | ✅ |
| 4.1 API 接口 | 任务5（API路由）+ 任务6（API Client） | ✅ |
| 6.1 提示交互设计 | 任务8（前端提示） | ✅ |
| 7.1-7.3 智能 Tab 定位 | 任务7（智能 Tab 定位） | ✅ |
| 8.1 提示交互设计 | 任务8（前端提示） | ✅ |

---

## 四、执行方式选择

**计划已完成并保存到 `docs/superpowers/plans/2026-05-28-packing-spec-implementation.md`。两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**