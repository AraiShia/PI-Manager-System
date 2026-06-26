from datetime import datetime
from sqlalchemy.orm import Session
from models import SysNumberRule, SysNumberHistory
from config.product_categories import get_category_code
import string
import random
import logging

logger = logging.getLogger(__name__)

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
        """自动生成PI号
        
        规则: PI{部门编号}{客户编号}{年份后两位}{月份}{日期}{一位36进制识别号}
        示例: PI D01C001260601A
        
        一位36进制识别号范围: 0-9, A-Z (共36个/天/客户)
        
        使用行锁保证并发安全，防止生成重复PI号
        注意: 此方法不执行commit，由调用者管理事务
        """
        from models import PiProformaInvoice
        import time
        
        dept_prefix = (dept_id.strip() if dept_id else 'D01').strip()
        customer_code_clean = (customer_code.strip() if customer_code else 'C001').strip()
        customer_prefix = customer_code_clean[:4] if len(customer_code_clean) >= 4 else customer_code_clean.ljust(4, '0')
        
        logger.info(f"[PI号生成] 输入参数 - dept_id='{dept_id}'(len={len(dept_id) if dept_id else 0}) -> dept_prefix='{dept_prefix}'(len={len(dept_prefix)}), customer_code='{customer_code}'(len={len(customer_code) if customer_code else 0}) -> customer_prefix='{customer_prefix}'(len={len(customer_prefix)})")
        
        today = datetime.now()
        date_part = today.strftime("%y%m%d")
        
        max_retries = 20
        pi_no = None
        
        for attempt in range(max_retries):
            try:
                last_pi = db.query(PiProformaInvoice).filter(
                    PiProformaInvoice.pi_no.like(f"PI{dept_prefix}{customer_prefix}{date_part}%")
                ).with_for_update().order_by(
                    PiProformaInvoice.pi_no.desc()
                ).first()
                
                if last_pi and last_pi.pi_no:
                    last_seq_char = last_pi.pi_no[-1]
                    logger.info(f"[PI号生成] 找到上一个PI - pi_no='{last_pi.pi_no}'(len={len(last_pi.pi_no)}), last_char='{last_seq_char}'")
                    try:
                        seq = int(last_seq_char, 36) + 1
                        if seq > 35:
                            seq = 0
                    except ValueError:
                        seq = 0
                else:
                    seq = 0
                
                seq_char = format(seq, '36').upper()
                pi_no = f"PI{dept_prefix}{customer_prefix}{date_part}{seq_char}"
                
                # 最终清理：移除所有空格
                pi_no = ''.join(pi_no.split())
                
                logger.info(f"[PI号生成] 生成候选 - pi_no='{pi_no}'(len={len(pi_no)}), 尝试次数={attempt+1}")
                
                existing = db.query(PiProformaInvoice).filter(
                    PiProformaInvoice.pi_no == pi_no
                ).with_for_update().first()
                
                if not existing:
                    logger.info(f"[PI号生成] 成功 - pi_no={pi_no}, 尝试次数={attempt+1}")
                    break
                else:
                    logger.warning(f"[PI号生成] 冲突重试 - pi_no={pi_no} 已存在, 重试 {attempt+1}/{max_retries}")
                    time.sleep(0.05 * (attempt + 1))
                    
            except Exception as e:
                logger.error(f"[PI号生成] 异常 - 尝试 {attempt+1}/{max_retries}: {e}")
                time.sleep(0.1 * (attempt + 1))
        
        if not pi_no:
            raise Exception(f"无法生成唯一PI号，已重试{max_retries}次")
        
        history = SysNumberHistory(
            rule_type="PI",
            generated_no=pi_no,
            related_type="PI"
        )
        db.add(history)
        
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
