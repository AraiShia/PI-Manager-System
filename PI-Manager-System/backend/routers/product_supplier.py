from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from crud import product_supplier as ps_crud
from schemas import ProductSupplierCreate, ProductSupplierUpdate, ProductSupplierResponse, ProductSupplierDetailResponse
from app.database import get_db

router = APIRouter(prefix="/api/product-suppliers", tags=["product-suppliers"])

@router.post("/", response_model=ProductSupplierResponse)
def create_product_supplier(product_supplier: ProductSupplierCreate, db: Session = Depends(get_db)):
    try:
        return ps_crud.create_product_supplier(db, product_supplier)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{product_id}", response_model=list[ProductSupplierDetailResponse])
def get_product_suppliers(product_id: int, db: Session = Depends(get_db)):
    return ps_crud.get_product_suppliers_with_details(db, product_id)

@router.put("/{ps_id}", response_model=ProductSupplierResponse)
def update_product_supplier(ps_id: int, update_data: ProductSupplierUpdate, db: Session = Depends(get_db)):
    result = ps_crud.update_product_supplier(db, ps_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="Product supplier not found")
    return result

@router.delete("/{ps_id}")
def delete_product_supplier(ps_id: int, db: Session = Depends(get_db)):
    success = ps_crud.delete_product_supplier(db, ps_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product supplier not found")
    return {"message": "Deleted successfully"}