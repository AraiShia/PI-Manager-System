
# 订单产品编辑功能实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为订单详情表格的产品项添加完整的编辑能力：简单字段表格内联编辑、编辑产品 Dialog（768×1280）负责产品与包装信息、更换供应商 Dialog 负责采购/供应商信息、右键菜单新增采购快照与访问店铺网站入口。

**架构：** 在 `order_detail_panel.py` 中扩展表格编辑标志与右键菜单，新增/重构 `product_item_edit_dialog.py` 作为完整编辑 Dialog，新增 `supplier_change_dialog.py` 作为更换供应商 Dialog，复用 `PUT /pi/items/{item_id}` 进行字段保存，并在后端新增采购单重新生成与库存联动逻辑。

**技术栈：** PySide6（前端）、FastAPI + SQLAlchemy（后端）、SQLite（数据库）。

---

## 文件结构

| 文件 | 职责 |
|---|---|
| `client/widgets/order_summary/order_detail_panel.py` | 订单详情表格。设置可编辑列、处理失焦保存、扩展右键菜单、转发 Dialog 打开信号。 |
| `client/widgets/product_item_edit_dialog.py` | 编辑产品 Dialog（768×1280）。显示所有字段，可编辑字段按状态启用/禁用，采购/供应商字段锁定显示并带入口按钮。 |
| `client/widgets/supplier_change_dialog.py` | 更换供应商 Dialog。编辑采购/工厂/供应商/开票字段，保存后重新生成采购单。 |
| `client/widgets/purchase_snapshot_dialog.py` | 采购快照 Dialog。只读展示当前采购状态。 |
| `client/api/client.py` | 已包含 `update_pi_item(item_id, data)`；新增 `change_supplier(item_id, data)`。 |
| `backend/routers/pi.py` | 扩展 `/pi/items/{item_id}` 以支持更多字段；新增 `/pi/items/{item_id}/change-supplier`。 |
| `backend/crud/pi.py` | 扩展 `update_pi_item` 支持新字段；新增 `change_pi_item_supplier` 处理采购单重新生成。 |
| `backend/crud/purchase.py` | 提供 `_build_purchase_order_item` 与 `create_grouped_purchase_orders`，用于重新生成采购单。 |
| `backend/models/pi.py` | 已包含 `PiProformaInvoiceItem` 全部字段定义。 |
| `backend/models/purchase.py` | 已包含 `PoPurchaseOrder`、`PoPurchaseOrderItem` 模型。 |
| `backend/models/inventory.py` | 已包含 `InvInventory` 模型。 |

---

## 任务 1：后端扩展 `update_pi_item` 支持缺失字段

**文件：**
- 修改：`backend/crud/pi.py:1040-1240`

当前 `update_pi_item` 已支持大部分字段，但缺少：`shipping_fee`、`misc_fee`、`delivery_date`、`product_name`、`image_url`/`default_image_url`、`brand`、`invoice_status`、`supplier_name`/`factory_short_name`、`shop_url`/`line_1688_url`、`factory_code`、`purchase_price`/`factory_price`。本任务补齐这些字段的写入逻辑。

- [ ] **步骤 1：编写失败测试**

在 `backend/tests/crud/test_pi.py` 新增（如不存在则创建）：

```python
def test_update_pi_item_supports_all_editable_fields(db, sample_pi_item):
    from backend.crud.pi import update_pi_item
    data = {
        "shipping_fee": 12.5,
        "misc_fee": 3.0,
        "delivery_date": "2026-08-15",
        "product_name": "Updated Name",
        "brand": "BOSCH",
        "invoice_status": "增票",
        "supplier_name": "New Factory",
        "shop_url": "https://example.com/123",
        "factory_code": "FC-001",
        "purchase_price": 88.8,
    }
    item = update_pi_item(db, sample_pi_item.id, data)
    assert float(item.shipping_fee) == 12.5
    assert float(item.misc_fee) == 3.0
    assert item.delivery_date is not None
    assert item.product_name == "Updated Name"
    assert item.brand == "BOSCH"
    assert item.invoice_status == "增票"
    assert item.supplier_name == "New Factory"
    assert item.shop_url == "https://example.com/123"
    assert item.factory_code == "FC-001"
    assert float(item.purchase_price) == 88.8
```

- [ ] **步骤 2：运行测试验证失败**

```bash
cd e:\AI\TraeProject\PI-Manager-System\backend
pytest tests/crud/test_pi.py::test_update_pi_item_supports_all_editable_fields -v
```

预期：FAIL，`AttributeError` 或字段未更新。

- [ ] **步骤 3：扩展 `update_pi_item` 字段处理**

在 `backend/crud/pi.py` 的 `update_pi_item` 函数中，在现有字段处理之后、`# ---- 派生字段:total_price ----` 之前插入：

```python
    # ---- 其他可编辑字段 ----
    if 'shipping_fee' in update_data and update_data['shipping_fee'] is not None:
        db_item.shipping_fee = float(update_data['shipping_fee'])
    if 'misc_fee' in update_data and update_data['misc_fee'] is not None:
        db_item.misc_fee = float(update_data['misc_fee'])
    if 'delivery_date' in update_data:
        from datetime import datetime
        val = update_data['delivery_date']
        if val:
            if isinstance(val, str):
                db_item.delivery_date = datetime.strptime(val[:10], "%Y-%m-%d")
            else:
                db_item.delivery_date = val
        else:
            db_item.delivery_date = None
    if 'product_name' in update_data:
        db_item.product_name = update_data['product_name']
    if 'image_url' in update_data:
        db_item.image_url = update_data['image_url']
    if 'default_image_url' in update_data:
        db_item.image_url = update_data['default_image_url']
    if 'brand' in update_data:
        db_item.brand = update_data['brand']
    if 'invoice_status' in update_data:
        db_item.invoice_status = update_data['invoice_status']
    if 'supplier_name' in update_data:
        db_item.supplier_name = update_data['supplier_name']
    if 'factory_short_name' in update_data:
        db_item.supplier_name = update_data['factory_short_name']
    if 'shop_url' in update_data:
        db_item.shop_url = update_data['shop_url']
    if 'line_1688_url' in update_data:
        db_item.shop_url = update_data['line_1688_url']
    if 'factory_code' in update_data:
        db_item.factory_code = update_data['factory_code']
    if 'purchase_price' in update_data and update_data['purchase_price'] is not None:
        db_item.purchase_price = float(update_data['purchase_price'])
    if 'factory_price' in update_data and update_data['factory_price'] is not None:
        db_item.purchase_price = float(update_data['factory_price'])
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/crud/test_pi.py::test_update_pi_item_supports_all_editable_fields -v
```

预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add backend/crud/pi.py backend/tests/crud/test_pi.py
git commit -m "feat(backend): extend update_pi_item to support all editable fields"
```

---

## 任务 2：后端新增更换供应商 CRUD

**文件：**
- 修改：`backend/crud/pi.py`
- 可能修改：`backend/crud/purchase.py`

- [ ] **步骤 1：编写失败测试**

```python
def test_change_supplier_recreate_purchase_order(db, sample_pi_with_purchase):
    from backend.crud.pi import change_pi_item_supplier
    result = change_pi_item_supplier(
        db,
        item_id=sample_pi_with_purchase.item_id,
        supplier_data={
            "supplier_name": "New Factory",
            "shop_url": "https://new.example.com",
            "purchase_price": 99.9,
            "invoice_status": "增票",
        },
    )
    assert result["success"] is True
    assert result["new_po_id"] is not None
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/crud/test_pi.py::test_change_supplier_recreate_purchase_order -v
```

预期：FAIL，`change_pi_item_supplier` 未定义。

- [ ] **步骤 3：实现 `change_pi_item_supplier`**

在 `backend/crud/pi.py` 中新增函数：

```python
def change_pi_item_supplier(db: Session, item_id: int, supplier_data: dict) -> dict:
    """更换 PI item 的供应商/采购信息，并重新生成采购单。

    约束：
    - 必须已存在采购单（否则不允许调用）。
    - 若原采购单已收货/已入库，拒绝更换。
    - 删除原采购单及采购项，创建新采购单。
    """
    from models import PoPurchaseOrder, PoPurchaseOrderItem, SupSupplier
    from crud.purchase import create_grouped_purchase_orders
    from schemas.purchase import PurchaseOrderCreate, PurchaseOrderItemCreate

    db_item = get_pi_item(db, item_id)
    if not db_item:
        raise ValueError("订单项不存在")

    # 1. 查找当前采购单
    old_po_items = db.query(PoPurchaseOrderItem).filter(
        PoPurchaseOrderItem.pi_item_id == item_id
    ).all()
    if not old_po_items:
        raise ValueError("该订单项尚未生成采购单")

    old_po_item = old_po_items[0]
    old_po = db.query(PoPurchaseOrder).filter(
        PoPurchaseOrder.id == old_po_item.po_id
    ).first()

    # 2. 检查是否可更换
    if old_po_item.inbound_status not in (None, 1):
        raise ValueError("采购单已入库或已收货，无法更换供应商")

    # 3. 更新 PI item 字段
    field_map = {
        "supplier_name": "supplier_name",
        "factory_short_name": "supplier_name",
        "shop_url": "shop_url",
        "line_1688_url": "shop_url",
        "factory_code": "factory_code",
        "brand": "brand",
        "purchase_price": "purchase_price",
        "factory_price": "purchase_price",
        "factory_deposit": "factory_deposit",
        "factory_balance": "factory_balance",
        "invoice_status": "invoice_status",
    }
    for src, dst in field_map.items():
        if src in supplier_data and supplier_data[src] is not None:
            if src in ("purchase_price", "factory_price", "factory_deposit", "factory_balance"):
                setattr(db_item, dst, float(supplier_data[src]))
            else:
                setattr(db_item, dst, supplier_data[src])

    # 4. 获取或创建供应商
    supplier_name = supplier_data.get("supplier_name") or supplier_data.get("factory_short_name") or db_item.supplier_name
    supplier = db.query(SupSupplier).filter(SupSupplier.name == supplier_name).first()
    if not supplier:
        supplier = SupSupplier(
            dept_id=old_po.dept_id,
            name=supplier_name,
        )
        db.add(supplier)
        db.flush()
        db.refresh(supplier)

    # 5. 删除旧采购单
    db.delete(old_po)

    # 6. 创建新采购单
    purchase = PurchaseOrderCreate(
        pi_id=db_item.pi_id,
        dept_id=old_po.dept_id,
        supplier_id=supplier.id,
        currency=old_po.currency,
        items=[
            PurchaseOrderItemCreate(
                pi_item_id=db_item.id,
                product_id=db_item.product_id,
                quantity=float(db_item.quantity),
                unit_price=float(db_item.purchase_price or 0),
                line_1688_url=db_item.shop_url,
                factory_code=db_item.factory_code,
                invoice_type=db_item.invoice_status,
            )
        ],
    )
    new_orders = create_grouped_purchase_orders(db, purchase)
    new_po_id = new_orders[0].id if new_orders else None

    db.commit()
    return {"success": True, "new_po_id": new_po_id, "old_po_id": old_po.id}
```

> 注意：需要确认 `PurchaseOrderCreate` 与 `PurchaseOrderItemCreate` 的字段名及 `create_grouped_purchase_orders` 是否接受单供应商调用。若字段不匹配，按实际 schema 调整。

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/crud/test_pi.py::test_change_supplier_recreate_purchase_order -v
```

预期：PASS（可能需要根据实际 schema 调整字段名）。

- [ ] **步骤 5：Commit**

```bash
git add backend/crud/pi.py backend/tests/crud/test_pi.py
git commit -m "feat(backend): add change_pi_item_supplier to recreate PO"
```

---

## 任务 3：后端新增更换供应商路由

**文件：**
- 修改：`backend/routers/pi.py`

- [ ] **步骤 1：编写失败测试**

```python
def test_change_supplier_api(client, sample_pi_with_purchase):
    res = client.put(f"/api/pi/items/{sample_pi_with_purchase.item_id}/change-supplier", json={
        "supplier_name": "New Factory",
        "shop_url": "https://new.example.com",
        "purchase_price": 99.9,
        "invoice_status": "增票",
    })
    assert res.status_code == 200
    assert res.json()["success"] is True
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/routers/test_pi.py::test_change_supplier_api -v
```

预期：FAIL，404 或路由未注册。

- [ ] **步骤 3：注册路由**

在 `backend/routers/pi.py` 中，在 `@router.put("/items/{item_id}")` 之后新增：

```python
class ChangeSupplierRequest(BaseModel):
    supplier_name: Optional[str] = None
    factory_short_name: Optional[str] = None
    shop_url: Optional[str] = None
    line_1688_url: Optional[str] = None
    factory_code: Optional[str] = None
    brand: Optional[str] = None
    purchase_price: Optional[float] = None
    factory_price: Optional[float] = None
    factory_deposit: Optional[float] = None
    factory_balance: Optional[float] = None
    invoice_status: Optional[str] = None

@router.put("/items/{item_id}/change-supplier")
def change_supplier_api(item_id: int, payload: ChangeSupplierRequest, db: Session = Depends(get_db)):
    """更换供应商并重新生成采购单"""
    from crud.pi import change_pi_item_supplier
    try:
        result = change_pi_item_supplier(db, item_id, payload.model_dump(exclude_unset=True))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/routers/test_pi.py::test_change_supplier_api -v
```

预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add backend/routers/pi.py backend/tests/routers/test_pi.py
git commit -m "feat(backend): add change-supplier API endpoint"
```

---

## 任务 4：前端扩展 ApiClient

**文件：**
- 修改：`client/api/client.py`

- [ ] **步骤 1：在 `ApiClient` 中新增方法**

在 `client/api/client.py` 的 `update_pi_item` 附近新增：

```python
    def change_supplier(self, item_id: int, data: Dict) -> Dict:
        """更换供应商并重新生成采购单"""
        return self.put(f"/pi/items/{item_id}/change-supplier", data)
```

- [ ] **步骤 2：运行类型/语法检查**

```bash
cd e:\AI\TraeProject\PI-Manager-System\client
python -m py_compile api/client.py
```

预期：无错误。

- [ ] **步骤 3：Commit**

```bash
git add client/api/client.py
git commit -m "feat(client): add change_supplier api client method"
```

---

## 任务 5：创建 `SupplierChangeDialog`

**文件：**
- 创建：`client/widgets/supplier_change_dialog.py`

- [ ] **步骤 1：编写对话框骨架**

```python
# -*- coding: utf-8 -*-
"""更换供应商对话框"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QDoubleSpinBox, QPushButton, QFormLayout, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt


class SupplierChangeDialog(QDialog):
    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.item = item.copy()
        self.setWindowTitle("更换供应商")
        self.setMinimumSize(600, 500)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.supplier_name_edit = QLineEdit(self.item.get("supplier_name", ""))
        self.shop_url_edit = QLineEdit(self.item.get("shop_url", ""))
        self.factory_code_edit = QLineEdit(self.item.get("factory_code", ""))
        self.brand_edit = QLineEdit(self.item.get("brand", ""))

        self.purchase_price_spin = QDoubleSpinBox()
        self.purchase_price_spin.setRange(0, 99999999)
        self.purchase_price_spin.setDecimals(4)
        self.purchase_price_spin.setValue(float(self.item.get("purchase_price", 0) or 0))

        self.factory_deposit_spin = QDoubleSpinBox()
        self.factory_deposit_spin.setRange(0, 99999999)
        self.factory_deposit_spin.setDecimals(4)
        self.factory_deposit_spin.setValue(float(self.item.get("factory_deposit", 0) or 0))

        self.factory_balance_spin = QDoubleSpinBox()
        self.factory_balance_spin.setRange(0, 99999999)
        self.factory_balance_spin.setDecimals(4)
        self.factory_balance_spin.setValue(float(self.item.get("factory_balance", 0) or 0))

        self.invoice_status_combo = QComboBox()
        self.invoice_status_combo.addItems(["增票", "普票", "不开票"])
        current_invoice = self.item.get("invoice_status", "")
        idx = self.invoice_status_combo.findText(current_invoice)
        if idx >= 0:
            self.invoice_status_combo.setCurrentIndex(idx)

        form.addRow("工厂简称:", self.supplier_name_edit)
        form.addRow("店铺链接:", self.shop_url_edit)
        form.addRow("工厂编号:", self.factory_code_edit)
        form.addRow("品牌:", self.brand_edit)
        form.addRow("采购价格:", self.purchase_price_spin)
        form.addRow("工厂订金:", self.factory_deposit_spin)
        form.addRow("工厂尾款:", self.factory_balance_spin)
        form.addRow("开票情况:", self.invoice_status_combo)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet("background-color: #10b981; color: white; padding: 8px 16px; border-radius: 4px;")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _on_save(self):
        reply = QMessageBox.question(
            self,
            "确认更换供应商",
            "确定要按以上信息更换供应商并重新生成采购单吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.result_data = {
            "supplier_name": self.supplier_name_edit.text(),
            "shop_url": self.shop_url_edit.text(),
            "factory_code": self.factory_code_edit.text(),
            "brand": self.brand_edit.text(),
            "purchase_price": self.purchase_price_spin.value(),
            "factory_deposit": self.factory_deposit_spin.value(),
            "factory_balance": self.factory_balance_spin.value(),
            "invoice_status": self.invoice_status_combo.currentText(),
        }
        self.accept()

    def get_data(self):
        return getattr(self, "result_data", {})
```

- [ ] **步骤 2：语法检查**

```bash
cd e:\AI\TraeProject\PI-Manager-System\client
python -m py_compile widgets/supplier_change_dialog.py
```

预期：无错误。

- [ ] **步骤 3：Commit**

```bash
git add client/widgets/supplier_change_dialog.py
git commit -m "feat(client): add SupplierChangeDialog"
```

---

## 任务 6：重构 `ProductItemEditDialog`

**文件：**
- 修改：`client/widgets/product_item_edit_dialog.py`（完全重写）

- [ ] **步骤 1：完全重写 `ProductItemEditDialog`**

新的 Dialog 尺寸 768×1280，包含基础信息、财务、数量日期、包装规格、采购/供应商 Area、客户回复 Area。

```python
# -*- coding: utf-8 -*-
"""编辑订单产品项对话框（完整版）"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QDoubleSpinBox, QPushButton, QFormLayout, QMessageBox,
    QComboBox, QDateEdit, QScrollArea, QWidget, QTextEdit,
    QFileDialog
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QDesktopServices, QUrl


class ProductItemEditDialog(QDialog):
    COLUMN_TO_FIELD = {
        2: "customer_code",
        3: "oe_number",
        4: "remark",
        5: "product_name",
        6: "image_url",
        7: "customer_model",
        8: "product_feature",
        9: "quantity",
        10: "unit_price",
        13: "customer_prepayment",
        14: "remaining_payment",
        18: "shipping_fee",
        19: "misc_fee",
        23: "delivery_date",
        29: "packaging",
        30: "purchase_option_name",
        31: "product_detail",
        33: "carton_size",
        34: "pack_spec",
        37: "carton_gross_weight",
    }

    def __init__(self, item: dict, api_client=None, focus_column: int = None, has_formal: bool = False, is_purchased: bool = False, parent=None):
        super().__init__(parent)
        self.item = item.copy()
        self.api_client = api_client
        self.focus_column = focus_column
        self.has_formal = has_formal
        self.is_purchased = is_purchased
        self.setWindowTitle("编辑产品")
        self.resize(768, 1280)
        self._editors = {}
        self._init_ui()
        self._apply_focus()

    def _init_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)

        # 基础信息
        layout.addWidget(QLabel("<b>基础信息</b>"))
        base_form = QFormLayout()
        self._add_line_edit(base_form, "customer_code", "客户产品编号", self.item.get("customer_code", ""))
        self._add_line_edit(base_form, "oe_number", "OE号", self.item.get("oe_number", ""))
        self._add_line_edit(base_form, "remark", "客户需求/产品备注", self.item.get("remark", ""))
        self._add_line_edit(base_form, "product_name", "产品名称", self.item.get("product_name", self.item.get("detail_desc", "")))
        self._add_image_field(layout)
        self._add_line_edit(base_form, "customer_model", "客户型号", self.item.get("customer_model", ""))
        self._add_line_edit(base_form, "product_feature", "产品特性", self.item.get("product_feature", ""))
        layout.addLayout(base_form)

        # 数量与日期
        layout.addWidget(QLabel("<b>数量与日期</b>"))
        qty_form = QFormLayout()
        self._add_spin(qty_form, "quantity", "数量", self.item.get("quantity", 0))
        self._add_date(qty_form, "delivery_date", "交货日期", self.item.get("delivery_date"))
        layout.addLayout(qty_form)

        # 财务
        layout.addWidget(QLabel("<b>财务</b>"))
        fin_form = QFormLayout()
        self._add_spin(fin_form, "unit_price", "报价", self.item.get("unit_price", 0))
        self._add_spin(fin_form, "customer_prepayment", "客户预付款", self.item.get("customer_prepayment", 0))
        self._add_spin(fin_form, "remaining_payment", "待收尾款", self.item.get("remaining_payment", 0))
        self._add_spin(fin_form, "shipping_fee", "运费", self.item.get("shipping_fee", 0))
        self._add_spin(fin_form, "misc_fee", "杂费", self.item.get("misc_fee", 0))
        layout.addLayout(fin_form)

        # 包装规格
        layout.addWidget(QLabel("<b>包装规格</b>"))
        pack_form = QFormLayout()
        self._add_combo(pack_form, "packaging", "包装方式", ["1件/箱", "多件/箱", "1件多箱"], self.item.get("packaging", ""))
        self._add_line_edit(pack_form, "purchase_option_name", "采购选项/名称", self.item.get("purchase_option_name", ""))
        self._add_line_edit(pack_form, "product_detail", "产品细节", self.item.get("product_detail", ""))
        self._add_line_edit(pack_form, "carton_size", "纸箱尺寸", self.item.get("carton_size", ""))
        self._add_line_edit(pack_form, "pack_spec", "打包规格", self.item.get("pack_spec", ""))
        self._add_spin(pack_form, "carton_gross_weight", "整箱毛重", self.item.get("carton_gross_weight", 0))
        layout.addLayout(pack_form)

        # 采购/供应商 Area（锁定显示 + 按钮）
        layout.addWidget(QLabel("<b>采购/供应商信息</b>"))
        supplier_form = QFormLayout()
        self._add_readonly_line(supplier_form, "supplier_name", "工厂简称", self.item.get("supplier_name", ""))
        self._add_readonly_line(supplier_form, "shop_url", "店铺链接", self.item.get("shop_url", ""))
        self._add_readonly_line(supplier_form, "factory_code", "工厂编号", self.item.get("factory_code", ""))
        self._add_readonly_line(supplier_form, "brand", "品牌", self.item.get("brand", ""))
        self._add_readonly_spin(supplier_form, "purchase_price", "采购价格", self.item.get("purchase_price", 0))
        self._add_readonly_spin(supplier_form, "factory_deposit", "工厂订金", self.item.get("factory_deposit", 0))
        self._add_readonly_spin(supplier_form, "factory_balance", "工厂尾款", self.item.get("factory_balance", 0))
        self._add_readonly_line(supplier_form, "invoice_status", "开票情况", self.item.get("invoice_status", ""))
        layout.addLayout(supplier_form)

        btn_layout = QHBoxLayout()
        purchase_btn = QPushButton("采购 Dialog")
        purchase_btn.clicked.connect(self._open_purchase_dialog)
        btn_layout.addWidget(purchase_btn)

        self.change_supplier_btn = QPushButton("更换供应商 Dialog")
        self.change_supplier_btn.setEnabled(self.is_purchased)
        self.change_supplier_btn.setToolTip("尚未生成采购单" if not self.is_purchased else "更换供应商将重新生成采购单")
        self.change_supplier_btn.clicked.connect(self._on_change_supplier)
        btn_layout.addWidget(self.change_supplier_btn)
        layout.addLayout(btn_layout)

        # 客户回复 Area（预留接口）
        layout.addWidget(QLabel("<b>客户回复</b>"))
        self.reply_input = QTextEdit()
        self.reply_input.setPlaceholderText("输入新回复（当前仅本地记录）...")
        self.reply_input.setMaximumHeight(80)
        layout.addWidget(self.reply_input)
        add_reply_btn = QPushButton("添加回复")
        add_reply_btn.clicked.connect(self._add_reply)
        layout.addWidget(add_reply_btn)

        # 保存/取消
        btn_layout2 = QHBoxLayout()
        btn_layout2.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout2.addWidget(cancel_btn)
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet("background-color: #10b981; color: white; padding: 8px 16px; border-radius: 4px;")
        save_btn.clicked.connect(self._on_save)
        btn_layout2.addWidget(save_btn)
        layout.addLayout(btn_layout2)

        scroll.setWidget(container)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        self._apply_locks()

    def _add_line_edit(self, form, key, label, value):
        edit = QLineEdit(str(value if value is not None else ""))
        edit.setObjectName(key)
        form.addRow(label + ":", edit)
        self._editors[key] = edit

    def _add_spin(self, form, key, label, value):
        spin = QDoubleSpinBox()
        spin.setRange(0, 99999999)
        spin.setDecimals(4)
        spin.setValue(float(value or 0))
        spin.setObjectName(key)
        form.addRow(label + ":", spin)
        self._editors[key] = spin

    def _add_date(self, form, key, label, value):
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("yyyy-MM-dd")
        if value:
            from datetime import datetime
            if isinstance(value, str):
                value = datetime.strptime(value[:10], "%Y-%m-%d")
            date_edit.setDate(QDate(value.year, value.month, value.day))
        else:
            date_edit.setDate(QDate.currentDate())
        date_edit.setObjectName(key)
        form.addRow(label + ":", date_edit)
        self._editors[key] = date_edit

    def _add_combo(self, form, key, label, options, value):
        combo = QComboBox()
        combo.addItems(options)
        idx = combo.findText(str(value or ""))
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.setObjectName(key)
        form.addRow(label + ":", combo)
        self._editors[key] = combo

    def _add_image_field(self, layout):
        img_layout = QHBoxLayout()
        img_layout.addWidget(QLabel("图片:"))
        self.image_label = QLabel("无图片")
        self.image_path = self.item.get("image_url") or self.item.get("default_image_url", "")
        if self.image_path:
            self.image_label.setText(self.image_path)
        img_layout.addWidget(self.image_label)
        upload_btn = QPushButton("上传图片")
        upload_btn.clicked.connect(self._upload_image)
        img_layout.addWidget(upload_btn)
        clear_btn = QPushButton("清除图片")
        clear_btn.clicked.connect(self._clear_image)
        img_layout.addWidget(clear_btn)
        layout.addLayout(img_layout)
        self._editors["image_url"] = self  # 占位，图片单独处理

    def _add_readonly_line(self, form, key, label, value):
        edit = QLineEdit(str(value if value is not None else ""))
        edit.setReadOnly(True)
        edit.setStyleSheet("background-color: #f3f4f6;")
        edit.setObjectName(key)
        form.addRow(label + ":", edit)
        self._editors[key] = edit

    def _add_readonly_spin(self, form, key, label, value):
        spin = QDoubleSpinBox()
        spin.setRange(0, 99999999)
        spin.setDecimals(4)
        spin.setValue(float(value or 0))
        spin.setReadOnly(True)
        spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        spin.setStyleSheet("background-color: #f3f4f6;")
        spin.setObjectName(key)
        form.addRow(label + ":", spin)
        self._editors[key] = spin

    def _apply_locks(self):
        # 已转正式 PI：产品基本信息锁定
        if self.has_formal:
            for key in ["customer_code", "oe_number", "remark", "product_name", "customer_model", "product_feature", "quantity"]:
                editor = self._editors.get(key)
                if editor:
                    editor.setEnabled(False)
        # 已采购：包装规格 + 数量 + 日期锁定
        if self.is_purchased:
            for key in ["quantity", "delivery_date", "packaging", "purchase_option_name", "product_detail", "carton_size", "pack_spec", "carton_gross_weight"]:
                editor = self._editors.get(key)
                if editor:
                    editor.setEnabled(False)

    def _apply_focus(self):
        if self.focus_column is None:
            return
        key = self.COLUMN_TO_FIELD.get(self.focus_column)
        if not key:
            return
        editor = self._editors.get(key)
        if not editor:
            return
        editor.setStyleSheet("border: 2px solid #f59e0b; background-color: #fffbeb;")
        editor.setFocus()
        # 下拉框展开、日期选择器弹出
        if isinstance(editor, QComboBox):
            editor.showPopup()
        elif isinstance(editor, QDateEdit):
            editor.calendarWidget().showSelectedDate()

    def _upload_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return
        if self.api_client:
            try:
                url = self.api_client.upload_image(path, product_id=self.item.get("product_id"))
                self.image_path = url
                self.image_label.setText(url)
            except Exception as e:
                QMessageBox.warning(self, "上传失败", str(e))
        else:
            self.image_path = path
            self.image_label.setText(path)

    def _clear_image(self):
        self.image_path = ""
        self.image_label.setText("无图片")

    def _open_purchase_dialog(self):
        # 调用外部传入的回调或信号
        if hasattr(self.parent(), "open_purchase_dialog_for_item"):
            self.parent().open_purchase_dialog_for_item(self.item)

    def _on_change_supplier(self):
        reply = QMessageBox.question(
            self,
            "确认更换供应商",
            "确定要更换供应商吗？当前采购单将被取消并重新生成。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from widgets.supplier_change_dialog import SupplierChangeDialog
        dlg = SupplierChangeDialog(self.item, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if self.api_client:
                try:
                    self.api_client.change_supplier(self.item["id"], data)
                    QMessageBox.information(self, "成功", "供应商已更换，采购单已重新生成")
                    self.accept()
                except Exception as e:
                    QMessageBox.warning(self, "失败", str(e))

    def _add_reply(self):
        text = self.reply_input.toPlainText().strip()
        if not text:
            return
        # 预留接口：本地记录
        self.item.setdefault("customer_replies", []).append(text)
        self.reply_input.clear()
        QMessageBox.information(self, "提示", "回复已记录（客户回复接口尚未接入后端）")

    def _on_save(self):
        result = {}
        for key, editor in self._editors.items():
            if key == "image_url":
                continue
            if isinstance(editor, QLineEdit):
                result[key] = editor.text()
            elif isinstance(editor, QDoubleSpinBox):
                result[key] = editor.value()
            elif isinstance(editor, QComboBox):
                result[key] = editor.currentText()
            elif isinstance(editor, QDateEdit):
                result[key] = editor.date().toString("yyyy-MM-dd")
        result["image_url"] = self.image_path
        self.item.update(result)
        self.result_data = result
        self.accept()

    def get_data(self):
        return getattr(self, "result_data", {})
```

- [ ] **步骤 2：语法检查**

```bash
cd e:\AI\TraeProject\PI-Manager-System\client
python -m py_compile widgets/product_item_edit_dialog.py
```

预期：无错误。

- [ ] **步骤 3：Commit**

```bash
git add client/widgets/product_item_edit_dialog.py
git commit -m "feat(client): rewrite ProductItemEditDialog with full fields and locking"
```

---

## 任务 7：创建 `PurchaseSnapshotDialog`

**文件：**
- 创建：`client/widgets/purchase_snapshot_dialog.py`

- [ ] **步骤 1：实现只读快照 Dialog**

```python
# -*- coding: utf-8 -*-
"""采购快照对话框"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFormLayout
from PySide6.QtCore import Qt


class PurchaseSnapshotDialog(QDialog):
    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("采购快照")
        self.setMinimumSize(500, 400)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        fields = [
            ("工厂简称", "supplier_name"),
            ("店铺链接", "shop_url"),
            ("工厂编号", "factory_code"),
            ("品牌", "brand"),
            ("采购价格", "purchase_price"),
            ("工厂订金", "factory_deposit"),
            ("工厂尾款", "factory_balance"),
            ("开票情况", "invoice_status"),
            ("采购单状态", "storage_status"),
            ("已采购数量", "purchase_quantity"),
            ("已入库数量", "stocked_qty"),
        ]

        for label, key in fields:
            value = self.item.get(key, "")
            if isinstance(value, (int, float)):
                value = str(value)
            form.addRow(label + ":", QLabel(value or "-"))

        layout.addLayout(form)
        btn = QPushButton("关闭")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
```

- [ ] **步骤 2：语法检查**

```bash
python -m py_compile widgets/purchase_snapshot_dialog.py
```

预期：无错误。

- [ ] **步骤 3：Commit**

```bash
git add client/widgets/purchase_snapshot_dialog.py
git commit -m "feat(client): add PurchaseSnapshotDialog"
```

---

## 任务 8：扩展 `OrderDetailPanel`

**文件：**
- 修改：`client/widgets/order_summary/order_detail_panel.py`

### 8.1 设置可编辑列与失焦保存

- [ ] **步骤 1：修改 `_create_table` 启用编辑**

将：

```python
table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
```

改为：

```python
# 简单字段列支持双击编辑
table.setEditTriggers(
    QAbstractItemView.EditTrigger.DoubleClicked
    | QAbstractItemView.EditTrigger.EditKeyPressed
)
```

- [ ] **步骤 2：连接 `cellChanged` 信号实现失焦保存**

在 `_init_ui` 中新增：

```python
self._table.cellChanged.connect(self._on_cell_changed)
self._pending_cell_save = None
```

新增方法：

```python
def _on_cell_changed(self, row, column):
    """表格内联编辑：失焦自动保存"""
    if column not in (10, 13, 14, 18, 19):
        return
    item = self.get_item_at_row(row)
    if not item:
        return
    new_value = self._table.item(row, column).text()
    field_map = {
        10: "unit_price",
        13: "customer_prepayment",
        14: "remaining_payment",
        18: "shipping_fee",
        19: "misc_fee",
    }
    field = field_map[column]
    try:
        num_value = float(new_value)
    except ValueError:
        QMessageBox.warning(self, "输入错误", f"{field} 必须是数字")
        self.show_order_detail(self._current_order, self._current_items)
        return

    self._pending_cell_save = (row, column, item["id"], field, num_value, self._table.item(row, column).text())

    # 使用 QTimer 确保失焦后再保存
    from PySide6.QtCore import QTimer
    QTimer.singleShot(100, self._do_cell_save)

def _do_cell_save(self):
    if not self._pending_cell_save:
        return
    row, column, item_id, field, value, old_text = self._pending_cell_save
    self._pending_cell_save = None
    try:
        self.api_client.update_pi_item(item_id, {field: value})
        # 更新本地缓存
        item = self.get_item_at_row(row)
        if item:
            item[field] = value
        self._update_summary_row()
        self._update_status_indicator(self._current_items)
    except Exception as e:
        QMessageBox.warning(self, "保存失败", str(e))
        self.show_order_detail(self._current_order, self._current_items)
```

- [ ] **步骤 3：控制哪些单元格可编辑**

在 `_fill_excel_41_columns` 填充单元格时，对可编辑列设置 `Qt.ItemIsEditable`：

```python
editable_columns = {10, 13, 14, 18, 19}
for col in range(ORDER_DETAIL_COLUMN_COUNT):
    # ... 原有创建 QTableWidgetItem 逻辑 ...
    if col in editable_columns:
        cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
    else:
        cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
```

### 8.2 双击打开编辑 Dialog

- [ ] **步骤 4：修改 `_on_cell_double_clicked`**

```python
@Slot(int, int)
def _on_cell_double_clicked(self, row, column):
    """双击事件：可编辑列进入内联编辑；2-9/23/包装规格列打开编辑产品 Dialog"""
    if column in (10, 13, 14, 18, 19):
        # 让表格默认行为处理内联编辑
        return
    if column in (
        2, 3, 4, 5, 6, 7, 8, 9,  # 基础信息
        10, 13, 14, 18, 19,       # 财务（也可通过 Dialog 编辑）
        23,                       # 交货日期
        29, 30, 31, 33, 34, 37,   # 包装规格
    ):
        self.editProductRequested.emit(row, column)
```

- [ ] **步骤 5：新增信号**

在 `OrderDetailPanel` 顶部新增信号：

```python
editProductRequested = Signal(int, int)          # 行索引, 列号
changeSupplierRequested = Signal(int)            # 行索引
purchaseSnapshotRequested = Signal(int)          # 行索引
openShopUrlRequested = Signal(int)               # 行索引
```

### 8.3 扩展右键菜单

- [ ] **步骤 6：在 `_build_context_menu` 中添加菜单项**

在 `删除商品` 之后、`缺货标记` 之前插入：

```python
menu.addSeparator()
edit_action = menu.addAction("编辑产品")
edit_action.triggered.connect(lambda: self.editProductRequested.emit(row, -1))

change_supplier_action = menu.addAction("更换供应商")
# 只有已采购才允许更换
has_po = bool(self._get_item_purchase_order_id(item))
change_supplier_action.setEnabled(has_po)
change_supplier_action.setToolTip("尚未生成采购单" if not has_po else "更换供应商将重新生成采购单")
change_supplier_action.triggered.connect(lambda: self.changeSupplierRequested.emit(row))

snapshot_action = menu.addAction("采购快照")
snapshot_action.triggered.connect(lambda: self.purchaseSnapshotRequested.emit(row))

open_url_action = menu.addAction("访问店铺网站")
shop_url = item.get("shop_url", "")
open_url_action.setEnabled(bool(shop_url))
open_url_action.triggered.connect(lambda: self.openShopUrlRequested.emit(row))
```

新增辅助方法：

```python
def _get_item_purchase_order_id(self, item: dict) -> int | None:
    """检查 item 是否有关联的采购单（通过 purchase_order_id 或 storage_status 推断）"""
    return item.get("purchase_order_id") or item.get("po_id")
```

### 8.4 提供打开 Dialog 的公共方法

- [ ] **步骤 7：新增 `open_edit_dialog` 方法**

```python
def open_edit_dialog(self, row: int, focus_column: int = None):
    """外部调用：打开编辑产品 Dialog"""
    item = self.get_item_at_row(row)
    if not item:
        return
    from widgets.product_item_edit_dialog import ProductItemEditDialog
    dlg = ProductItemEditDialog(
        item,
        api_client=self.api_client,
        focus_column=focus_column,
        has_formal=self._has_formal_record,
        is_purchased=self._is_item_purchased(item),
        parent=self,
    )
    if dlg.exec() == QDialog.DialogCode.Accepted:
        data = dlg.get_data()
        if data:
            try:
                self.api_client.update_pi_item(item["id"], data)
                # 刷新当前行
                self.show_order_detail(self._current_order, self._current_items)
            except Exception as e:
                QMessageBox.warning(self, "保存失败", str(e))
```

- [ ] **步骤 8：Commit**

```bash
git add client/widgets/order_summary/order_detail_panel.py
git commit -m "feat(client): extend order detail panel with inline edit and context menu"
```

---

## 任务 9：在 `main.py` 连接信号

**文件：**
- 修改：`client/main.py`

- [ ] **步骤 1：找到订单详情面板初始化位置**

搜索 `self.order_detail_panel = OrderDetailPanel(...)` 附近代码。

- [ ] **步骤 2：连接新增信号**

```python
self.order_detail_panel.editProductRequested.connect(self._on_edit_product)
self.order_detail_panel.changeSupplierRequested.connect(self._on_change_supplier_from_menu)
self.order_detail_panel.purchaseSnapshotRequested.connect(self._on_purchase_snapshot)
self.order_detail_panel.openShopUrlRequested.connect(self._on_open_shop_url)
```

- [ ] **步骤 3：实现槽函数**

```python
def _on_edit_product(self, row, column):
    self.order_detail_panel.open_edit_dialog(row, focus_column=column if column >= 0 else None)

def _on_change_supplier_from_menu(self, row):
    item = self.order_detail_panel.get_item_at_row(row)
    if not item:
        return
    from widgets.supplier_change_dialog import SupplierChangeDialog
    dlg = SupplierChangeDialog(item, parent=self)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        data = dlg.get_data()
        try:
            self.api_client.change_supplier(item["id"], data)
            QMessageBox.information(self, "成功", "供应商已更换，采购单已重新生成")
            self.order_detail_panel.show_order_detail(
                self.order_detail_panel._current_order,
                self.order_detail_panel._current_items,
            )
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

def _on_purchase_snapshot(self, row):
    item = self.order_detail_panel.get_item_at_row(row)
    if not item:
        return
    from widgets.purchase_snapshot_dialog import PurchaseSnapshotDialog
    dlg = PurchaseSnapshotDialog(item, parent=self)
    dlg.exec()

def _on_open_shop_url(self, row):
    item = self.order_detail_panel.get_item_at_row(row)
    if not item:
        return
    url = item.get("shop_url", "")
    if not url:
        QMessageBox.information(self, "提示", "店铺链接为空")
        return
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtCore import QUrl
    QDesktopServices.openUrl(QUrl(url))
```

- [ ] **步骤 4：语法检查**

```bash
cd e:\AI\TraeProject\PI-Manager-System\client
python -m py_compile main.py
```

预期：无错误。

- [ ] **步骤 5：Commit**

```bash
git add client/main.py
git commit -m "feat(client): wire up edit/change-supplier/snapshot context menu in main window"
```

---

## 任务 10：集成测试与自检

- [ ] **步骤 1：后端启动测试**

```bash
cd e:\AI\TraeProject\PI-Manager-System\backend
python -c "from main import app; print('backend ok')"
```

预期：输出 `backend ok`，无导入错误。

- [ ] **步骤 2：前端编译测试**

```bash
cd e:\AI\TraeProject\PI-Manager-System\client
python -m py_compile main.py
python -m py_compile widgets/product_item_edit_dialog.py
python -m py_compile widgets/supplier_change_dialog.py
python -m py_compile widgets/purchase_snapshot_dialog.py
python -m py_compile widgets/order_summary/order_detail_panel.py
```

预期：全部无错误。

- [ ] **步骤 3：API 集成测试**

```python
def test_update_pi_item_full_fields(client):
    res = client.put("/api/pi/items/1", json={
        "unit_price": 100,
        "shipping_fee": 10,
        "packaging": "1件/箱",
        "delivery_date": "2026-08-15",
    })
    assert res.status_code == 200
    assert res.json()["success"] is True
```

运行：

```bash
pytest tests/routers/test_pi.py::test_update_pi_item_full_fields -v
```

预期：PASS。

- [ ] **步骤 4：规格覆盖度自检**

逐条核对规格中的需求是否已覆盖：

| 规格需求 | 实现任务 |
|---|---|
| 简单字段表格内联编辑 | 任务 8.1 |
| 双击 2-9/23/包装规格打开编辑 Dialog | 任务 8.2 |
| 编辑 Dialog 768×1280 显示所有字段 | 任务 6 |
| 采购/供应商字段锁定 + 按钮入口 | 任务 6 |
| 无采购单时更换供应商按钮禁用 | 任务 6、8.3 |
| 有采购单时三次确认更换供应商 | 任务 6、5 |
| 转为正式 PI 后产品基本信息锁定 | 任务 6 |
| 右键菜单"采购快照" | 任务 7、8.3 |
| 右键菜单"访问店铺网站" | 任务 8.3、9 |
| 高亮触发列对应字段 | 任务 6 |
| 后端字段扩展 | 任务 1 |
| 更换供应商重新生成采购单 | 任务 2、3 |

- [ ] **步骤 5：最终 Commit**

```bash
git add docs/superpowers/plans/2026-07-02-order-product-edit-plan.md
git commit -m "docs: complete implementation plan for order product edit"
```

---

## 执行选项

计划已完成并保存到 `docs/superpowers/plans/2026-07-02-order-product-edit-plan.md`。两种执行方式：

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代。

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点供审查。

选哪种方式？









