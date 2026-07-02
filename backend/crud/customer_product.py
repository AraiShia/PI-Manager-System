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


def get_customer_products(
    db: Session,
    customer_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[List[PrdCustomerProduct], int]:
    """获取客户产品列表"""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[CP查询-DEBUG] ===== get_customer_products 开始 =====")
    logger.info(f"[CP查询-DEBUG] 查询参数: customer_id={customer_id}, search={search!r}, skip={skip}, limit={limit}")

    query = db.query(PrdCustomerProduct).filter(PrdCustomerProduct.is_active == True)
    logger.info(f"[CP查询-DEBUG] 基础查询: is_active=True")

    if customer_id:
        query = query.filter(PrdCustomerProduct.customer_id == customer_id)
        logger.info(f"[CP查询-DEBUG] 添加筛选: customer_id={customer_id}")

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