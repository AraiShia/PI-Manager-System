"""
产品编号生成工具
格式: 客户编号 + 部门编号 + 产品类别(2位) + 年份(2位) + 序号(4位36进制)
示例: A01S01240001
"""
from datetime import datetime
from sqlalchemy.orm import Session
from models.customer_product import PrdCustomerProduct


class ProductCodeGenerator:
    """产品编号生成器"""
    
    # 部门编号映射
    DEPT_CODES = {
        'S': '索英普',
        'W': '维那',
        'M': '马迪那',
        'D': '银达',
    }
    
    # 36进制字符表（0-9, A-Z，共36位）
    CHARSET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    
    def __init__(self, db: Session):
        self.db = db
    
    def int_to_base36(self, num: int) -> str:
        """整数转36进制，固定4位"""
        if num <= 0:
            return '0000'
        
        result = ''
        while num > 0:
            num -= 1
            result = self.CHARSET[num % 36] + result
            num //= 36
        
        # 补齐4位
        return result.zfill(4)
    
    def base36_to_int(self, s: str) -> int:
        """36进制转整数"""
        if not s:
            return 0
        return int(s, 36)
    
    def get_current_year_code(self) -> str:
        """获取当前年份后两位，如 24"""
        year = datetime.now().year
        return str(year)[-2:]
    
    def get_next_sequence(self, customer_code: str, dept_code: str, category_code: str) -> str:
        """
        获取下一个序号
        规则: 客户编号+部门+类别+年份 相同的记录中找最大序号
        """
        year_code = self.get_current_year_code()
        prefix = f"{customer_code}{dept_code}{category_code}{year_code}"
        
        # 查找该前缀下的最大序号
        products = self.db.query(PrdCustomerProduct).filter(
            PrdCustomerProduct.system_code.like(f"{prefix}%")
        ).all()
        
        max_seq = 0
        for p in products:
            if p.system_code and len(p.system_code) >= len(prefix) + 4:
                seq_str = p.system_code[len(prefix):len(prefix)+4]
                try:
                    seq = self.base36_to_int(seq_str)
                    if seq > max_seq:
                        max_seq = seq
                except:
                    pass
        
        return self.int_to_base36(max_seq + 1)
    
    def generate_code(self, customer_code: str, dept_code: str, category_code: str) -> str:
        """
        生成完整的产品编号
        格式: 客户编号 + 部门编号 + 类别(2位) + 年份(2位) + 序号(4位)
        """
        if not customer_code or not dept_code or not category_code:
            raise ValueError("客户编号、部门编号、产品类别都不能为空")
        
        # 验证部门编号
        dept_code = dept_code.upper()
        if dept_code not in self.DEPT_CODES:
            raise ValueError(f"无效的部门编号: {dept_code}，必须是 S/W/M/D 之一")
        
        # 补齐类别为2位
        category_code = category_code.zfill(2)
        
        # 获取下一个序号
        seq = self.get_next_sequence(customer_code, dept_code, category_code)
        
        # 拼接完整编号
        year_code = self.get_current_year_code()
        return f"{customer_code}{dept_code}{category_code}{year_code}{seq}"
    
    def generate_code_from_customer(self, customer_id: int, dept_code: str, category_code: str) -> str:
        """
        根据客户ID生成产品编号
        自动获取客户编号
        """
        from models.customer import CrmCustomer
        
        customer = self.db.query(CrmCustomer).filter(CrmCustomer.id == customer_id).first()
        if not customer:
            raise ValueError(f"客户ID={customer_id} 不存在")
        
        customer_code = customer.customer_code
        if not customer_code:
            raise ValueError(f"客户ID={customer_id} 的 customer_code 为空")
        
        return self.generate_code(customer_code, dept_code, category_code)


def generate_product_code(db: Session, customer_id: int, dept_code: str, category_code: str) -> str:
    """便捷函数：生成产品编号"""
    generator = ProductCodeGenerator(db)
    return generator.generate_code_from_customer(customer_id, dept_code, category_code)