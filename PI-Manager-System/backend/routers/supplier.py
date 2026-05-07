from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from crud.supplier import (
    create_supplier, get_supplier, get_suppliers, update_supplier, delete_supplier, batch_create_suppliers
)
from schemas.supplier import SupplierCreate, SupplierUpdate, SupplierResponse
from region_data import get_all_provinces, get_cities_by_province

router = APIRouter(prefix="/api/suppliers", tags=["供应商管理"])

@router.post("/", response_model=SupplierResponse)
def create_supplier_api(supplier: SupplierCreate, dept_id: str = "S", db: Session = Depends(get_db)):
    return create_supplier(db, supplier, dept_id)

@router.get("/", response_model=list[SupplierResponse])
def read_suppliers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_suppliers(db, skip=skip, limit=limit)

@router.get("/provinces")
def get_provinces():
    return get_all_provinces()

@router.get("/cities/{province}")
def get_cities(province: str):
    return get_cities_by_province(province)

@router.get("/{supplier_id}", response_model=SupplierResponse)
def read_supplier(supplier_id: int, db: Session = Depends(get_db)):
    db_supplier = get_supplier(db, supplier_id)
    if db_supplier is None:
        raise HTTPException(status_code=404, detail="供应商不存在")
    return db_supplier

@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier_api(supplier_id: int, supplier: SupplierUpdate, db: Session = Depends(get_db)):
    db_supplier = update_supplier(db, supplier_id, supplier)
    if db_supplier is None:
        raise HTTPException(status_code=404, detail="供应商不存在")
    return db_supplier

@router.delete("/{supplier_id}")
def delete_supplier_api(supplier_id: int, db: Session = Depends(get_db)):
    success = delete_supplier(db, supplier_id)
    if not success:
        raise HTTPException(status_code=404, detail="供应商不存在")
    return {"message": "供应商已删除"}

@router.post("/batch")
def batch_create_suppliers_api(suppliers: dict, dept_id: str = "S", db: Session = Depends(get_db)):
    supplier_list = suppliers.get("suppliers", [])
    if not supplier_list:
        raise HTTPException(status_code=400, detail="供应商列表不能为空")
    
    result = batch_create_suppliers(db, supplier_list, dept_id)
    return result