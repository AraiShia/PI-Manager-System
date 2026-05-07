from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from crud.customer import (
    create_customer, get_customer, get_customers, update_customer, delete_customer,
    search_customers, toggle_customer_status, get_customer_addresses,
    create_customer_address, update_customer_address, delete_customer_address,
    get_customer_contacts, get_customer_pi_list,
    create_customer_contact, update_customer_contact, delete_customer_contact
)
from schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse, CustomerAddressCreate, CustomerAddressUpdate, CustomerAddressResponse, CustomerContactCreate

router = APIRouter(prefix="/api/customers", tags=["客户管理"])

@router.post("/", response_model=CustomerResponse)
def create_customer_api(customer: CustomerCreate, db: Session = Depends(get_db)):
    return create_customer(db, customer)

@router.get("/", response_model=list[CustomerResponse])
def read_customers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_customers(db, skip=skip, limit=limit)

@router.get("/search", response_model=list[CustomerResponse])
def search_customers_api(keyword: str = "", country: str = None, db: Session = Depends(get_db)):
    return search_customers(db, keyword=keyword, country=country)

@router.get("/{customer_id}", response_model=CustomerResponse)
def read_customer(customer_id: int, db: Session = Depends(get_db)):
    db_customer = get_customer(db, customer_id)
    if db_customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    return db_customer

@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer_api(customer_id: int, customer: CustomerUpdate, db: Session = Depends(get_db)):
    db_customer = update_customer(db, customer_id, customer)
    if db_customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    return db_customer

@router.patch("/{customer_id}/status")
def toggle_status_api(customer_id: int, db: Session = Depends(get_db)):
    success = toggle_customer_status(db, customer_id)
    if not success:
        raise HTTPException(status_code=404, detail="客户不存在")
    return {"message": "状态已更新"}

@router.delete("/{customer_id}")
def delete_customer_api(customer_id: int, db: Session = Depends(get_db)):
    success = delete_customer(db, customer_id)
    if not success:
        raise HTTPException(status_code=404, detail="客户不存在")
    return {"message": "客户已删除"}

# 客户地址管理
@router.get("/{customer_id}/addresses")
def read_customer_addresses(customer_id: int, db: Session = Depends(get_db)):
    return get_customer_addresses(db, customer_id)

@router.post("/{customer_id}/addresses", response_model=CustomerAddressResponse)
def create_address_api(customer_id: int, address: CustomerAddressCreate, db: Session = Depends(get_db)):
    return create_customer_address(db, customer_id, address)

@router.put("/{customer_id}/addresses/{address_id}", response_model=CustomerAddressResponse)
def update_address_api(customer_id: int, address_id: int, address: CustomerAddressUpdate, db: Session = Depends(get_db)):
    db_address = update_customer_address(db, customer_id, address_id, address)
    if db_address is None:
        raise HTTPException(status_code=404, detail="地址不存在")
    return db_address

@router.delete("/{customer_id}/addresses/{address_id}")
def delete_address_api(customer_id: int, address_id: int, db: Session = Depends(get_db)):
    success = delete_customer_address(db, customer_id, address_id)
    if not success:
        raise HTTPException(status_code=404, detail="地址不存在")
    return {"message": "地址已删除"}

# 客户联系人
@router.get("/{customer_id}/contacts")
def read_customer_contacts(customer_id: int, db: Session = Depends(get_db)):
    return get_customer_contacts(db, customer_id)

@router.post("/{customer_id}/contacts")
def create_customer_contact(customer_id: int, contact: CustomerContactCreate, db: Session = Depends(get_db)):
    return create_customer_contact(db, customer_id, contact)

@router.put("/{customer_id}/contacts/{contact_id}")
def update_customer_contact(customer_id: int, contact_id: int, contact: CustomerContactCreate, db: Session = Depends(get_db)):
    db_contact = update_customer_contact(db, customer_id, contact_id, contact)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="联系人不存在")
    return db_contact

@router.delete("/{customer_id}/contacts/{contact_id}")
def delete_customer_contact(customer_id: int, contact_id: int, db: Session = Depends(get_db)):
    success = delete_customer_contact(db, customer_id, contact_id)
    if not success:
        raise HTTPException(status_code=404, detail="联系人不存在")
    return {"message": "联系人已删除"}

# 客户 PI 订单历史
@router.get("/{customer_id}/pi-orders")
def read_customer_pi_orders(customer_id: int, db: Session = Depends(get_db)):
    return get_customer_pi_list(db, customer_id)
