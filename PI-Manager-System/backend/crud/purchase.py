from sqlalchemy.orm import Session
from datetime import datetime
from models import (
    PoPurchaseOrder, 
    PoPurchaseOrderItem, 
    Po1688Purchase,
    PiProformaInvoice,
    SupSupplier,
    PrdProduct
)
from schemas import PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderItemCreate
from utils.number_generator import NumberGenerator
from utils.volume_calculator import VolumeCalculator

def create_purchase_order(db: Session, purchase: PurchaseOrderCreate) -> PoPurchaseOrder:
    pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == purchase.pi_id).first()
    if not pi:
        raise ValueError("PI不存在")
    
    supplier = db.query(SupSupplier).filter(SupSupplier.id == purchase.supplier_id).first()
    if not supplier:
        raise ValueError("供应商不存在")
    
    supplier_code = str(supplier.id).zfill(3)
    po_no = NumberGenerator.generate_po_no(db, pi.pi_no, supplier_code)
    
    total_amount = sum(item.quantity * item.unit_price for item in purchase.items)
    
    db_po = PoPurchaseOrder(
        po_no=po_no,
        pi_id=purchase.pi_id,
        supplier_id=purchase.supplier_id,
        total_amount=total_amount,
        currency=purchase.currency,
        status=1,
        dept_id=purchase.dept_id
    )
    
    db.add(db_po)
    db.commit()
    db.refresh(db_po)
    
    for item in purchase.items:
        product = db.query(PrdProduct).filter(PrdProduct.id == item.product_id).first()
        
        total_volume = 0
        cartons = 0
        if product and product.carton_volume_m3 and product.units_per_carton:
            cartons = VolumeCalculator.calculate_cartons(item.quantity, product.units_per_carton)
            total_volume = cartons * product.carton_volume_m3
        
        db_item = PoPurchaseOrderItem(
            po_id=db_po.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.quantity * item.unit_price,
            cartons=cartons,
            total_volume_m3=total_volume,
            remark=item.remark
        )
        db.add(db_item)
    
    db.commit()
    db.refresh(db_po)
    
    return db_po

def get_purchase_order(db: Session, po_id: int) -> PoPurchaseOrder:
    return db.query(PoPurchaseOrder).filter(PoPurchaseOrder.id == po_id).first()

def get_purchase_order_by_no(db: Session, po_no: str) -> PoPurchaseOrder:
    return db.query(PoPurchaseOrder).filter(PoPurchaseOrder.po_no == po_no).first()

def get_purchase_orders(db: Session, skip: int = 0, limit: int = 100, status: int = None, pi_id: int = None):
    query = db.query(PoPurchaseOrder)
    if status is not None:
        query = query.filter(PoPurchaseOrder.status == status)
    if pi_id is not None:
        query = query.filter(PoPurchaseOrder.pi_id == pi_id)
    return query.offset(skip).limit(limit).all()

def update_purchase_status(db: Session, po_id: int, status: int) -> PoPurchaseOrder:
    db_po = get_purchase_order(db, po_id)
    if not db_po:
        return None
    
    db_po.status = status
    db.commit()
    db.refresh(db_po)
    return db_po

def update_purchase_order(db: Session, po_id: int, purchase_update) -> PoPurchaseOrder:
    db_po = get_purchase_order(db, po_id)
    if not db_po:
        return None
    
    if purchase_update.supplier_id is not None:
        supplier = db.query(SupSupplier).filter(SupSupplier.id == purchase_update.supplier_id).first()
        if not supplier:
            raise ValueError("供应商不存在")
        db_po.supplier_id = purchase_update.supplier_id
    
    if purchase_update.currency is not None:
        db_po.currency = purchase_update.currency
    
    if purchase_update.status is not None:
        db_po.status = purchase_update.status
    
    if purchase_update.items is not None and len(purchase_update.items) > 0:
        db.query(PoPurchaseOrderItem).filter(PoPurchaseOrderItem.po_id == po_id).delete()
        
        total_amount = 0
        for item in purchase_update.items:
            product = db.query(PrdProduct).filter(PrdProduct.id == item.product_id).first()
            
            total_volume = 0
            cartons = 0
            if product and product.carton_volume_m3 and product.units_per_carton:
                cartons = VolumeCalculator.calculate_cartons(item.quantity, product.units_per_carton)
                total_volume = cartons * product.carton_volume_m3
            
            total_price = item.quantity * item.unit_price
            total_amount += total_price
            
            db_item = PoPurchaseOrderItem(
                po_id=po_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=total_price,
                cartons=cartons,
                total_volume_m3=total_volume,
                remark=item.remark
            )
            db.add(db_item)
        
        db_po.total_amount = total_amount
    
    db.commit()
    db.refresh(db_po)
    return db_po

def create_1688_purchase(db: Session, purchase_data):
    db_purchase = Po1688Purchase(
        pi_id=purchase_data.pi_id,
        url=purchase_data.url,
        product_name=purchase_data.product_name,
        quantity=purchase_data.quantity,
        unit_price=purchase_data.unit_price,
        freight=purchase_data.freight,
        payment_method=purchase_data.payment_method,
        gross_weight_kg=purchase_data.gross_weight_kg
    )
    db.add(db_purchase)
    db.commit()
    db.refresh(db_purchase)
    return db_purchase

def get_1688_purchases(db: Session, pi_id: int = None, skip: int = 0, limit: int = 100):
    query = db.query(Po1688Purchase)
    if pi_id is not None:
        query = query.filter(Po1688Purchase.pi_id == pi_id)
    return query.offset(skip).limit(limit).all()
