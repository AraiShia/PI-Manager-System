"""
数据库迁移脚本：移除 prd_product_supplier 表的唯一约束，支持同一产品对应同一供应商的多个方案
"""
import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'pimain.db')
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查是否有唯一约束
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='prd_product_supplier'")
        result = cursor.fetchone()
        
        if result and 'UNIQUE(product_id, supplier_id)' in result[0]:
            print("检测到唯一约束，开始迁移...")
            
            # 1. 创建新表（无唯一约束）
            cursor.execute("""
                CREATE TABLE prd_product_supplier_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    supplier_id INTEGER NOT NULL,
                    factory_code VARCHAR(50) NOT NULL,
                    purchase_price DECIMAL(15, 4),
                    currency VARCHAR(10),
                    units_per_carton INTEGER,
                    carton_length_cm DECIMAL(10, 2),
                    carton_width_cm DECIMAL(10, 2),
                    carton_height_cm DECIMAL(10, 2),
                    gross_weight_kg DECIMAL(10, 4),
                    moq INTEGER,
                    lead_time_days INTEGER,
                    purchase_channel VARCHAR(100),
                    remark VARCHAR(500),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME,
                    FOREIGN KEY (product_id) REFERENCES prd_product(id),
                    FOREIGN KEY (supplier_id) REFERENCES sup_supplier(id)
                )
            """)
            
            # 2. 复制数据
            cursor.execute("""
                INSERT INTO prd_product_supplier_new 
                SELECT id, product_id, supplier_id, factory_code, purchase_price, currency,
                       units_per_carton, carton_length_cm, carton_width_cm, carton_height_cm,
                       gross_weight_kg, moq, lead_time_days, purchase_channel, remark, created_at, updated_at
                FROM prd_product_supplier
            """)
            
            # 3. 删除旧表
            cursor.execute("DROP TABLE prd_product_supplier")
            
            # 4. 重命名新表
            cursor.execute("ALTER TABLE prd_product_supplier_new RENAME TO prd_product_supplier")
            
            conn.commit()
            print("迁移成功！已移除唯一约束，现在支持同一产品对应同一供应商的多个方案")
        else:
            print("未检测到唯一约束或表结构已更新，无需迁移")
            
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
