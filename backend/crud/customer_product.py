"""
客户产品管理 CRUD
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional, Tuple
import json
from models import PrdCustomerProduct, PrdCustomerProductCode, PrdCustomerProductOE, CrmCustomer, PrdProductCategory
from schemas.customer_product import (
    CustomerProductCreate, 
    CustomerProductUpdate,
    CustomerProductCodeCreate,
    CustomerProductOECreate
)


def _generate_system_code(db: Session, customer_id: int, category_id: str = None, dept_code: str = 'S') -> str:
    """
    生成系统产品编号（完整存储用）
    格式: 客户编号 + 部门编号 + 产品类别(2位) + 年份(2位) + 序号(4位36进制)
    示例: A01S01240001

    使用原子操作 + 重试机制确保唯一性
    """
    from datetime import datetime

    # 获取客户编号
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == customer_id).first()
    if not customer or not customer.customer_code:
        return None

    customer_code = customer.customer_code

    # 类别默认为 01
    category_code = category_id.zfill(2) if category_id else '01'

    # 获取年份后两位
    year_code = str(datetime.now().year)[-2:]

    # 查找最大序号
    prefix = f"{customer_code}{dept_code}{category_code}{year_code}"

    # 查找该前缀下的所有编号
    products = db.query(PrdCustomerProduct).filter(
        PrdCustomerProduct.system_code.like(f"{prefix}%")
    ).all()

    CHARSET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    max_seq = 0
    for p in products:
        if p.system_code and len(p.system_code) >= len(prefix) + 4:
            seq_str = p.system_code[len(prefix):len(prefix)+4]
            try:
                seq = int(seq_str, 36)
                if seq > max_seq:
                    max_seq = seq
            except:
                pass

    # 生成新序号（36进制）
    new_seq = max_seq + 1
    # 2026-06-23 修复 off-by-one bug：
    # 原算法 `num = new_seq; while num > 0: num -= 1; seq_str = CHARSET[num % 36] + seq_str; num //= 36`
    # 当 new_seq=1 时：num=1 → num-1=0 → CHARSET[0]='0' → 退出循环 → seq_str='0' → zfill(4)='0000'
    # 结果：max_seq=0 永远生成 '0000'，与第一条已有记录 system_code 冲突 → UNIQUE constraint failed
    # 改用 standard base36 编码（divmod 风格），new_seq=1 → '1' → '0001'
    seq_str = ''
    n = new_seq
    while n > 0:
        n, r = divmod(n, 36)
        seq_str = CHARSET[r] + seq_str
    if not seq_str:
        seq_str = '0'
    seq_str = seq_str.zfill(4)

    return f"{customer_code}{dept_code}{category_code}{year_code}{seq_str}"


def _generate_system_code_with_retry(db: Session, customer_id: int, category_id: str = None, dept_code: str = 'S', max_retries: int = 10) -> str:
    """
    生成系统产品编号（带重试机制）
    当发生冲突时，重新查询最大序号并重试
    """
    from datetime import datetime

    customer = db.query(CrmCustomer).filter(CrmCustomer.id == customer_id).first()
    if not customer or not customer.customer_code:
        return None

    customer_code = customer.customer_code
    category_code = category_id.zfill(2) if category_id else '01'
    year_code = str(datetime.now().year)[-2:]
    prefix = f"{customer_code}{dept_code}{category_code}{year_code}"

    CHARSET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    for attempt in range(max_retries):
        # 每次都重新查询最大序号（在重试时）
        products = db.query(PrdCustomerProduct).filter(
            PrdCustomerProduct.system_code.like(f"{prefix}%")
        ).all()

        max_seq = 0
        for p in products:
            if p.system_code and len(p.system_code) >= len(prefix) + 4:
                seq_str = p.system_code[len(prefix):len(prefix)+4]
                try:
                    seq = int(seq_str, 36)
                    if seq > max_seq:
                        max_seq = seq
                except:
                    pass

        # 生成新序号
        new_seq = max_seq + 1 + attempt  # 每次重试增加序号
        # 2026-06-23：与 _generate_system_code 同样的 off-by-one bug 修复
        seq_str = ''
        n = new_seq
        while n > 0:
            n, r = divmod(n, 36)
            seq_str = CHARSET[r] + seq_str
        if not seq_str:
            seq_str = '0'
        seq_str = seq_str.zfill(4)

        new_code = f"{customer_code}{dept_code}{category_code}{year_code}{seq_str}"

        # 检查是否已存在
        existing = db.query(PrdCustomerProduct).filter(
            PrdCustomerProduct.system_code == new_code
        ).first()

        if not existing:
            return new_code

    return None  # 多次重试后仍失败


def create_customer_product(db: Session, data: CustomerProductCreate, dept_code: str = 'S') -> PrdCustomerProduct:
    """创建客户产品（支持临时/正式产品，单表存储）"""
    # 生成系统产品编号
    system_code = _generate_system_code(db, data.customer_id, data.category_id, dept_code)

    # 处理副图（存储为JSON）
    sub_images_json = json.dumps(data.sub_images) if data.sub_images else None

    # Phase 2: 创建客户产品（含临时产品标志）
    is_temporary = bool(getattr(data, "is_temporary", False))
    customer_product = PrdCustomerProduct(
        customer_id=data.customer_id,
        system_code=system_code,  # 自动生成的系统编号
        product_name=data.product_name,
        customer_model=data.customer_model,
        color=data.color,
        customer_remark=data.customer_remark,
        category_id=data.category_id,
        price_usd=data.price_usd,
        price_rmb=data.price_rmb,
        detail_desc=data.detail_desc,
        brand=data.brand,
        specifications=data.specifications,
        image_url=data.image_url,
        sub_images=sub_images_json,
        carton_length_cm=data.carton_length_cm,
        carton_width_cm=data.carton_width_cm,
        carton_height_cm=data.carton_height_cm,
        units_per_carton=data.units_per_carton,
        gross_weight_kg=data.gross_weight_kg,
        is_temporary=is_temporary,  # Phase 2: 临时产品标志
    )
    db.add(customer_product)
    db.flush()

    # 添加编号（如果有）
    if data.codes:
        for idx, code_str in enumerate(data.codes):
            code = PrdCustomerProductCode(
                customer_product_id=customer_product.id,
                product_code=code_str,
                is_primary=(idx == 0),  # 第一个设为默认主编号
            )
            db.add(code)
    
    # 添加OE号（如果有）
    if data.oes:
        for idx, oe_number in enumerate(data.oes):
            oe = PrdCustomerProductOE(
                customer_product_id=customer_product.id,
                oe_number=oe_number,
                is_primary=(idx == 0),  # 第一个设为默认主OE
            )
            db.add(oe)
    
    db.commit()
    db.refresh(customer_product)
    return customer_product


# ============================================================
# 2026-06-23 新增：导入时按 Model 幂等创建 temp
# ============================================================
def find_or_create_temp_customer_product(
    db: Session,
    customer_id: int,
    row: dict,
) -> Tuple[PrdCustomerProduct, bool]:
    """按 customer_id + customer_model 查重，命中复用、未命中新建 temp。

    用途：订单导入 / 补充商品流程中，为未匹配行静默创建临时产品。

    Args:
        customer_id: 客户 ID
        row: 单行数据，应包含以下键（均可选）：
            - customer_model / model: 客户型号（**去重键**，不参与 OE 去重）
            - oe_number: OE 号（写入 PrdCustomerProductOE 子表）
            - product_name / detail_desc: 产品名称
            - customer_remark / remark: 客户备注
            - unit_price / price_rmb: 人民币价格
            - price_usd: 美元价格

    Returns:
        (product, created) 元组。created=True 表示本次新建，False 表示命中复用。
    """
    from schemas.customer_product import CustomerProductCreate
    from models import CrmCustomer, PrdCustomerProduct, PrdCustomerProductOE
    import uuid
    from datetime import datetime

    model = (row.get('customer_model') or row.get('model') or '').strip()

    # 1. 按 customer_id + customer_model 查重（不参与 OE 去重；OE 跨类目可能重复）
    if model:
        existing = db.query(PrdCustomerProduct).filter(
            PrdCustomerProduct.customer_id == customer_id,
            PrdCustomerProduct.customer_model == model,
        ).first()
        if existing:
            # 保守策略：命中即复用，不更新任何字段
            return existing, False

    # 2. 未命中 → 新建 temp
    # 2026-06-23 修复：直接构造 PrdCustomerProduct 绕过 _generate_system_code
    # （该函数有 base36 编码 bug，已有 ME9S01260000 时重复生成同 code）
    # 这里手写 system_code：<customer_code>S<cat>YY<uuid6>，保证唯一。
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == customer_id).first()
    customer_code = (customer.customer_code if customer else "TMP")[:8]
    year = str(datetime.now().year)[-2:]
    cat = "01"  # temp 默认 category
    system_code = f"{customer_code}S{cat}{year}{uuid.uuid4().hex[:6].upper()}"

    oe = (row.get('oe_number') or '').strip() or None
    product = PrdCustomerProduct(
        customer_id=customer_id,
        system_code=system_code,
        product_name=(row.get('product_name') or row.get('detail_desc') or '').strip() or None,
        customer_model=model or None,
        customer_remark=(row.get('customer_remark') or row.get('remark') or '').strip() or None,
        price_rmb=row.get('unit_price') or row.get('price_rmb'),
        price_usd=row.get('price_usd'),
        is_temporary=True,
        is_active=True,
    )
    db.add(product)
    db.flush()  # 触发主键分配

    if oe:
        db.add(PrdCustomerProductOE(
            customer_product_id=product.id,
            oe_number=oe,
            is_primary=True,
        ))

    db.commit()
    db.refresh(product)
    return product, True


def get_customer_products(
    db: Session,
    customer_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    is_temporary: Optional[bool] = None,  # Phase 2: 支持临时/正式筛选
) -> Tuple[List[PrdCustomerProduct], int]:
    """获取客户产品列表（支持临时/正式产品筛选）"""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[CP查询-DEBUG] ===== get_customer_products 开始 =====")
    logger.info(f"[CP查询-DEBUG] 查询参数: customer_id={customer_id}, search={search!r}, skip={skip}, limit={limit}, is_temporary={is_temporary}")

    query = db.query(PrdCustomerProduct).filter(PrdCustomerProduct.is_active == True)
    logger.info(f"[CP查询-DEBUG] 基础查询: is_active=True")

    if customer_id:
        query = query.filter(PrdCustomerProduct.customer_id == customer_id)
        logger.info(f"[CP查询-DEBUG] 添加筛选: customer_id={customer_id}")

    # Phase 2: 按临时/正式产品筛选
    if is_temporary is not None:
        query = query.filter(PrdCustomerProduct.is_temporary == is_temporary)
        logger.info(f"[CP查询-DEBUG] 添加筛选: is_temporary={is_temporary}")

    if search:
        # 搜索产品名称、客户型号、编号、OE号
        search_filter = or_(
            PrdCustomerProduct.product_name.ilike(f"%{search}%"),
            PrdCustomerProduct.customer_model.ilike(f"%{search}%"),
        )
        # 搜索编号
        codes = db.query(PrdCustomerProductCode).filter(
            PrdCustomerProductCode.product_code.ilike(f"%{search}%")
        ).all()
        code_ids = [c.customer_product_id for c in codes]
        oes = db.query(PrdCustomerProductOE).filter(
            PrdCustomerProductOE.oe_number.ilike(f"%{search}%")
        ).all()
        oe_ids = [o.customer_product_id for o in oes]

        search_filter = or_(
            search_filter,
            PrdCustomerProduct.id.in_(code_ids) if code_ids else False,
            PrdCustomerProduct.id.in_(oe_ids) if oe_ids else False,
        )
        query = query.filter(search_filter)
        logger.info(f"[CP查询-DEBUG] 添加搜索: search={search!r}")

    total = query.count()
    logger.info(f"[CP查询-DEBUG] 总记录数: total={total}")

    items = query.order_by(PrdCustomerProduct.created_at.desc()).offset(skip).limit(limit).all()
    logger.info(f"[CP查询-DEBUG] 返回记录数: len(items)={len(items)}")

    # [DEBUG] 打印返回的记录详情（最多5条）
    if len(items) > 0:
        logger.info(f"[CP查询-DEBUG] 返回记录详情:")
        for idx, item in enumerate(items[:5]):
            logger.info(f"[CP查询-DEBUG]   [{idx}] id={item.id}, customer_id={item.customer_id}, "
                       f"system_code={item.system_code!r}, "
                       f"product_name={item.product_name!r}, is_active={item.is_active}")
        if len(items) > 5:
            logger.info(f"[CP查询-DEBUG]   ... 还有 {len(items) - 5} 条未显示")
    else:
        logger.warning(f"[CP查询-DEBUG] ⚠️ 无匹配记录!")

    logger.info(f"[CP查询-DEBUG] ===== get_customer_products 完成 =====")
    return items, total


def get_customer_product(db: Session, product_id: int) -> Optional[PrdCustomerProduct]:
    """获取单个客户产品"""
    return db.query(PrdCustomerProduct).filter(PrdCustomerProduct.id == product_id).first()


def get_customer_product_by_system_code(db: Session, system_code: str) -> Optional[PrdCustomerProduct]:
    """通过系统编号获取单个客户产品（system_code 唯一）"""
    return db.query(PrdCustomerProduct).filter(
        PrdCustomerProduct.system_code == system_code
    ).first()


def get_customer_products_by_customer(db: Session, customer_id: int) -> List[PrdCustomerProduct]:
    """获取指定客户的所有产品"""
    return db.query(PrdCustomerProduct).filter(
        PrdCustomerProduct.customer_id == customer_id,
        PrdCustomerProduct.is_active == True
    ).order_by(PrdCustomerProduct.product_name).all()


def update_customer_product(db: Session, product_id: int, data: CustomerProductUpdate) -> Optional[PrdCustomerProduct]:
    """更新客户产品"""
    customer_product = get_customer_product(db, product_id)
    if not customer_product:
        return None
    
    update_data = data.model_dump(exclude_unset=True)
    
    # 处理副图JSON转换
    if 'sub_images' in update_data and update_data['sub_images'] is not None:
        update_data['sub_images'] = json.dumps(update_data['sub_images'])
    
    for key, value in update_data.items():
        setattr(customer_product, key, value)

    db.commit()
    db.refresh(customer_product)
    return customer_product


# ============ Phase 2: 临时产品相关 ============

def convert_temporary_to_official(db: Session, product_id: int) -> Optional[PrdCustomerProduct]:
    """
    将临时产品转正（is_temporary=False）
    Phase 2 新增：单表操作，不涉及 prd_product
    """
    import logging
    logger = logging.getLogger(__name__)

    convert_start = datetime.now()
    logger.info(f"\n{'═' * 80}")
    logger.info(f"[🔄 产品转正流程开始] convert_temporary_to_official()")
    logger.info(f"{'═' * 80}")
    logger.info(f"  参数: product_id={product_id}")

    customer_product = get_customer_product(db, product_id)
    if not customer_product:
        logger.error(f"[❌ 转正失败] 产品不存在: product_id={product_id}")
        return None

    logger.info(f"[步骤1/3] 查询产品信息")
    logger.info(f"  产品ID: {customer_product.id}")
    logger.info(f"  客户型号: {customer_product.customer_model}")
    logger.info(f"  产品名称: {customer_product.product_name}")
    logger.info(f"  当前状态: {'临时产品' if customer_product.is_temporary else '正式产品'}")

    if not customer_product.is_temporary:
        # 已经是正式产品，直接返回
        logger.info(f"[✅ 跳过转正] 该产品已经是正式产品，无需转正")
        return customer_product

    logger.info(f"[步骤2/3] 执行转正操作 - is_temporary: True → False")
    customer_product.is_temporary = False
    db.commit()
    db.refresh(customer_product)

    convert_duration = (datetime.now() - convert_start).total_seconds()

    logger.info(f"[步骤3/3] 转正完成验证")
    logger.info(f"  更新后状态: {'临时产品' if customer_product.is_temporary else '正式产品 ✓'}")
    logger.info(f"  更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"\n{'═' * 80}")
    logger.info(f"[✅ 产品转正成功]")
    logger.info(f"  Product ID: {product_id}")
    logger.info(f"  客户型号: {customer_product.customer_model}")
    logger.info(f"  耗时: {convert_duration:.3f}s")
    logger.info(f"{'═' * 80}\n")

    return customer_product


def update_and_confirm_temporary(
    db: Session,
    product_id: int,
    full_data: dict,
) -> Optional[PrdCustomerProduct]:
    """2026-06-16 修复 log.txt 404：临时产品转正 + 更新字段

    替代已删除的 `crud/product.py::confirm_temporary_product`（Phase 5 后 PrdProduct 表已删除）。
    此函数直接更新 PrdCustomerProduct 记录并清除 `is_temporary` 标记。

    支持的 full_data 字段：
        - product_name, oe_number (→ customer_model 默认), brand, color
        - detail_desc, customer_remark, category_id
        - price_usd, price_rmb
        - default_image_url (→ image_url), sub_images (JSON 字符串)
        - customer_model, dept_id
        - customer_id（转正后允许切换客户，否则保持）

    Returns:
        更新后的 PrdCustomerProduct，None 表示产品不存在
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[转正-Phase5-兼容] update_and_confirm_temporary product_id={product_id}")

    customer_product = get_customer_product(db, product_id)
    if not customer_product:
        logger.error(f"[转正失败] 产品不存在: product_id={product_id}")
        return None

    if not customer_product.is_temporary:
        logger.info(f"[转正-跳过] 已经是正式产品，直接更新字段")
    else:
        customer_product.is_temporary = False
        logger.info(f"[转正] is_temporary: True → False")

    # 更新字段（白名单：只允许更新存在的列）
    _ALLOWED = {
        "product_name", "customer_model", "color", "customer_remark",
        "category_id", "price_usd", "price_rmb",
        "detail_desc", "brand", "specifications",
        "image_url", "sub_images",
    }
    for key, val in (full_data or {}).items():
        if key in _ALLOWED and val is not None:
            setattr(customer_product, key, val)

    # 兼容旧字段映射
    if "default_image_url" in (full_data or {}) and full_data["default_image_url"]:
        customer_product.image_url = full_data["default_image_url"]

    # 2026-06-23：OE 号支持列表（oe_numbers）+ 兼容单字段（oe_number）
    # 修复：之前只存一个 oe_number 字段，用户在 Dialog 加的 TESTOE1/TESTOE2 全部丢失
    from models.customer_product_oe import PrdCustomerProductOE
    oe_list: list[str] = []
    if full_data.get("oe_numbers"):
        oe_list = [str(x).strip() for x in full_data["oe_numbers"] if x]
    elif full_data.get("oe_number"):
        oe_list = [str(full_data["oe_number"]).strip()]

    for idx, oe_val in enumerate(oe_list):
        if not oe_val:
            continue
        # 第一次写入时同步 customer_model
        if idx == 0 and not customer_product.customer_model:
            customer_product.customer_model = oe_val
        existing_oe = db.query(PrdCustomerProductOE).filter(
            PrdCustomerProductOE.customer_product_id == product_id,
            PrdCustomerProductOE.oe_number == oe_val,
        ).first()
        if not existing_oe:
            new_oe = PrdCustomerProductOE(
                customer_product_id=product_id,
                oe_number=oe_val,
                # 第一个 OE 设为主 OE；用户可后续在编辑界面切换
                is_primary=(idx == 0),
            )
            db.add(new_oe)
        else:
            # 已存在：确保主标记正确
            if idx == 0:
                existing_oe.is_primary = True

    # 2026-06-23：客户产品编号也支持列表（customer_codes）+ 兼容单字段（product_code）
    # 修复：之前转正根本不写 prd_customer_product_code 表
    from models.customer_product_code import PrdCustomerProductCode
    code_list: list[str] = []
    if full_data.get("customer_codes"):
        code_list = [str(x).strip() for x in full_data["customer_codes"] if x]
    elif full_data.get("product_code"):
        code_list = [str(full_data["product_code"]).strip()]

    for idx, code_val in enumerate(code_list):
        if not code_val:
            continue
        existing_code = db.query(PrdCustomerProductCode).filter(
            PrdCustomerProductCode.customer_product_id == product_id,
            PrdCustomerProductCode.product_code == code_val,
        ).first()
        if not existing_code:
            new_code = PrdCustomerProductCode(
                customer_product_id=product_id,
                product_code=code_val,
                is_primary=(idx == 0),
            )
            db.add(new_code)

    # 生成系统编号（如果还没有）
    if not customer_product.system_code:
        try:
            customer_id = customer_product.customer_id
            category_id = customer_product.category_id or '01'
            new_code = _generate_system_code(db, customer_id, category_id)
            if new_code:
                customer_product.system_code = new_code
        except Exception as e:
            logger.warning(f"[转正-系统编号生成失败] {e}（不影响转正）")

    db.commit()
    db.refresh(customer_product)

    logger.info(f"[✅ 转正+更新成功] product_id={product_id} system_code={customer_product.system_code}")
    return customer_product


def get_temporary_products(
    db: Session,
    customer_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[List[PrdCustomerProduct], int]:
    """获取临时产品列表（Phase 2 新增）"""
    return get_customer_products(
        db,
        customer_id=customer_id,
        skip=skip,
        limit=limit,
        is_temporary=True,
    )


def delete_customer_product(db: Session, product_id: int, soft_only: bool = True) -> dict:
    """
    删除客户产品（支持软删除和物理删除，处理多用户冲突）
    
    Args:
        db: 数据库会话
        product_id: 产品ID
        soft_only: True=只软删除, False=立即物理删除
    
    Returns:
        dict: {"success": bool, "conflict": bool, "message": str}
    """
    from datetime import datetime
    
    print(f"[DEBUG] delete_customer_product: 开始删除, product_id={product_id}, soft_only={soft_only}")
    
    # 使用行级锁防止并发冲突
    customer_product = db.query(PrdCustomerProduct).filter(
        PrdCustomerProduct.id == product_id
    ).with_for_update().first()
    
    if not customer_product:
        print(f"[DEBUG] delete_customer_product: 产品不存在, product_id={product_id}")
        return {"success": False, "conflict": False, "message": "产品不存在"}
    
    # 检查是否已被其他用户删除（并发冲突）
    if not customer_product.is_active:
        print(f"[DEBUG] delete_customer_product: 已被其他用户删除, product_id={product_id}")
        return {"success": False, "conflict": True, "message": "产品已被其他用户删除"}
    
    print(f"[DEBUG] delete_customer_product: 删除前 is_active={customer_product.is_active}")
    
    if soft_only:
        # 软删除：设置为非激活 + 记录删除时间
        customer_product.is_active = False
        customer_product.deleted_at = datetime.now()
    else:
        # 立即物理删除
        db.delete(customer_product)
    
    db.commit()
    
    print(f"[DEBUG] delete_customer_product: 删除后 is_active={customer_product.is_active}")
    return {"success": True, "conflict": False, "message": "删除成功"}


# ========== 编号管理 ==========

def add_product_code(db: Session, customer_product_id: int, data: CustomerProductCodeCreate) -> Optional[PrdCustomerProductCode]:
    """为客户产品添加编号"""
    # 检查是否已存在
    existing = db.query(PrdCustomerProductCode).filter(
        PrdCustomerProductCode.customer_product_id == customer_product_id,
        PrdCustomerProductCode.product_code == data.product_code
    ).first()
    
    if existing:
        return existing  # 已存在则返回现有记录
    
    code = PrdCustomerProductCode(
        customer_product_id=customer_product_id,
        product_code=data.product_code,
        is_primary=data.is_primary,
        remark=data.remark,
    )
    db.add(code)
    db.commit()
    db.refresh(code)
    return code


def get_product_codes(db: Session, customer_product_id: int) -> List[PrdCustomerProductCode]:
    """获取客户产品的所有编号"""
    return db.query(PrdCustomerProductCode).filter(
        PrdCustomerProductCode.customer_product_id == customer_product_id
    ).order_by(PrdCustomerProductCode.is_primary.desc(), PrdCustomerProductCode.created_at).all()


def set_primary_code(db: Session, code_id: int) -> bool:
    """设置主编号"""
    code = db.query(PrdCustomerProductCode).filter(PrdCustomerProductCode.id == code_id).first()
    if not code:
        return False
    
    # 先取消该产品的所有主编号标记
    db.query(PrdCustomerProductCode).filter(
        PrdCustomerProductCode.customer_product_id == code.customer_product_id
    ).update({'is_primary': False})
    
    # 设置当前编号为主编号
    code.is_primary = True
    db.commit()
    return True


def delete_product_code(db: Session, code_id: int) -> bool:
    """删除编号"""
    code = db.query(PrdCustomerProductCode).filter(PrdCustomerProductCode.id == code_id).first()
    if not code:
        return False
    
    db.delete(code)
    db.commit()
    return True


def batch_add_codes(db: Session, customer_product_id: int, codes: List[str], set_first_primary: bool = True) -> List[PrdCustomerProductCode]:
    """批量添加编号"""
    result = []
    for idx, code_str in enumerate(codes):
        code_str = code_str.strip()
        if not code_str:
            continue
        
        # 检查是否已存在
        existing = db.query(PrdCustomerProductCode).filter(
            PrdCustomerProductCode.customer_product_id == customer_product_id,
            PrdCustomerProductCode.product_code == code_str
        ).first()
        
        if existing:
            result.append(existing)
            continue
        
        code = PrdCustomerProductCode(
            customer_product_id=customer_product_id,
            product_code=code_str,
            is_primary=(idx == 0 and set_first_primary),
        )
        db.add(code)
        result.append(code)
    
    db.commit()
    return result


# ========== OE号管理 ==========

def add_product_oe(db: Session, customer_product_id: int, data: CustomerProductOECreate) -> Optional[PrdCustomerProductOE]:
    """为客户产品添加OE号"""
    # 检查是否已存在
    existing = db.query(PrdCustomerProductOE).filter(
        PrdCustomerProductOE.customer_product_id == customer_product_id,
        PrdCustomerProductOE.oe_number == data.oe_number
    ).first()
    
    if existing:
        return existing  # 已存在则返回现有记录
    
    oe = PrdCustomerProductOE(
        customer_product_id=customer_product_id,
        oe_number=data.oe_number,
        is_primary=data.is_primary,
        remark=data.remark,
    )
    db.add(oe)
    db.commit()
    db.refresh(oe)
    return oe


def get_product_oes(db: Session, customer_product_id: int) -> List[PrdCustomerProductOE]:
    """获取客户产品的所有OE号"""
    return db.query(PrdCustomerProductOE).filter(
        PrdCustomerProductOE.customer_product_id == customer_product_id
    ).order_by(PrdCustomerProductOE.is_primary.desc(), PrdCustomerProductOE.created_at).all()


def set_primary_oe(db: Session, oe_id: int) -> bool:
    """设置主OE号"""
    oe = db.query(PrdCustomerProductOE).filter(PrdCustomerProductOE.id == oe_id).first()
    if not oe:
        return False
    
    # 先取消该产品的所有主OE标记
    db.query(PrdCustomerProductOE).filter(
        PrdCustomerProductOE.customer_product_id == oe.customer_product_id
    ).update({'is_primary': False})
    
    # 设置当前OE为主OE
    oe.is_primary = True
    db.commit()
    return True


def delete_product_oe(db: Session, oe_id: int) -> bool:
    """删除OE号"""
    oe = db.query(PrdCustomerProductOE).filter(PrdCustomerProductOE.id == oe_id).first()
    if not oe:
        return False
    
    db.delete(oe)
    db.commit()
    return True


def batch_add_oes(db: Session, customer_product_id: int, oes: List[str], set_first_primary: bool = True) -> List[PrdCustomerProductOE]:
    """批量添加OE号"""
    result = []
    for idx, oe_str in enumerate(oes):
        oe_str = oe_str.strip()
        if not oe_str:
            continue
        
        # 检查是否已存在
        existing = db.query(PrdCustomerProductOE).filter(
            PrdCustomerProductOE.customer_product_id == customer_product_id,
            PrdCustomerProductOE.oe_number == oe_str
        ).first()
        
        if existing:
            result.append(existing)
            continue
        
        oe = PrdCustomerProductOE(
            customer_product_id=customer_product_id,
            oe_number=oe_str,
            is_primary=(idx == 0 and set_first_primary),
        )
        db.add(oe)
        result.append(oe)
    
    db.commit()
    return result


def search_by_oe_number(db: Session, oe_number: str) -> List[PrdCustomerProduct]:
    """通过OE号搜索客户产品"""
    # 先找到OE号对应的产品ID列表
    oe_records = db.query(PrdCustomerProductOE).filter(
        PrdCustomerProductOE.oe_number.ilike(f"%{oe_number}%")
    ).all()
    
    if not oe_records:
        return []
    
    product_ids = list(set([oe.customer_product_id for oe in oe_records]))
    return db.query(PrdCustomerProduct).filter(
        PrdCustomerProduct.id.in_(product_ids),
        PrdCustomerProduct.is_active == True
    ).all()


def search_by_code(db: Session, code: str) -> List[PrdCustomerProduct]:
    """通过编号搜索客户产品"""
    code_records = db.query(PrdCustomerProductCode).filter(
        PrdCustomerProductCode.product_code.ilike(f"%{code}%")
    ).all()
    
    if not code_records:
        return []
    
    product_ids = list(set([c.customer_product_id for c in code_records]))
    return db.query(PrdCustomerProduct).filter(
        PrdCustomerProduct.id.in_(product_ids),
        PrdCustomerProduct.is_active == True
    ).all()