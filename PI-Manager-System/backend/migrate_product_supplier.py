"""
数据库迁移脚本：为 prd_product_supplier 表添加新字段
"""
import sqlite3
import os

def migrate():
    # 数据库路径
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'pimain.db')
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(prd_product_supplier)")
        columns = [col[1] for col in cursor.fetchall()]
        
        new_columns = [
            ('purchase_price', 'DECIMAL(15, 4)'),
            ('currency', 'VARCHAR(10)'),
            ('units_per_carton', 'INTEGER'),
            ('carton_length_cm', 'DECIMAL(10, 2)'),
            ('carton_width_cm', 'DECIMAL(10, 2)'),
            ('carton_height_cm', 'DECIMAL(10, 2)'),
            ('gross_weight_kg', 'DECIMAL(10, 4)'),
            ('moq', 'INTEGER'),
            ('lead_time_days', 'INTEGER'),
            ('remark', 'VARCHAR(500)'),
            ('updated_at', 'DATETIME')
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in columns:
                cursor.execute(f"ALTER TABLE prd_product_supplier ADD COLUMN {col_name} {col_type}")
                print(f"成功添加字段: {col_name}")
            else:
                print(f"字段已存在: {col_name}")
        
        conn.commit()
        print("迁移完成!")
        
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
