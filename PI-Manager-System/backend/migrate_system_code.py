"""
迁移：为客户产品表添加系统产品编号字段和软删除时间字段
"""
from app.database import engine, SessionLocal
from sqlalchemy import inspect, text


def migrate():
    """执行迁移"""
    inspector = inspect(engine)
    
    print("[INFO] 检查数据库结构...")
    
    # 检查表是否存在
    if 'prd_customer_product' not in inspector.get_table_names():
        print("[ERROR] prd_customer_product 表不存在")
        return
    
    # 检查 system_code 列
    columns = [col['name'] for col in inspector.get_columns('prd_customer_product')]
    
    if 'system_code' not in columns:
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE prd_customer_product 
                    ADD COLUMN system_code VARCHAR(50)
                """))
                conn.commit()
            print("[SUCCESS] 添加 system_code 列成功")
        except Exception as e:
            print(f"[ERROR] 添加 system_code 列失败: {e}")
    
    # 检查 deleted_at 列
    if 'deleted_at' not in columns:
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE prd_customer_product 
                    ADD COLUMN deleted_at DATETIME
                """))
                conn.commit()
            print("[SUCCESS] 添加 deleted_at 列成功")
        except Exception as e:
            print(f"[ERROR] 添加 deleted_at 列失败: {e}")


def verify():
    """验证表结构"""
    inspector = inspect(engine)
    
    print("\n[INFO] 当前表结构:")
    if 'prd_customer_product' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('prd_customer_product')]
        print(f"  prd_customer_product: {columns}")
    else:
        print("  prd_customer_product: 不存在")


if __name__ == "__main__":
    print("=" * 50)
    print("客户产品系统编号迁移")
    print("=" * 50)
    
    migrate()
    verify()
    
    print("\n" + "=" * 50)
    print("迁移完成!")
    print("=" * 50)