from sqlalchemy.orm import Session, joinedload
from models import SupSupplier, SupSupplierContact
from schemas import SupplierCreate, SupplierUpdate
from region_data import get_city_code

def int_to_base32(n):
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUV"
    return chars[n]

def generate_supplier_code(db: Session, city_code: str) -> str:
    prefix = f"SP{city_code}" if city_code else "SP000"
    base_query = db.query(SupSupplier.supplier_code).filter(
        SupSupplier.supplier_code.like(f"{prefix}%")
    ).order_by(SupSupplier.supplier_code.desc())

    max_code = base_query.first()

    if max_code:
        suffix = max_code[0][len(prefix):]
        if len(suffix) == 3:
            try:
                last_num = int(suffix)
                next_num = last_num + 1
                return f"{prefix}{str(next_num).zfill(3)}"
            except ValueError:
                pass

    return f"{prefix}001"

def create_supplier(db: Session, supplier: SupplierCreate, dept_id: str = "S") -> SupSupplier:
    city_code = supplier.city_code or "000"
    supplier_code = generate_supplier_code(db, city_code)

    region = f"{supplier.province} {supplier.city}" if supplier.province and supplier.city else ""

    db_supplier = SupSupplier(
        supplier_code=supplier_code,
        dept_id=dept_id,
        supplier_name=supplier.supplier_name,
        region=region
    )

    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)

    if supplier.contact_person or supplier.phone or supplier.email or supplier.address:
        contact = SupSupplierContact(
            supplier_id=db_supplier.id,
            name=supplier.contact_person,
            phone=supplier.phone,
            email=supplier.email,
            address=supplier.address,
            is_primary=1
        )
        db.add(contact)
        db.commit()

    return db_supplier

def get_supplier(db: Session, supplier_id: int) -> SupSupplier:
    return db.query(SupSupplier).filter(SupSupplier.id == supplier_id).first()

def get_supplier_by_code(db: Session, supplier_code: str) -> SupSupplier:
    return db.query(SupSupplier).filter(SupSupplier.supplier_code == supplier_code).first()

def get_supplier_by_name(db: Session, supplier_name: str, dept_id: str = "S") -> SupSupplier:
    """按名称精确查找供应商（同部门内）"""
    if not supplier_name:
        return None
    return db.query(SupSupplier).filter(
        SupSupplier.supplier_name == supplier_name,
        SupSupplier.dept_id == dept_id,
    ).first()

def find_or_create_supplier_by_name(
    db: Session,
    supplier_name: str,
    dept_id: str = "S",
    contact_person: str = None,
    phone: str = None,
    address: str = None,
) -> SupSupplier:
    """2026-06-23：线上采购（1688 店铺/微信昵称）按名称查找或创建供应商

    流程：
    1. 按 supplier_name + dept_id 精确查找现有供应商
    2. 找到 → 复用，返回
    3. 找不到 → 用 SupplierCreate 创建，dept_id 默认为 'S'
    """
    if not supplier_name or not supplier_name.strip():
        return None
    supplier_name = supplier_name.strip()

    existing = get_supplier_by_name(db, supplier_name, dept_id)
    if existing:
        return existing

    # 创建新供应商
    create_payload = SupplierCreate(
        supplier_name=supplier_name,
        contact_person=contact_person or "",
        phone=phone or "",
        address=address or "",
    )
    return create_supplier(db, create_payload, dept_id)

def get_suppliers(db: Session, skip: int = 0, limit: int = 100):
    suppliers = db.query(SupSupplier).options(
        joinedload(SupSupplier.contacts)
    ).offset(skip).limit(limit).all()

    result = []
    for s in suppliers:
        supplier_dict = {
            "id": s.id,
            "supplier_code": s.supplier_code,
            "supplier_name": s.supplier_name,
            "region": s.region,
            "dept_id": s.dept_id,
            "status": s.status,
            "created_at": s.created_at
        }
        primary_contact = next((c for c in s.contacts if c.is_primary == 1), None)
        if primary_contact:
            supplier_dict["contact_person"] = getattr(primary_contact, 'name', None)
            supplier_dict["phone"] = getattr(primary_contact, 'phone', None)
            supplier_dict["email"] = getattr(primary_contact, 'email', None)
            supplier_dict["address"] = getattr(primary_contact, 'address', None)
        result.append(supplier_dict)
    return result

def update_supplier(db: Session, supplier_id: int, supplier_update: SupplierUpdate) -> SupSupplier:
    db_supplier = get_supplier(db, supplier_id)
    if not db_supplier:
        return None

    update_data = supplier_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_supplier, key, value)

    db.commit()
    db.refresh(db_supplier)
    return db_supplier

def delete_supplier(db: Session, supplier_id: int) -> bool:
    db_supplier = get_supplier(db, supplier_id)
    if not db_supplier:
        return False

    for contact in db_supplier.contacts:
        db.delete(contact)
    
    db.delete(db_supplier)
    db.commit()
    return True

def batch_create_suppliers(db: Session, supplier_list: list, dept_id: str = "S") -> dict:
    success_count = 0
    fail_count = 0
    failed_items = []
    
    for idx, supplier_data in enumerate(supplier_list):
        try:
            supplier_create = SupplierCreate(**supplier_data)
            result = create_supplier(db, supplier_create, dept_id)
            success_count += 1
        except Exception as e:
            fail_count += 1
            failed_items.append({
                "index": idx,
                "supplier_name": supplier_data.get("supplier_name", "未知"),
                "error": str(e)
            })
    
    return {
        "total": len(supplier_list),
        "success": success_count,
        "failed": fail_count,
        "failed_items": failed_items
    }