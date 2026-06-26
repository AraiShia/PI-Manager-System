from sqlalchemy.orm import Session
from sqlalchemy import or_
from models import CrmCustomer, CrmCustomerAddress, CrmCustomerContact
from schemas import CustomerCreate, CustomerUpdate, CustomerAddressCreate, CustomerAddressUpdate, CustomerContactCreate
from utils.number_generator import NumberGenerator

def create_customer(db: Session, customer: CustomerCreate) -> CrmCustomer:
    customer_code = NumberGenerator.generate_customer_code(db)
    
    db_customer = CrmCustomer(
        customer_code=customer_code,
        dept_id=customer.dept_id,
        customer_name=customer.customer_name,
        country=customer.country,
        basic_require=customer.basic_require,
        special_require=customer.special_require,
        payment_terms=customer.payment_terms
    )
    
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    
    if customer.addresses:
        for addr in customer.addresses:
            db_address = CrmCustomerAddress(
                customer_id=db_customer.id,
                **addr.dict()
            )
            db.add(db_address)
    
    if customer.contacts:
        for contact in customer.contacts:
            db_contact = CrmCustomerContact(
                customer_id=db_customer.id,
                **contact.dict()
            )
            db.add(db_contact)
    
    db.commit()
    return db_customer

def get_customer(db: Session, customer_id: int) -> CrmCustomer:
    return db.query(CrmCustomer).filter(CrmCustomer.id == customer_id).first()

def get_customer_by_code(db: Session, customer_code: str) -> CrmCustomer:
    return db.query(CrmCustomer).filter(CrmCustomer.customer_code == customer_code).first()

def get_customers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(CrmCustomer).offset(skip).limit(limit).all()

def search_customers(db: Session, keyword: str = "", country: str = None):
    query = db.query(CrmCustomer)
    
    if keyword:
        query = query.filter(or_(
            CrmCustomer.customer_name.like(f"%{keyword}%"),
            CrmCustomer.customer_code.like(f"%{keyword}%")
        ))
    
    if country:
        query = query.filter(CrmCustomer.country == country)
    
    return query.all()

def update_customer(db: Session, customer_id: int, customer_update: CustomerUpdate) -> CrmCustomer:
    db_customer = get_customer(db, customer_id)
    if not db_customer:
        return None

    update_data = customer_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        if key != 'customer_code':
            setattr(db_customer, key, value)

    db.commit()
    db.refresh(db_customer)
    return db_customer

def toggle_customer_status(db: Session, customer_id: int) -> bool:
    db_customer = get_customer(db, customer_id)
    if not db_customer:
        return False
    
    db_customer.status = 1 - db_customer.status
    db.commit()
    return True

def delete_customer(db: Session, customer_id: int) -> bool:
    db_customer = get_customer(db, customer_id)
    if not db_customer:
        return False
    
    db.delete(db_customer)
    db.commit()
    return True

# 地址管理
def get_customer_addresses(db: Session, customer_id: int):
    return db.query(CrmCustomerAddress).filter(CrmCustomerAddress.customer_id == customer_id).all()

def get_customer_address(db: Session, customer_id: int, address_id: int):
    return db.query(CrmCustomerAddress).filter(
        CrmCustomerAddress.customer_id == customer_id,
        CrmCustomerAddress.id == address_id
    ).first()

def create_customer_address(db: Session, customer_id: int, address: CustomerAddressCreate):
    db_address = CrmCustomerAddress(
        customer_id=customer_id,
        **address.dict()
    )
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address

def update_customer_address(db: Session, customer_id: int, address_id: int, address: CustomerAddressUpdate):
    db_address = get_customer_address(db, customer_id, address_id)
    if not db_address:
        return None
    
    update_data = address.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_address, key, value)
    
    db.commit()
    db.refresh(db_address)
    return db_address

def delete_customer_address(db: Session, customer_id: int, address_id: int) -> bool:
    db_address = get_customer_address(db, customer_id, address_id)
    if not db_address:
        return False
    
    db.delete(db_address)
    db.commit()
    return True

# 联系人管理
def get_customer_contacts(db: Session, customer_id: int):
    return db.query(CrmCustomerContact).filter(CrmCustomerContact.customer_id == customer_id).all()

def create_customer_contact(db: Session, customer_id: int, contact: CustomerContactCreate):
    db_contact = CrmCustomerContact(
        customer_id=customer_id,
        **contact.dict()
    )
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

def update_customer_contact(db: Session, customer_id: int, contact_id: int, contact: CustomerContactCreate):
    db_contact = db.query(CrmCustomerContact).filter(
        CrmCustomerContact.customer_id == customer_id,
        CrmCustomerContact.id == contact_id
    ).first()
    if not db_contact:
        return None
    
    update_data = contact.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_contact, key, value)
    
    db.commit()
    db.refresh(db_contact)
    return db_contact

def delete_customer_contact(db: Session, customer_id: int, contact_id: int) -> bool:
    db_contact = db.query(CrmCustomerContact).filter(
        CrmCustomerContact.customer_id == customer_id,
        CrmCustomerContact.id == contact_id
    ).first()
    if not db_contact:
        return False
    
    db.delete(db_contact)
    db.commit()
    return True

# 客户 PI 订单历史
def get_customer_pi_list(db: Session, customer_id: int):
    from models.pi import PiProformaInvoice
    return db.query(PiProformaInvoice).filter(PiProformaInvoice.customer_id == customer_id).all()

def get_customers_batch_info(db: Session, customer_ids: list[int]) -> dict[int, dict]:
    """批量获取客户联系人和地址（供路由层调用）

    Args:
        db: 数据库会话
        customer_ids: 客户ID列表

    Returns:
        dict[int, dict]: {客户ID: {"contacts": [...], "addresses": [...]}}
    """
    if not customer_ids:
        return {}

    customers = db.query(CrmCustomer).filter(CrmCustomer.id.in_(customer_ids)).all()

    result = {}
    for c in customers:
        result[c.id] = {
            "contacts": list(c.contacts),
            "addresses": list(c.addresses)
        }

    return result
