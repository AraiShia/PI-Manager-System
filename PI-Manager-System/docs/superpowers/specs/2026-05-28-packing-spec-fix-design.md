# 包装规格功能代码审查修复规格说明

> **日期：** 2026-05-28
> **类型：** 代码修复规格说明
> **关联审查：** chinese-code-review 反馈
> **目标：** 修复 3 个必须修复问题 + 优化 5 个建议修改项

---

## 一、修复背景

### 1.1 审查结论

| 优先级 | 数量 | 处理时间 |
|:---:|:---:|:---|
| 🔴 必须修复 | 3 | 合入前 |
| 🟡 建议修改 | 5 | 本周内 |
| 🔵 仅供参考 | 3 | 下个迭代 |

### 1.2 必须修复的问题清单

| # | 问题 | 文件 | 风险级别 |
|:---:|:---|:---|:---:|
| 1 | CRUD 层缺少事务管理 | backend/crud/purchase_package.py | 数据不一致 |
| 2 | GET 接口返回 None 导致序列化错误 | backend/routers/purchase_package.py | 运行时异常 |
| 3 | 路由层重复参数校验（死代码） | backend/routers/purchase_package.py | 可维护性 |

---

## 二、必须修复方案

### 2.1 问题 1：CRUD 事务管理

**问题描述：**
```python
# 当前代码 - 缺少事务保护
def create_or_update_package(db: Session, po_item_id: int, ...):
    existing = get_package_by_po_item(db, po_item_id)
    if existing:
        for key, value in ...:
            setattr(existing, key, value)
        db.commit()  # 如果这里失败，前面修改已生效但未回滚
        db.refresh(existing)
```

**修复方案：局部 try-finally**

```python
def create_or_update_package(db: Session, po_item_id: int, 
                             package_data: PurchasePackageCreate) -> PoPurchaseOrderItemPackage:
    """创建或更新包装规格（upsert）
    
    事务保护：任何异常都会自动回滚
    """
    try:
        existing = get_package_by_po_item(db, po_item_id)
        
        if existing:
            update_data = package_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if key != "po_item_id" and hasattr(existing, key):
                    setattr(existing, key, value)
            db.flush()  # 先刷新，验证数据合法性
            db.commit()
            db.refresh(existing)
            return existing
        else:
            db_package = PoPurchaseOrderItemPackage(
                po_item_id=po_item_id,
                **{k: v for k, v in package_data.model_dump().items() if k != "po_item_id"}
            )
            db.add(db_package)
            db.flush()
            db.commit()
            db.refresh(db_package)
            return db_package
    except Exception:
        db.rollback()
        raise
```

**同样修复 `delete_package`：**
```python
def delete_package(db: Session, po_item_id: int) -> bool:
    """删除包装规格"""
    try:
        package = get_package_by_po_item(db, po_item_id)
        if package:
            db.delete(package)
            db.commit()
            return True
        return False
    except Exception:
        db.rollback()
        raise
```

---

### 2.2 问题 2：GET 接口返回值

**问题描述：**
```python
# 当前代码 - 返回 None 与 response_model 不匹配
@router.get("/{po_item_id}/package", response_model=PurchasePackageResponse)
def get_package(po_item_id: int, db: Session = Depends(get_db)):
    package = crud_package.get_package_by_po_item(db, po_item_id)
    if not package:
        return None  # ❌ response_model 无法处理 None
    return package
```

**修复方案：返回 404**

```python
@router.get("/{po_item_id}/package", response_model=PurchasePackageResponse)
def get_package(po_item_id: int, db: Session = Depends(get_db)):
    """获取采购明细项的包装规格
    
    Returns:
        200: 包装规格数据
        404: 包装规格不存在
    """
    package = crud_package.get_package_by_po_item(db, po_item_id)
    if not package:
        raise HTTPException(status_code=404, detail="包装规格不存在")
    return package
```

---

### 2.3 问题 3：冗余参数校验

**问题描述：**
```python
# 当前代码 - 死代码，永远不会触发
@router.get("/history-package", response_model=HistoryPackageResponse)
def get_history_package(
    customer_id: int = Query(..., description="客户ID，必须为正整数", ge=1),
    product_id: int = Query(..., description="产品ID，必须为正整数", ge=1),
    db: Session = Depends(get_db)
):
    if customer_id <= 0 or product_id <= 0:  # ❌ ge=1 已保证，不会触发
        raise HTTPException(status_code=400, detail="缺少必填参数或参数无效")
    return crud_package.get_history_package(db, customer_id, product_id)
```

**修复方案：直接删除冗余校验**

```python
@router.get("/history-package", response_model=HistoryPackageResponse)
def get_history_package(
    customer_id: int = Query(..., description="客户ID", ge=1),
    product_id: int = Query(..., description="产品ID", ge=1),
    db: Session = Depends(get_db)
):
    """根据客户+产品获取历史包装规格（智能回填接口）
    
    参数校验：
    - ge=1 约束确保参数为正整数
    
    返回：
    - found=True + package: 找到历史记录
    - found=False + package=None: 无历史记录（正常返回）
    """
    return crud_package.get_history_package(db, customer_id, product_id)
```

---

## 三、建议优化方案

### 3.1 前端异步方法超时控制

**文件：** client/widgets/order_summary_edit_dialog.py

**问题：** 无防抖，多次点击产生多个并发请求

**优化方案：**
```python
def _load_history_package_async(self):
    """异步加载历史包装规格数据（带防抖）
    
    防抖机制：
    - 防止重复请求（_loading_history 标志位）
    - 5秒超时保护
    """
    customer_id = self.order_data.get('customer_id')
    product_id = self.order_data.get('product_id')
    
    if not customer_id or not product_id:
        print(f"[INFO] 智能回填: 缺少客户ID或产品ID，跳过")
        return
    
    # 防抖：检查是否正在加载
    if hasattr(self, '_loading_history') and self._loading_history:
        print("[INFO] 智能回填: 正在加载中，请稍候")
        return
    
    self._loading_history = True
    
    import threading
    
    def fetch_history():
        try:
            result = self.api_client.get_history_package(customer_id, product_id)
            from PySide6.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(
                self, "_on_history_package_loaded", Qt.QueuedConnection,
                [object], result
            )
        except Exception as e:
            print(f"[ERROR] 智能回填失败: {e}")
        finally:
            self._loading_history = False
    
    thread = threading.Thread(target=fetch_history, daemon=True)
    thread.start()
    
    # 5秒超时保护
    from PySide6.QtCore import QTimer
    QTimer.singleShot(5000, lambda: self._check_history_timeout())
```

---

### 3.2 前端保存用户反馈

**文件：** client/widgets/order_summary_edit_dialog.py

**问题：** 包装规格保存失败时用户不知道

**优化方案：**
```python
# 收集包装规格数据
po_item_id = self.order_data.get('po_item_id')
if po_item_id:
    package_data = {
        'packing_type': self.packing_type_combo.currentText() or None,
        # ... 其他字段
    }
    
    try:
        save_result = self.api_client.save_purchase_item_package(po_item_id, package_data)
        if save_result:
            data['package_saved'] = True
        else:
            reply = QMessageBox.question(
                self, "包装规格保存失败",
                "主订单信息已保存，但包装规格保存失败。\n\n是否仍要关闭对话框？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
    except Exception as e:
        QMessageBox.critical(self, "保存错误", f"包装规格保存异常:\n{str(e)}")
        return
```

---

### 3.3 API Client 错误分类

**文件：** client/api/client.py

**问题：** 所有异常都返回 None，调用方无法区分错误类型

**优化方案：**
```python
class PackageApiError(Exception):
    """包装规格 API 错误基类"""
    pass

class PackageNotFoundError(PackageApiError):
    """包装规格不存在（404）"""
    pass

class PackageNetworkError(PackageApiError):
    """网络错误"""
    pass

def get_purchase_item_package(self, po_item_id: int) -> Optional[Dict]:
    """获取采购明细项的包装规格
    
    Raises:
        PackageNotFoundError: 包装规格不存在（404）
        PackageNetworkError: 网络错误
    """
    try:
        return self.get(f"/purchase-items/{po_item_id}/package")
    except requests.exceptions.ConnectionError as e:
        raise PackageNetworkError(f"网络连接失败: {e}")
    except requests.exceptions.Timeout as e:
        raise PackageNetworkError(f"请求超时: {e}")
```

---

### 3.4 列号→Tab 映射表注释完善

**文件：** client/main.py

**优化方案：**
```python
COLUMN_TO_TAB = {
    # ===== Tab0: 订单信息 =====
    0: 0,   # 订单日期
    1: 0,   # ORDER NO.
    3: 0,   # OE号
    4: 0,   # 客户需求备注
    7: 0,   # 客户型号
    8: 0,   # OE号.1
    9: 0,   # 数量
    10: 0,  # 报价(USD/RMB)
    11: 0,  # 合计金额
    12: 0,  # 客户最新回复
    20: 0,  # （预留）
    
    # ===== Tab1: 客户信息 =====
    2: 1,   # 客户产品编号
    
    # ===== Tab2: 产品信息（含包装规格）=====
    5: 2,   # 产品名称
    6: 2,   # 图片
    31: 2,  # （预留）
    33: 2,  # 纸箱尺寸
    34: 2,  # 打包规格
    35: 2,  # （预留）
    36: 2,  # （预留）
    37: 2,  # 整箱毛重
    38: 2,  # （预留）
    39: 2,  # （预留）
    
    # ===== Tab3: 采购信息（含包装方式）=====
    17: 3,  # 采购价格
    18: 3,  # 预估美金报价
    19: 3,  # 预估毛利率
    21: 3,  # 供应商
    22: 3,  # 店铺链接
    23: 3,  # 运费
    29: 3,  # 包装方式
    30: 3,  # 采购选项/名称
    32: 3,  # 工厂编号
    
    # ===== Tab4: 付款信息 =====
    13: 4,  # 客户预付款
    14: 4,  # 待收尾款
    24: 4,  # 工厂订金
    25: 4,  # 工厂尾款
    26: 4,  # 付款阶段
    27: 4,  # 预付比例
    28: 4,  # 开票状态
    40: 4,  # （预留）
}
```

---

### 3.5 查询性能优化

**文件：** backend/crud/purchase_package.py

**优化方案：**

1. **限制查询字段（减少数据传输）：**
```python
def get_history_package(db: Session, customer_id: int, product_id: int) -> HistoryPackageResponse:
    """根据客户+产品获取历史包装规格（最近一次）
    
    性能优化：
    - 只查询需要的字段
    - 使用 order_by desc 降序排列获取最新记录
    """
    # 只查询需要的字段
    result = (
        db.query(
            PoPurchaseOrderItemPackage.packing_type,
            PoPurchaseOrderItemPackage.units_per_carton,
            PoPurchaseOrderItemPackage.carton_length_cm,
            PoPurchaseOrderItemPackage.carton_width_cm,
            PoPurchaseOrderItemPackage.carton_height_cm,
            PoPurchaseOrderItemPackage.po_item_id,
            PoPurchaseOrderItemPackage.created_at,
        )
        .join(PoPurchaseOrderItem, PoPurchaseOrderItemPackage.po_item_id == PoPurchaseOrderItem.id)
        .join(PiProformaInvoiceItem, PoPurchaseOrderItem.pi_item_id == PiProformaInvoiceItem.id)
        .filter(PiProformaInvoiceItem.customer_id == customer_id)
        .filter(PoPurchaseOrderItem.product_id == product_id)
        .order_by(desc(PoPurchaseOrderItemPackage.created_at))
        .first()
    )
```

2. **数据库索引（已在迁移脚本中创建）：**
```sql
-- 已创建的索引
CREATE INDEX idx_po_item_package_created ON po_purchase_order_item_package(created_at);
```

---

## 四、修改文件清单

| 序号 | 文件路径 | 修改类型 | 优先级 |
|:---:|:---|:---:|:---:|
| 1 | backend/crud/purchase_package.py | 修改 | 🔴 必须 |
| 2 | backend/routers/purchase_package.py | 修改 | 🔴 必须 |
| 3 | client/widgets/order_summary_edit_dialog.py | 修改 | 🟡 建议 |
| 4 | client/api/client.py | 修改 | 🟡 建议 |
| 5 | client/main.py | 修改 | 🟡 建议 |

---

## 五、预期效果

### 5.1 必须修复项

| 问题 | 修复后效果 |
|:---|:---|
| 事务管理 | 任何数据库操作异常都会自动回滚，不会产生脏数据 |
| GET 返回值 | 不存在资源时返回 404，与其他路由行为一致 |
| 冗余校验 | 代码简洁易读，无死代码干扰 |

### 5.2 建议优化项

| 问题 | 优化后效果 |
|:---|:---|
| 超时控制 | 防止重复请求，5秒超时保护 |
| 用户反馈 | 保存失败时给用户明确提示 |
| 错误分类 | 调用方可区分不同错误类型并针对性处理 |
| 映射表注释 | 新人能快速理解列号与 Tab 的对应关系 |
| 查询优化 | 减少数据传输，提升查询性能 |

---

## 六、验收标准

### 6.1 必须修复验收

- [ ] CRUD 层 `create_or_update_package` 包含 try-except-rollback
- [ ] CRUD 层 `delete_package` 包含 try-except-rollback
- [ ] GET 接口不存在时返回 404（测试：访问 `/purchase-items/9999/package`）
- [ ] `/history-package` 接口移除冗余的参数校验代码

### 6.2 建议优化验收

- [ ] `_load_history_package_async` 包含防抖逻辑
- [ ] 保存失败时弹出确认对话框
- [ ] API Client 方法能区分"不存在"和"网络错误"
- [ ] `COLUMN_TO_TAB` 每行列号有中文注释

---

## 七、风险评估

| 风险 | 影响 | 缓解措施 |
|:---|:---|:---|
| 事务管理改动范围大 | 可能影响其他模块 | 只修改 purchase_package.py，不改动其他 CRUD 模块 |
| 404 返回改变前端行为 | 前端可能未处理 404 | 前端 GET 方法返回 None 时仍保持兼容 |

---

## 八、后续计划

### 8.1 本次迭代（必须修复）

1. 修复 3 个必须修复问题
2. 通过验收测试
3. 提交代码审查

### 8.2 下个迭代（建议优化）

1. 实现超时控制和防抖逻辑
2. 完善用户反馈机制
3. 添加单元测试覆盖

---

**文档状态：** 待审查
**创建时间：** 2026-05-28
**最后更新：** 2026-05-28
