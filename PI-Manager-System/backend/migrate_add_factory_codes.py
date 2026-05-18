"""
数据库迁移脚本：为 sup_supplier 表添加 factory_codes 字段
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
        cursor.execute("PRAGMA table_info(sup_supplier)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'factory_codes' in columns:
            print("factory_codes 字段已存在，无需迁移")
            return
        
        # 添加 factory_codes 字段
        cursor.execute("ALTER TABLE sup_supplier ADD COLUMN factory_codes VARCHAR(500)")
        conn.commit()
        print("成功添加 factory_codes 字段到 sup_supplier 表")
        
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
