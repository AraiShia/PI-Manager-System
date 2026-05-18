from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from models.quote import QoQuote, QoQuoteItem
from models import (
    PiProformaInvoice,
    PiPriceHistory,
    CrmCustomer,
    PrdProduct,
    PoPurchaseOrder,
    PoPurchaseOrderItem
)
from schemas.quote import QuoteCreate, QuoteItemCreate
from utils.number_generator import NumberGenerator


def _parse_date(date_value):
    """解析日期字符串"""
    if not date_value:
        return None
    if isinstance(date_value, datetime):
        return date_value
    if isinstance(date_value, str):
        try:
            return datetime.strptime(date_value[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return None


def create_quote(db: Session, quote: QuoteCreate) -> QoQuote:
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == quote.customer_id).first()
    if not customer:
        raise ValueError("客户不存在")

    quote_no = NumberGenerator.generate_quote_no(db, quote.dept_id, customer.customer_code)
    total_amount = sum(item.quantity * item.unit_price for item in quote.items)

    db_quote = QoQuote(
        quote_no=quote_no,
        dept_id=quote.dept_id,
        customer_id=quote.customer_id,
        total_amount=total_amount,
        currency=quote.currency,
        valid_until=_parse_date(quote.valid_until),
        status=1,
        remark=getattr(quote, 'remark', None)
    )

    db.add(db_quote)
    db.commit()
    db.refresh(db_quote)

    for item in quote.items:
        product = db.query(PrdProduct).filter(PrdProduct.id == item.product_id).first()

        db_item = QoQuoteItem(
            quote_id=db_quote.id,
            product_id=item.product_id,
            oe_number=item.oe_number or (product.oe_number if product else None),
            customer_code=item.customer_code or customer.customer_code,
            detail_desc=item.detail_desc or (product.description if product else None),
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.quantity * item.unit_price,
            remark=item.remark
        )
        db.add(db_item)

    db.commit()
    db.refresh(db_quote)
    return db_quote


def get_quote(db: Session, quote_id: int) -> QoQuote:
    return db.query(QoQuote).filter(QoQuote.id == quote_id).first()


def get_quotes(db: Session, skip: int = 0, limit: int = 100, status: int = None, customer_id: int = None):
    query = db.query(QoQuote).order_by(QoQuote.created_at.desc())
    if status is not None:
        query = query.filter(QoQuote.status == status)
    if customer_id is not None:
        query = query.filter(QoQuote.customer_id == customer_id)
    return query.offset(skip).limit(limit).all()


def get_quote_with_items(db: Session, quote_id: int):
    """获取报价单详情，包含客户信息和明细"""
    quote = db.query(QoQuote).filter(QoQuote.id == quote_id).first()
    if not quote:
        return None

    customer = db.query(CrmCustomer).filter(CrmCustomer.id == quote.customer_id).first()
    customer_name = customer.customer_name if customer else None

    items = db.query(QoQuoteItem).filter(QoQuoteItem.quote_id == quote_id).all()

    items_data = []
    for item in items:
        items_data.append({
            "id": item.id,
            "quote_id": item.quote_id,
            "product_id": item.product_id,
            "oe_number": item.oe_number,
            "customer_code": item.customer_code,
            "detail_desc": item.detail_desc,
            "quantity": float(item.quantity) if item.quantity else 0,
            "unit_price": float(item.unit_price) if item.unit_price else 0,
            "total_price": float(item.total_price) if item.total_price else 0,
            "remark": item.remark
        })

    return {
        "id": quote.id,
        "quote_no": quote.quote_no,
        "dept_id": quote.dept_id,
        "customer_id": quote.customer_id,
        "customer_name": customer_name,
        "currency": quote.currency,
        "total_amount": float(quote.total_amount) if quote.total_amount else 0,
        "valid_until": quote.valid_until.isoformat()[:10] if quote.valid_until else None,
        "status": quote.status,
        "remark": quote.remark,
        "created_at": quote.created_at.isoformat() if quote.created_at else None,
        "items": items_data
    }


def get_latest_price_by_customer_product(db: Session, customer_id: int, product_id: int) -> dict:
    """获取客户采购该产品的最后一次价格（通过PI->采购单链路）"""
    # 获取该客户所有PI
    pi_id_list = [pi.id for pi in db.query(PiProformaInvoice.id).filter(
        PiProformaInvoice.customer_id == customer_id
    ).all()]

    if pi_id_list:
        # 获取这些PI对应的采购单ID
        po_id_list = [po.id for po in db.query(PoPurchaseOrder.id).filter(
            PoPurchaseOrder.pi_id.in_(pi_id_list)
        ).all()]

        if po_id_list:
            # PoPurchaseOrderItem 没有 created_at，通过关联 PoPurchaseOrder 排序
            result = db.query(PoPurchaseOrderItem, PrdProduct, PoPurchaseOrder).join(
                PrdProduct, PoPurchaseOrderItem.product_id == PrdProduct.id
            ).join(
                PoPurchaseOrder, PoPurchaseOrderItem.po_id == PoPurchaseOrder.id
            ).filter(
                PoPurchaseOrderItem.po_id.in_(po_id_list),
                PoPurchaseOrderItem.product_id == product_id
            ).order_by(PoPurchaseOrder.created_at.desc()).first()

            if result:
                item, product, po = result
                return {
                    "product_id": product_id,
                    "product_code": product.product_code,
                    "oe_number": product.oe_number,
                    "customer_code": None,
                    "unit_price": float(item.unit_price) if item.unit_price else 0,
                    "quantity": float(item.quantity) if item.quantity else 0,
                    "purchase_date": po.created_at
                }

    # 没有采购历史，返回产品基本信息
    product = db.query(PrdProduct).filter(PrdProduct.id == product_id).first()
    if product:
        return {
            "product_id": product_id,
            "product_code": product.product_code,
            "oe_number": product.oe_number,
            "customer_code": None,
            "unit_price": 0,
            "quantity": 0,
            "purchase_date": None
        }
    return None


def get_customer_products_with_prices(db: Session, customer_id: int):
    """获取该客户所有采购过的产品及其最后一次采购价格"""
    pi_id_list = [pi.id for pi in db.query(PiProformaInvoice.id).filter(
        PiProformaInvoice.customer_id == customer_id
    ).all()]

    if not pi_id_list:
        return []

    po_id_list = [po.id for po in db.query(PoPurchaseOrder.id).filter(
        PoPurchaseOrder.pi_id.in_(pi_id_list)
    ).all()]

    if not po_id_list:
        return []

    # 通过 PoPurchaseOrder.created_at 排序（PoPurchaseOrderItem 没有 created_at）
    items = db.query(PoPurchaseOrderItem, PrdProduct, PoPurchaseOrder).join(
        PrdProduct, PoPurchaseOrderItem.product_id == PrdProduct.id
    ).join(
        PoPurchaseOrder, PoPurchaseOrderItem.po_id == PoPurchaseOrder.id
    ).filter(
        PoPurchaseOrderItem.po_id.in_(po_id_list)
    ).order_by(PoPurchaseOrder.created_at.desc()).all()

    # 按产品ID分组，取最新的价格
    product_prices = {}
    for item, product, po in items:
        if product.id not in product_prices:
            product_prices[product.id] = {
                "product_id": product.id,
                "product_code": product.product_code,
                "oe_number": product.oe_number,
                "customer_code": None,
                "detail_desc": product.description,
                "unit_price": float(item.unit_price) if item.unit_price else 0,
                "last_quantity": float(item.quantity) if item.quantity else 0,
                "last_purchase_date": po.created_at
            }

    return list(product_prices.values())


def get_price_history_by_customer_product(db: Session, customer_id: int, product_id: int):
    """获取客户采购该产品的历史价格"""
    pi_id_list = [pi.id for pi in db.query(PiProformaInvoice.id).filter(
        PiProformaInvoice.customer_id == customer_id
    ).all()]

    if not pi_id_list:
        return []

    po_id_list = [po.id for po in db.query(PoPurchaseOrder.id).filter(
        PoPurchaseOrder.pi_id.in_(pi_id_list)
    ).all()]

    if not po_id_list:
        return []

    items = db.query(PoPurchaseOrderItem, PrdProduct, PoPurchaseOrder).join(
        PrdProduct, PoPurchaseOrderItem.product_id == PrdProduct.id
    ).join(
        PoPurchaseOrder, PoPurchaseOrderItem.po_id == PoPurchaseOrder.id
    ).filter(
        PoPurchaseOrderItem.po_id.in_(po_id_list),
        PoPurchaseOrderItem.product_id == product_id
    ).order_by(PoPurchaseOrder.created_at.desc()).limit(10).all()

    result = []
    for item, product, po in items:
        result.append({
            "product_id": product_id,
            "product_code": product.product_code,
            "oe_number": product.oe_number,
            "customer_code": None,
            "unit_price": float(item.unit_price) if item.unit_price else 0,
            "quantity": float(item.quantity) if item.quantity else 0,
            "purchase_date": po.created_at
        })

    return result


def convert_quote_to_pi(db: Session, quote_id: int):
    quote = get_quote(db, quote_id)
    if not quote:
        raise ValueError("报价单不存在")

    from crud.pi import create_pi_invoice
    from schemas.pi import PIInvoiceCreate, PIInvoiceItemCreate, PIPaymentStageCreate

    items = []
    for item in quote.items:
        items.append(PIInvoiceItemCreate(
            product_id=item.product_id,
            oe_number=item.oe_number,
            customer_code=item.customer_code,
            detail_desc=item.detail_desc,
            quantity=item.quantity,
            unit_price=item.unit_price,
            remark=item.remark
        ))

    pi_create = PIInvoiceCreate(
        dept_id=quote.dept_id,
        customer_id=quote.customer_id,
        currency=quote.currency,
        items=items,
        payment_stages=[
            PIPaymentStageCreate(
                stage_type='deposit',
                stage_no=1,
                amount=float(quote.total_amount or 0) * 0.3,
                due_date=datetime.now() + timedelta(days=7)
            ),
            PIPaymentStageCreate(
                stage_type='balance',
                stage_no=2,
                amount=float(quote.total_amount or 0) * 0.7,
                due_date=datetime.now() + timedelta(days=30)
            )
        ]
    )

    pi = create_pi_invoice(db, pi_create)
    quote.status = 2
    db.commit()
    return pi


def update_quote(db: Session, quote_id: int, quote_data: dict) -> QoQuote:
    """更新报价单"""
    db_quote = get_quote(db, quote_id)
    if not db_quote:
        raise ValueError("报价单不存在")

    if 'valid_until' in quote_data:
        db_quote.valid_until = _parse_date(quote_data['valid_until'])
    if 'remark' in quote_data:
        db_quote.remark = quote_data['remark']
    if 'status' in quote_data:
        db_quote.status = quote_data['status']

    if 'items' in quote_data:
        db.query(QoQuoteItem).filter(QoQuoteItem.quote_id == quote_id).delete()

        total_amount = 0
        customer = db.query(CrmCustomer).filter(CrmCustomer.id == db_quote.customer_id).first()
        for item_data in quote_data['items']:
            product = db.query(PrdProduct).filter(PrdProduct.id == item_data['product_id']).first()

            db_item = QoQuoteItem(
                quote_id=quote_id,
                product_id=item_data['product_id'],
                oe_number=item_data.get('oe_number') or (product.oe_number if product else None),
                customer_code=item_data.get('customer_code') or (customer.customer_code if customer else None),
                detail_desc=item_data.get('detail_desc') or (product.description if product else None),
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                total_price=item_data['quantity'] * item_data['unit_price'],
                remark=item_data.get('remark')
            )
            db.add(db_item)
            total_amount += item_data['quantity'] * item_data['unit_price']

        db_quote.total_amount = total_amount

    db.commit()
    db.refresh(db_quote)
    return db_quote


def update_quote_status(db: Session, quote_id: int, status: int) -> QoQuote:
    db_quote = get_quote(db, quote_id)
    if not db_quote:
        return None
    db_quote.status = status
    db.commit()
    db.refresh(db_quote)
    return db_quote


def delete_quote(db: Session, quote_id: int):
    """删除报价单及其明细"""
    db_quote = get_quote(db, quote_id)
    if not db_quote:
        raise ValueError("报价单不存在")
    # 先删除关联的明细
    db.query(QoQuoteItem).filter(QoQuoteItem.quote_id == quote_id).delete()
    db.delete(db_quote)
    db.commit()
