from datetime import datetime
from sqlalchemy.orm import Session
from models import SysNumberRule, SysNumberHistory
from config.product_categories import get_category_code
import string
import random

class NumberGenerator:
    @staticmethod
    def generate_product_code(db: Session, dept_id: str, category_id: int) -> str:
        rule = db.query(SysNumberRule).filter(SysNumberRule.rule_type == "PRODUCT").first()
        if not rule:
            rule = SysNumberRule(
                rule_type="PRODUCT",
                rule_pattern="DEPT+CATEGORY+YEAR+SEQ",
                current_value=0
            )
            db.add(rule)
            db.commit()
        
        year = datetime.now().strftime("%y")
        rule.current_value += 1
        db.commit()
        
        category_code = str(category_id).zfill(2) if category_id else "01"
        sequence = str(rule.current_value).zfill(4)
        
        product_code = f"{dept_id}{category_code}{year}{sequence}"
        
        history = SysNumberHistory(
            rule_type="PRODUCT",
            generated_no=product_code,
            related_type="PRODUCT"
        )
        db.add(history)
        db.commit()
        
        return product_code

    @staticmethod
    def generate_pi_no(db: Session, dept_id: str, customer_code: str) -> str:
        rule = db.query(SysNumberRule).filter(SysNumberRule.rule_type == "PI").first()
        if not rule:
            rule = SysNumberRule(
                rule_type="PI",
                rule_pattern="DEPT+CUSTOMER+DATE+SEQ",
                current_value=0
            )
            db.add(rule)
            db.commit()
        
        date_str = datetime.now().strftime("%y%m%d")
        
        from models import PiProformaInvoice
        today_count = db.query(PiProformaInvoice).filter(
            PiProformaInvoice.dept_id == dept_id,
            PiProformaInvoice.created_at >= datetime.now().date()
        ).count()
        identifier = today_count + 1
        
        pi_no = f"{dept_id}{customer_code}{date_str}{identifier}"
        
        history = SysNumberHistory(
            rule_type="PI",
            generated_no=pi_no,
            related_type="PI"
        )
        db.add(history)
        db.commit()
        
        return pi_no

    @staticmethod
    def generate_po_no(db: Session, pi_no: str, supplier_code: str) -> str:
        from models import PoPurchaseOrder
        
        supplier_no = supplier_code.zfill(3) if supplier_code else "001"
        existing_count = db.query(PoPurchaseOrder).filter(
            PoPurchaseOrder.po_no.like(f"V{pi_no}-%")
        ).count()
        sequence = existing_count + 1
        
        po_no = f"V{pi_no}-{supplier_no}{str(sequence).zfill(2)}"
        
        history = SysNumberHistory(
            rule_type="PO",
            generated_no=po_no,
            related_type="PO"
        )
        db.add(history)
        db.commit()
        
        return po_no

    @staticmethod
    def generate_customer_code(db: Session) -> str:
        rule = db.query(SysNumberRule).filter(SysNumberRule.rule_type == "CUSTOMER").first()
        if not rule:
            rule = SysNumberRule(
                rule_type="CUSTOMER",
                rule_pattern="3CHAR",
                current_value=0
            )
            db.add(rule)
            db.commit()
        
        chars = string.ascii_uppercase + string.digits
        
        while True:
            code = ''.join(random.choices(chars, k=3))
            
            from models import CrmCustomer
            existing = db.query(CrmCustomer).filter(CrmCustomer.customer_code == code).first()
            if not existing:
                history = SysNumberHistory(
                    rule_type="CUSTOMER",
                    generated_no=code,
                    related_type="CUSTOMER"
                )
                db.add(history)
                db.commit()
                return code

    @staticmethod
    def generate_receipt_no(db: Session, dept_id: str) -> str:
        from models import ArCustomerPayment
        prefix = f"RC{dept_id}{datetime.now().strftime('%y%m%d')}"
        count = db.query(ArCustomerPayment).filter(
            ArCustomerPayment.receipt_no.like(f"{prefix}%")
        ).count()
        receipt_no = f"{prefix}{str(count + 1).zfill(3)}"
        
        history = SysNumberHistory(
            rule_type="RECEIPT",
            generated_no=receipt_no,
            related_type="RECEIPT"
        )
        db.add(history)
        db.commit()
        return receipt_no

    @staticmethod
    def generate_payment_no(db: Session, dept_id: str) -> str:
        from models import ApSupplierPayment
        prefix = f"PM{dept_id}{datetime.now().strftime('%y%m%d')}"
        count = db.query(ApSupplierPayment).filter(
            ApSupplierPayment.payment_no.like(f"{prefix}%")
        ).count()
        payment_no = f"{prefix}{str(count + 1).zfill(3)}"
        
        history = SysNumberHistory(
            rule_type="PAYMENT",
            generated_no=payment_no,
            related_type="PAYMENT"
        )
        db.add(history)
        db.commit()
        return payment_no

    @staticmethod
    def generate_ci_no(db: Session, pi_no: str) -> str:
        """生成CI号: C+PI号"""
        ci_no = f"C{pi_no}"
        
        history = SysNumberHistory(
            rule_type="CI",
            generated_no=ci_no,
            related_type="CI"
        )
        db.add(history)
        db.commit()
        return ci_no

    @staticmethod
    def generate_pl_no(db: Session, pi_no: str) -> str:
        """生成PL号: P+PI号"""
        pl_no = f"P{pi_no}"
        
        history = SysNumberHistory(
            rule_type="PL",
            generated_no=pl_no,
            related_type="PL"
        )
        db.add(history)
        db.commit()
        return pl_no

    @staticmethod
    def generate_quote_no(db: Session, dept_id: str, customer_code: str) -> str:
        """生成报价单号: Q+部门+客户+年月日-序号"""
        date_str = datetime.now().strftime("%y%m%d")
        
        from models import QoQuote
        today_count = db.query(QoQuote).filter(
            QoQuote.dept_id == dept_id,
            QoQuote.quote_no.like(f"Q%{dept_id}{customer_code}{date_str}%")
        ).count()
        sequence = today_count + 1
        
        quote_no = f"Q{dept_id}{customer_code}{date_str}-{sequence}"
        
        history = SysNumberHistory(
            rule_type="QUOTE",
            generated_no=quote_no,
            related_type="QUOTE"
        )
        db.add(history)
        db.commit()
        return quote_no
