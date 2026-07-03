# 客户产品编号与系统编号重构实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现「临时系统编号 + 类目锁定后转正式编号」以及「客户产品编号自动生成、一次修改、保存确认」的逻辑。

**架构：** 后端在客户产品创建时强制生成 `TMP-{customer_code}-{seq}` 临时系统编号；更新时检测 `category_id` 从空到非空且当前为临时编号，自动替换为正式编号。前端 Dialog 打开时按 `{customer_code}{customer_model}` 自动填充客户产品编号，提供一次修改机会，保存前二次确认。

> **技术栈：** FastAPI + SQLAlchemy + PySide6

---

## 文件清单

- **创建：**
  - `tests/conftest.py`：提供 `db` session 和 `customer_factory` fixture。
  - `tests/backend/crud/test_customer_product_numbering.py`：后端编号逻辑单元测试。
- **修改：**
  - `backend/crud/customer_product.py`：新增临时系统编号生成函数，修改创建/更新逻辑。
  - `backend/schemas/customer_product.py`：在响应模型中增加 `is_system_code_temp` 派生字段。
  - `backend/routers/customer_product.py`：在 `_build_response` 中填充 `is_system_code_temp`。
  - `client/widgets/customer_product_dialog.py`：系统编号显示、客户产品编号自动生成与修改锁定、保存确认。
- **测试：**
  - `tests/backend/crud/test_customer_product_numbering.py`：新增后端编号逻辑单元测试。

---

### 任务 0：创建后端测试基础设施

**文件：**
- 创建：`tests/conftest.py`

- [ ] **步骤 1：创建 `tests/conftest.py`**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from models import Base
from models.customer_product import PrdCustomerProduct
from models.customer import CrmCustomer


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def customer_factory(db):
    def _make(customer_code="TEST"):
        customer = CrmCustomer(
            customer_code=customer_code,
            customer_name=f"Customer {customer_code}",
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer
    return _make
```

- [ ] **步骤 2：验证 pytest 能发现 fixture**

运行：`pytest tests/conftest.py --collect-only`
预期：无报错，显示 0 个测试（仅验证导入和 fixture 注册）。

- [ ] **步骤 3：创建 Python 包标记文件**

创建空文件：
- `tests/backend/__init__.py`
- `tests/backend/crud/__init__.py`

运行：

```bash
New-Item -ItemType File -Path tests/backend/__init__.py -Force
New-Item -ItemType File -Path tests/backend/crud/__init__.py -Force
```

- [ ] **步骤 4：Commit**

```bash
git add tests/conftest.py tests/backend/__init__.py tests/backend/crud/__init__.py
git commit -m "test: add backend test fixtures"
```

---

### 任务 1：后端新增临时系统编号生成函数

**文件：**
- 修改：`backend/crud/customer_product.py:140`
- 测试：`tests/backend/crud/test_customer_product_numbering.py`

- [ ] **步骤 1：编写失败的测试**

```python
from crud.customer_product import _generate_temp_system_code


def test_generate_temp_system_code(db, customer_factory):
    customer = customer_factory(customer_code="A01")
    code1 = _generate_temp_system_code(db, customer.customer_code)
    code2 = _generate_temp_system_code(db, customer.customer_code)
    assert code1.startswith("TMP-A01-")
    assert code2.startswith("TMP-A01-")
    assert code1 != code2
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/backend/crud/test_customer_product_numbering.py::test_generate_temp_system_code -v`
预期：FAIL，`NameError: name '_generate_temp_system_code' is not defined`

- [ ] **步骤 3：实现 `_generate_temp_system_code`**

在 `backend/crud/customer_product.py` 的 `_generate_system_code_with_retry` 函数之后插入：

```python
def _generate_temp_system_code(db: Session, customer_code: str) -> str:
    """
    生成临时系统编号。
    格式: TMP-{customer_code}-{6位十进制序号}
    示例: TMP-A01-000001
    """
    prefix = f"TMP-{customer_code}-"
    existing = db.query(PrdCustomerProduct).filter(
        PrdCustomerProduct.system_code.like(f"{prefix}%")
    ).all()

    max_seq = 0
    for p in existing:
        if p.system_code and len(p.system_code) > len(prefix):
            seq_str = p.system_code[len(prefix):]
            try:
                seq = int(seq_str)
                if seq > max_seq:
                    max_seq = seq
            except ValueError:
                pass

    new_seq = max_seq + 1
    return f"{prefix}{new_seq:06d}"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/backend/crud/test_customer_product_numbering.py::test_generate_temp_system_code -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add tests/backend/crud/test_customer_product_numbering.py backend/crud/customer_product.py
git commit -m "feat: add temp system code generator for customer products"
```

---

### 任务 2：后端创建客户产品时强制使用临时系统编号

**文件：**
- 修改：`backend/crud/customer_product.py:140-150`
- 测试：`tests/backend/crud/test_customer_product_numbering.py`

- [ ] **步骤 1：编写失败的测试**

```python
from schemas.customer_product import CustomerProductCreate
from crud.customer_product import create_customer_product


def test_create_customer_product_uses_temp_code(db, customer_factory):
    customer = customer_factory(customer_code="B02")
    data = CustomerProductCreate(customer_id=customer.id, product_name="测试产品")
    cp = create_customer_product(db, data)
    assert cp.system_code.startswith("TMP-B02-")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/backend/crud/test_customer_product_numbering.py::test_create_customer_product_uses_temp_code -v`
预期：FAIL，assertion 失败（当前生成的是正式编号）

- [ ] **步骤 3：修改 `create_customer_product`**

将 `backend/crud/customer_product.py:142-143`：

```python
    # 生成系统产品编号
    system_code = _generate_system_code(db, data.customer_id, data.category_id, dept_code)
```

替换为：

```python
    # 生成临时系统产品编号（类目锁定后重新生成正式编号）
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == data.customer_id).first()
    customer_code = customer.customer_code if customer else None
    system_code = _generate_temp_system_code(db, customer_code) if customer_code else None
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/backend/crud/test_customer_product_numbering.py::test_create_customer_product_uses_temp_code -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add backend/crud/customer_product.py tests/backend/crud/test_customer_product_numbering.py
git commit -m "feat: force temp system code on customer product creation"
```

---

### 任务 3：后端更新时检测类目锁定并生成正式系统编号

**文件：**
- 修改：`backend/crud/customer_product.py:289-306`
- 测试：`tests/backend/crud/test_customer_product_numbering.py`

- [ ] **步骤 1：编写失败的测试**

```python
from schemas.customer_product import CustomerProductUpdate
from crud.customer_product import create_customer_product, update_customer_product


def test_update_converts_temp_to_formal_code(db, customer_factory):
    customer = customer_factory(customer_code="C03")
    cp = create_customer_product(db, CustomerProductCreate(customer_id=customer.id))
    assert cp.system_code.startswith("TMP-C03-")

    updated = update_customer_product(
        db,
        cp.id,
        CustomerProductUpdate(category_id="01")
    )
    assert updated is not None
    assert not updated.system_code.startswith("TMP-")
    assert updated.category_id == "01"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/backend/crud/test_customer_product_numbering.py::test_update_converts_temp_to_formal_code -v`
预期：FAIL，`system_code` 仍为临时编号

- [ ] **步骤 3：修改 `update_customer_product`**

将 `backend/crud/customer_product.py:289-306` 更新逻辑改为：

```python
def update_customer_product(db: Session, product_id: int, data: CustomerProductUpdate) -> Optional[PrdCustomerProduct]:
    """更新客户产品"""
    customer_product = get_customer_product(db, product_id)
    if not customer_product:
        return None

    update_data = data.model_dump(exclude_unset=True)

    # 检测类目从空到非空的首次锁定，临时编号转正式编号
    old_category_id = customer_product.category_id
    new_category_id = update_data.get('category_id')
    if (not old_category_id and new_category_id
            and customer_product.system_code
            and customer_product.system_code.startswith("TMP-")):
        formal_code = _generate_system_code_with_retry(
            db, customer_product.customer_id, new_category_id, 'S'
        )
        if formal_code:
            customer_product.system_code = formal_code
        # 若生成失败，保持临时编号，继续后续更新

    # 处理副图JSON转换
    if 'sub_images' in update_data and update_data['sub_images'] is not None:
        update_data['sub_images'] = json.dumps(update_data['sub_images'])

    for key, value in update_data.items():
        setattr(customer_product, key, value)

    db.commit()
    db.refresh(customer_product)
    return customer_product
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/backend/crud/test_customer_product_numbering.py::test_update_converts_temp_to_formal_code -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add backend/crud/customer_product.py tests/backend/crud/test_customer_product_numbering.py
git commit -m "feat: convert temp system code to formal on category lock"
```

---

### 任务 4：后端响应中暴露临时系统编号状态

**文件：**
- 修改：`backend/schemas/customer_product.py:97-131`
- 修改：`backend/routers/customer_product.py:88-129`
- 测试：`tests/backend/crud/test_customer_product_numbering.py`

- [ ] **步骤 1：编写失败的测试**

```python
from routers.customer_product import _build_response


def test_response_includes_temp_flag(db, customer_factory):
    customer = customer_factory(customer_code="D04")
    cp = create_customer_product(db, CustomerProductCreate(customer_id=customer.id))
    resp = _build_response(cp, db)
    assert resp.is_system_code_temp is True

    update_customer_product(db, cp.id, CustomerProductUpdate(category_id="01"))
    resp2 = _build_response(get_customer_product(db, cp.id), db)
    assert resp2.is_system_code_temp is False
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/backend/crud/test_customer_product_numbering.py::test_response_includes_temp_flag -v`
预期：FAIL，`AttributeError: 'CustomerProductResponse' object has no attribute 'is_system_code_temp'`

- [ ] **步骤 3：修改响应 Schema 和构建函数**

在 `backend/schemas/customer_product.py` 的 `CustomerProductResponse` 中新增字段：

```python
    is_system_code_temp: bool = False  # 是否为临时系统编号
```

在 `backend/routers/customer_product.py` 的 `_build_response` 中，返回 `CustomerProductResponse` 时增加：

```python
        is_system_code_temp=(
            customer_product.system_code is not None
            and customer_product.system_code.startswith("TMP-")
        ),
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/backend/crud/test_customer_product_numbering.py::test_response_includes_temp_flag -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add backend/schemas/customer_product.py backend/routers/customer_product.py tests/backend/crud/test_customer_product_numbering.py
git commit -m "feat: expose is_system_code_temp in customer product response"
```

---

### 任务 5：前端 Dialog 显示系统编号与临时状态标签

**文件：**
- 修改：`client/widgets/customer_product_dialog.py:496-582`（基础信息表单区）

- [ ] **步骤 1：在基础信息区添加系统编号只读行**

在 `init_ui` 中创建 `basic_layout`（QFormLayout）后，在「产品名称」行前插入：

```python
        # 系统编号（只读，带临时/正式标签）
        self.system_code_label = QLabel("")
        self.system_code_label.setStyleSheet("font-weight: bold;")
        basic_layout.addRow("系统编号:", self.system_code_label)
```

- [ ] **步骤 2：在 `init_ui` 中填充系统编号标签**

在 `init_ui` 中加载完基本信息字段后（`basic_group.setLayout(basic_layout)` 之前）增加：

```python
        system_code = self.product.get('system_code', '')
        is_temp = self.product.get('is_system_code_temp', False)
        if is_temp:
            self.system_code_label.setText(f"{system_code} <span style='color:#f59e0b;'>[临时]</span>")
        else:
            self.system_code_label.setText(f"{system_code} <span style='color:#10b981;'>[正式]</span>")
```

- [ ] **步骤 3：py_compile 验证**

运行：`python -m py_compile client/widgets/customer_product_dialog.py`
预期：无错误

- [ ] **步骤 4：Commit**

```bash
git add client/widgets/customer_product_dialog.py
git commit -m "feat(ui): display system code and temp/formal status in customer product dialog"
```

---

### 任务 6：前端 Dialog 自动填充客户产品编号并支持一次修改

**文件：**
- 修改：`client/widgets/customer_product_dialog.py:638-665`（编号管理区）

- [ ] **步骤 1：重构编号管理区 UI**

将原 `codes_group` 中的按钮区（`add_code_btn` 等）上方新增「客户产品编号」只读输入框和「修改编号」按钮：

```python
        # 主编号显示与修改
        primary_code_layout = QHBoxLayout()
        self.primary_code_edit = QLineEdit()
        self.primary_code_edit.setReadOnly(True)
        self.primary_code_edit.setPlaceholderText("未生成（缺少客户型号）")
        primary_code_layout.addWidget(self.primary_code_edit, stretch=1)

        self.modify_code_btn = QPushButton("修改编号")
        self.modify_code_btn.setToolTip("只能修改一次")
        self.modify_code_btn.clicked.connect(self._on_modify_primary_code)
        primary_code_layout.addWidget(self.modify_code_btn)
        codes_layout.addLayout(primary_code_layout)
```

- [ ] **步骤 2：在 `_load_data_async` 中自动填充主编号**

找到 `_load_data_async` 中加载 codes 的位置（`self.codes = codes_resp` 之后），在 `self.init_ui()` 调用前增加：

```python
        self._auto_fill_primary_code()
        self._update_modify_code_button_state()
```

新增方法：

```python
    def _auto_fill_primary_code(self):
        customer_code = self._get_customer_code()
        customer_model = self.model_input.text().strip()

        # 若已存在主编号，直接显示，不再自动生成
        primary = next((c for c in self.codes if c.get('is_primary')), None)
        if primary:
            self.primary_code_edit.setText(primary.get('product_code', ''))
            return

        if not customer_code or not customer_model:
            self.primary_code_edit.setPlaceholderText("未生成（缺少客户型号）")
            self.primary_code_edit.clear()
            return

        generated = f"{customer_code}{customer_model}"
        self.primary_code_edit.setText(generated)
```

其中 `_get_customer_code` 已在当前文件中实现，根据客户下拉框返回客户编号。

- [ ] **步骤 3：实现修改编号流程**

新增方法：

```python
    def _on_modify_primary_code(self):
        if not self.primary_code_edit.isReadOnly():
            # 当前处于编辑状态，点击即确认
            new_code = self.primary_code_edit.text().strip()
            if not new_code:
                QMessageBox.warning(self, "提示", "客户产品编号不能为空")
                return

            reply = QMessageBox.question(
                self,
                "确认客户产品编号",
                f"确认使用「{new_code}」作为客户产品编号？\n确认后将不可再次修改。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            self.primary_code_edit.setReadOnly(True)
            self.modify_code_btn.setText("已锁定")
            self.modify_code_btn.setEnabled(False)
            self._pending_primary_code = new_code
        else:
            # 进入编辑状态，允许修改一次
            self.primary_code_edit.setReadOnly(False)
            self.modify_code_btn.setText("确认")
            self.primary_code_edit.setFocus()
```

- [ ] **步骤 4：控制按钮状态**

新增方法：

```python
    def _update_modify_code_button_state(self):
        has_primary_saved = any(c.get('is_primary') for c in self.codes)
        if has_primary_saved:
            self.modify_code_btn.setText("已锁定")
            self.modify_code_btn.setEnabled(False)
            self.primary_code_edit.setReadOnly(True)
        else:
            self.modify_code_btn.setText("修改编号")
            self.modify_code_btn.setEnabled(True)
            self.primary_code_edit.setReadOnly(True)
```

- [ ] **步骤 5：py_compile 验证**

运行：`python -m py_compile client/widgets/customer_product_dialog.py`
预期：无错误

- [ ] **步骤 6：Commit**

```bash
git add client/widgets/customer_product_dialog.py
git commit -m "feat(ui): auto-fill and one-time edit of primary customer product code"
```

---

### 任务 7：前端保存时二次确认客户产品编号

**文件：**
- 修改：`client/widgets/customer_product_dialog.py:1029-1107`（`save` 方法）

- [ ] **步骤 1：在保存逻辑中加入确认并写入 codes**

找到 `save` 方法，在 `data = { ... }` 组装之后、API 调用之前增加：

```python
        # 客户产品编号保存确认
        primary_code = self.primary_code_edit.text().strip()
        has_primary_saved = any(c.get('is_primary') for c in self.codes)
        if primary_code and not has_primary_saved:
            reply = QMessageBox.question(
                self,
                "确认保存",
                f"是否将「{primary_code}」保存为客户产品主编号？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            # 以当前 primary_code 作为唯一主编号写入 self.codes
            self.codes = [{
                'product_code': primary_code,
                'is_primary': True,
                'remark': None
            }]
```

- [ ] **步骤 2：确保新增模式下也能保存主编号**

在 `save` 方法的 `else` 分支（新增模式，`resp = self.api_client.post("/customer-products", data)`）之后、显示成功弹窗之前，增加与编辑模式相同的 codes 同步逻辑：

```python
                # 同步新增的主编号
                product_id = resp.get('id')
                for c in self.codes:
                    if not c.get('id') and product_id:
                        self.api_client.post(f"/customer-products/{product_id}/codes", {
                            'product_code': c.get('product_code'),
                            'is_primary': c.get('is_primary', False)
                        })
```

- [ ] **步骤 3：py_compile 验证**

运行：`python -m py_compile client/widgets/customer_product_dialog.py`
预期：无错误

- [ ] **步骤 4：Commit**

```bash
git add client/widgets/customer_product_dialog.py
git commit -m "feat(ui): confirm and persist primary customer product code on save"
```

---

### 任务 8：后端临时编号生成支持并发唯一性

**文件：**
- 修改：`backend/crud/customer_product.py`（新增函数内部）
- 测试：`tests/backend/crud/test_customer_product_numbering.py`

- [ ] **步骤 1：为 `_generate_temp_system_code` 添加重试**

将任务 1 中实现的 `_generate_temp_system_code` 改为带重试的版本：

```python
def _generate_temp_system_code(db: Session, customer_code: str, max_retries: int = 10) -> str:
    """
    生成临时系统编号（带重试，防止并发冲突）。
    格式: TMP-{customer_code}-{6位十进制序号}
    """
    prefix = f"TMP-{customer_code}-"

    for attempt in range(max_retries):
        existing = db.query(PrdCustomerProduct).filter(
            PrdCustomerProduct.system_code.like(f"{prefix}%")
        ).all()

        max_seq = 0
        for p in existing:
            if p.system_code and len(p.system_code) > len(prefix):
                seq_str = p.system_code[len(prefix):]
                try:
                    seq = int(seq_str)
                    if seq > max_seq:
                        max_seq = seq
                except ValueError:
                    pass

        new_seq = max_seq + 1 + attempt
        candidate = f"{prefix}{new_seq:06d}"

        conflict = db.query(PrdCustomerProduct).filter(
            PrdCustomerProduct.system_code == candidate
        ).first()
        if not conflict:
            return candidate

    # 兜底：使用时间戳
    from datetime import datetime
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
```

- [ ] **步骤 2：运行测试验证**

运行：`pytest tests/backend/crud/test_customer_product_numbering.py -v`
预期：全部 PASS

- [ ] **步骤 3：Commit**

```bash
git add backend/crud/customer_product.py
git commit -m "feat: add retry to temp system code generation"
```

---

### 任务 9：集成测试与冒烟验证

**文件：**
- 运行：无文件修改，仅执行命令

- [ ] **步骤 1：后端导入/路由冒烟测试**

运行：

```bash
cd backend
python -c "from main import app; print('OK')"
```

预期：输出 `OK`

- [ ] **步骤 2：后端 CRUD 测试全量运行**

运行：`pytest tests/backend/crud/test_customer_product_numbering.py -v`
预期：全部 PASS

- [ ] **步骤 3：前端 py_compile**

运行：`python -m py_compile client/widgets/customer_product_dialog.py`
预期：无错误

- [ ] **步骤 4：Commit（如仅测试结果变更）**

若无需代码改动，跳过 commit。

---

## 自检

- **规格覆盖度：** 临时编号生成（任务 1、2、8）、类目锁定转正式（任务 3）、响应字段（任务 4）、前端显示（任务 5）、前端自动生成与修改锁定（任务 6）、保存确认（任务 7）、集成验证（任务 9）均已覆盖。
- **占位符扫描：** 无 TODO、待定或模糊描述。
- **类型一致性：** `_generate_temp_system_code`、`_generate_system_code_with_retry`、响应模型字段名在各任务中一致。
