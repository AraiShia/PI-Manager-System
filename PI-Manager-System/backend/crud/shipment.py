from sqlalchemy.orm import Session
from datetime import datetime
from models import (
    ShShipment, 
    ShShipmentItem,
    InvInventory,
    InvInventoryLog,
    PiProformaInvoice,
    PrdProduct
)
from schemas import ShipmentCreate, ShipmentItemCreate
from utils.volume_calculator import VolumeCalculator

def create_shipment(db: Session, shipment: ShipmentCreate) -> ShShipment:
    pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == shipment.pi_id).first()
    if not pi:
        raise ValueError("PI不存在")
    
    total_amount = 0
    total_volume = 0
    
    db_shipment = ShShipment(
        pi_id=shipment.pi_id,
        shipment_date=shipment.shipment_date,
        currency=shipment.currency,
        status=1,
        dept_id=shipment.dept_id
    )
    
    db.add(db_shipment)
    db.commit()
    db.refresh(db_shipment)
    
    for item in shipment.items:
        product = db.query(PrdProduct).filter(PrdProduct.id == item.product_id).first()
        
        inventory = db.query(InvInventory).filter(
            InvInventory.product_id == item.product_id,
            InvInventory.customer_id == pi.customer_id,
            InvInventory.pending_quantity >= item.quantity
        ).first()
        
        if not inventory:
            raise ValueError(f"产品{item.product_id}库存不足")
        
        total_price = item.quantity * (item.unit_price or 0)
        total_amount += total_price
        
        cartons = 0
        volume = 0
        if product and product.carton_volume_m3 and product.units_per_carton:
            cartons = VolumeCalculator.calculate_cartons(item.quantity, product.units_per_carton)
            volume = cartons * product.carton_volume_m3
            total_volume += volume
        
        db_item = ShShipmentItem(
            shipment_id=db_shipment.id,
            product_id=item.product_id,
            inventory_id=inventory.id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=total_price,
            cartons=cartons,
            volume_m3=volume,
            remark=item.remark
        )
        db.add(db_item)
    
    db_shipment.total_amount = total_amount
    db_shipment.total_volume_m3 = total_volume
    
    db.commit()
    db.refresh(db_shipment)
    
    return db_shipment

def confirm_shipment(db: Session, shipment_id: int) -> ShShipment:
    shipment = db.query(ShShipment).filter(ShShipment.id == shipment_id).first()
    if not shipment:
        raise ValueError("出货单不存在")
    
    for item in shipment.items:
        inventory = db.query(InvInventory).filter(InvInventory.id == item.inventory_id).first()
        if not inventory:
            raise ValueError("库存不存在")
        
        if inventory.pending_quantity < item.quantity:
            raise ValueError(f"产品{item.product_id}可出数量不足")
        
        inventory.pending_quantity -= item.quantity
        inventory.shipped_quantity += item.quantity
        inventory.current_location = 'IN_TRANSIT'
        
        db.add(inventory)
        
        log = InvInventoryLog(
            product_id=item.product_id,
            customer_id=inventory.customer_id,
            pi_id=shipment.pi_id,
            change_type='SHIP',
            change_quantity=-item.quantity,
            ref_type='SH',
            ref_id=shipment_id
        )
        db.add(log)
    
    shipment.status = 2
    db.commit()
    db.refresh(shipment)
    
    return shipment

def get_shipment(db: Session, shipment_id: int) -> ShShipment:
    return db.query(ShShipment).filter(ShShipment.id == shipment_id).first()

def get_shipments(db: Session, skip: int = 0, limit: int = 100, pi_id: int = None, status: int = None):
    query = db.query(ShShipment)
    if pi_id is not None:
        query = query.filter(ShShipment.pi_id == pi_id)
    if status is not None:
        query = query.filter(ShShipment.status == status)
    return query.offset(skip).limit(limit).all()

def get_available_inventory(db: Session, pi_id: int):
    pi = db.query(PiProformaInvoice).filter(PiProformaInvoice.id == pi_id).first()
    if not pi:
        return []
    
    return db.query(InvInventory).filter(
        InvInventory.customer_id == pi.customer_id,
        InvInventory.pending_quantity > 0
    ).all()
