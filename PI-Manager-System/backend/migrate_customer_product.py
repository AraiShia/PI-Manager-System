"""
迁移脚本：为客户产品管理更新表结构
"""
from app.database import engine, Base, SessionLocal
from sqlalchemy import inspect, text
import sys

def migrate():
    """执行迁移"""
    inspector = inspect(engine)
    
    print("[INFO] 检查并更新数据库结构...")
    
    # 检查 prd_customer_product 表
    if 'prd_customer_product' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('prd_customer_product')]
        print(f"[INFO] prd_customer_product 当前列: {columns}")
        
        # 如果存在 customer_product_code 列且模型中已移除，需要删除或设为 nullable
        if 'customer_product_code' in columns:
            try:
                # 检查是否有 NOT NULL 约束
                with engine.connect() as conn:
                    # 获取表创建语句（SQLite不支持直接查看约束，需要尝试删除列）
                    # 先将现有值设为 NULL 或默认值
                    conn.execute(text("UPDATE prd_customer_product SET customer_product_code = '' WHERE customer_product_code IS NULL"))
                    conn.commit()
                print("[INFO] 已处理 customer_product_code 列的 NULL 值")
            except Exception as e:
                print(f"[WARN] 处理 customer_product_code 失败: {e}")
        
        # 添加缺失的列
        new_columns = {
            'category_id': 'VARCHAR(10)',
            'sub_images': 'TEXT',
        }
        
        for col_name, col_type in new_columns.items():
            if col_name not in columns:
                try:
                    with engine.connect() as conn:
                        conn.execute(text(f"ALTER TABLE prd_customer_product ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                    print(f"[SUCCESS] 添加列: prd_customer_product.{col_name}")
                except Exception as e:
                    print(f"[WARN] 添加列 {col_name} 失败: {e}")
    
    # 检查并创建 prd_customer_product_code 表
    if 'prd_customer_product_code' not in inspector.get_table_names():
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE prd_customer_product_code (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_product_id INTEGER NOT NULL,
                        product_code VARCHAR(100) NOT NULL,
                        is_primary INTEGER DEFAULT 0,
                        remark VARCHAR(200),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (customer_product_id) REFERENCES prd_customer_product(id) ON DELETE CASCADE,
                        UNIQUE (customer_product_id, product_code)
                    )
                """))
                conn.commit()
            print("[SUCCESS] 创建表: prd_customer_product_code")
        except Exception as e:
            print(f"[ERROR] 创建表失败: {e}")
    else:
        print("[INFO] prd_customer_product_code 表已存在")
    
    # 创建索引
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cp_code_product_id ON prd_customer_product_code (customer_product_id)"))
            conn.commit()
        print("[SUCCESS] 创建索引完成")
    except Exception as e:
        print(f"[WARN] 创建索引失败: {e}")

def verify():
    """验证表结构"""
    inspector = inspect(engine)
    
    print("\n[INFO] 当前表结构:")
    
    tables = ['prd_customer_product', 'prd_customer_product_code', 'prd_customer_product_oe']
    
    for table in tables:
        if table in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns(table)]
            print(f"  ✓ {table}: {columns}")
        else:
            print(f"  ✗ {table}: 不存在")

if __name__ == "__main__":
    print("=" * 50)
    print("客户产品管理 - 数据库迁移")
    print("=" * 50)
    
    try:
        migrate()
        verify()
        print("\n" + "=" * 50)
        print("迁移完成!")
        print("=" * 50)
    except Exception as e:
        print(f"\n[ERROR] 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)