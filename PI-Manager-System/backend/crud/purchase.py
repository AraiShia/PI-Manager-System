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
        status=1,
        dept_id=purchase.dept_id
    )

    db.add(db_po)
    db.commit()
    db.refresh(db_po)

    for item in purchase.items:
        product = db.query(PrdProduct).filter(PrdProduct.id == item.product_id).first()

        cartons_estimated = 0
        volume_estimated_m3 = 0
        if product and product.carton_volume_m3 and product.units_per_carton:
            cartons_estimated = int(item.quantity / product.units_per_carton) if product.units_per_carton else 0
            volume_estimated_m3 = cartons_estimated * float(product.carton_volume_m3) if product.carton_volume_m3 else 0

        db_item = PoPurchaseOrderItem(
            po_id=db_po.id,
            product_id=item.product_id,
            pi_item_id=item.pi_item_id,
            factory_code=item.factory_code,
            product_image=item.product_image,
            color=item.color,
            detail_requirement=item.detail_requirement,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.quantity * item.unit_price,
            price_ex_factory=item.price_ex_factory,
            price_ex_factory_tax=item.price_ex_factory_tax,
            price_fob=item.price_fob,
            price_fob_tax=item.price_fob_tax,
            cartons_estimated=cartons_estimated,
            volume_estimated_m3=volume_estimated_m3,
            inbound_status=1  # 默认已采购状态（黄色）
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

def get_purchase_orders_by_supplier(db: Session, supplier_id: int):
    return db.query(PoPurchaseOrder).filter(PoPurchaseOrder.supplier_id == supplier_id).all()

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

    if purchase_update.status is not None:
        db_po.status = purchase_update.status

    if purchase_update.items is not None and len(purchase_update.items) > 0:
        db.query(PoPurchaseOrderItem).filter(PoPurchaseOrderItem.po_id == po_id).delete()

        total_amount = 0
        for item in purchase_update.items:
            product = db.query(PrdProduct).filter(PrdProduct.id == item.product_id).first()

            cartons_estimated = 0
            volume_estimated_m3 = 0
            if product and product.carton_volume_m3 and product.units_per_carton:
                cartons_estimated = int(item.quantity / product.units_per_carton) if product.units_per_carton else 0
                volume_estimated_m3 = cartons_estimated * float(product.carton_volume_m3) if product.carton_volume_m3 else 0

            total_price = item.quantity * item.unit_price
            total_amount += total_price

            db_item = PoPurchaseOrderItem(
                po_id=po_id,
                product_id=item.product_id,
                pi_item_id=item.pi_item_id,
                factory_code=item.factory_code,
                product_image=item.product_image,
                color=item.color,
                detail_requirement=item.detail_requirement,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=total_price,
                price_ex_factory=item.price_ex_factory,
                price_ex_factory_tax=item.price_ex_factory_tax,
                price_fob=item.price_fob,
                price_fob_tax=item.price_fob_tax,
                cartons_estimated=cartons_estimated,
                volume_estimated_m3=volume_estimated_m3,
                inbound_status=1
            )
            db.add(db_item)

        db_po.total_amount = total_amount

    db.commit()
    db.refresh(db_po)
    return db_po

def create_1688_purchase(db: Session, purchase_data):
    db_purchase = Po1688Purchase(
        pi_id=purchase_data.pi_id,
        po_id=purchase_data.po_id,
        product_id=purchase_data.product_id,
        supplier_name=purchase_data.supplier_name,
        product_url=purchase_data.product_url,
        product_remark=purchase_data.product_remark,
        color=purchase_data.color,
        invoice_type=purchase_data.invoice_type,
        labeling_fee=purchase_data.labeling_fee,
        shipping_fee=purchase_data.shipping_fee,
        shipping_method=purchase_data.shipping_method,
        carton_count=purchase_data.carton_count,
        freight=purchase_data.freight,
        payment_method=purchase_data.payment_method,
        gross_weight=purchase_data.gross_weight,
        status=1
    )
    db.add(db_purchase)
    db.commit()
    db.refresh(db_purchase)
    return db_purchase

def get_1688_purchases(db: Session, pi_id: int = None, po_id: int = None, skip: int = 0, limit: int = 100):
    query = db.query(Po1688Purchase)
    if pi_id is not None:
        query = query.filter(Po1688Purchase.pi_id == pi_id)
    if po_id is not None:
        query = query.filter(Po1688Purchase.po_id == po_id)
    return query.offset(skip).limit(limit).all()

def get_1688_purchase(db: Session, purchase_id: int):
    return db.query(Po1688Purchase).filter(Po1688Purchase.id == purchase_id).first()

def update_1688_purchase(db: Session, purchase_id: int, purchase_data):
    db_purchase = get_1688_purchase(db, purchase_id)
    if not db_purchase:
        return None

    if purchase_data.supplier_name is not None:
        db_purchase.supplier_name = purchase_data.supplier_name
    if purchase_data.product_url is not None:
        db_purchase.product_url = purchase_data.product_url
    if purchase_data.product_remark is not None:
        db_purchase.product_remark = purchase_data.product_remark
    if purchase_data.color is not None:
        db_purchase.color = purchase_data.color
    if purchase_data.invoice_type is not None:
        db_purchase.invoice_type = purchase_data.invoice_type
    if purchase_data.labeling_fee is not None:
        db_purchase.labeling_fee = purchase_data.labeling_fee
    if purchase_data.shipping_fee is not None:
        db_purchase.shipping_fee = purchase_data.shipping_fee
    if purchase_data.shipping_method is not None:
        db_purchase.shipping_method = purchase_data.shipping_method
    if purchase_data.carton_count is not None:
        db_purchase.carton_count = purchase_data.carton_count
    if purchase_data.freight is not None:
        db_purchase.freight = purchase_data.freight
    if purchase_data.payment_method is not None:
        db_purchase.payment_method = purchase_data.payment_method
    if purchase_data.gross_weight is not None:
        db_purchase.gross_weight = purchase_data.gross_weight
    if purchase_data.status is not None:
        db_purchase.status = purchase_data.status

    db.commit()
    db.refresh(db_purchase)
    return db_purchase