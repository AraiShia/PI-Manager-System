"""
为已有产品生成系统编号
"""
from app.database import SessionLocal
from models.customer_product import PrdCustomerProduct
from models.customer import CrmCustomer
from datetime import datetime


def generate_codes():
    db = SessionLocal()
    
    try:
        # 查找所有没有 system_code 的产品
        products = db.query(PrdCustomerProduct).filter(
            PrdCustomerProduct.system_code == None
        ).all()
        
        print(f"[INFO] 找到 {len(products)} 个产品需要生成编号")
        
        CHARSET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        year_code = str(datetime.now().year)[-2:]
        dept_code = 'S'  # 默认部门
        
        for idx, product in enumerate(products, 1):
            # 获取客户编号
            customer = db.query(CrmCustomer).filter(CrmCustomer.id == product.customer_id).first()
            customer_code = customer.customer_code if customer and customer.customer_code else 'XX'
            
            # 获取类别
            category_code = product.category_id.zfill(2) if product.category_id else '01'
            
            # 计算序号
            seq_num = idx
            seq_str = ''
            num = seq_num
            while num > 0:
                num -= 1
                seq_str = CHARSET[num % 36] + seq_str
                num //= 36
            seq_str = seq_str.zfill(4)
            
            # 生成编号
            system_code = f"{customer_code}{dept_code}{category_code}{year_code}{seq_str}"
            
            # 更新产品
            product.system_code = system_code
            print(f"[{idx}] 产品ID={product.id}: {product.product_name} -> {system_code}")
        
        db.commit()
        print(f"\n[SUCCESS] 已为 {len(products)} 个产品生成编号")
        
    except Exception as e:
        print(f"[ERROR] 失败: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("为已有产品生成系统编号")
    print("=" * 50)
    generate_codes()
