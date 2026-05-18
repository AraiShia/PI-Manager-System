# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为 prd_product_supplier 表添加新字段
- customer_id INTEGER (外键关联客户，可为空)
- special_requirements TEXT (特殊需求)
- is_default BOOLEAN DEFAULT 0 (是否默认方案)
"""
import sqlite3
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'pimain.db')

def migrate():
    """执行数据库迁移"""
    print(f"正在连接数据库: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print(f"错误: 数据库文件不存在: {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prd_product_supplier'")
        if not cursor.fetchone():
            print("错误: prd_product_supplier 表不存在")
            return False
        
        # 获取现有列信息
        cursor.execute("PRAGMA table_info(prd_product_supplier)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        print(f"现有列: {existing_columns}")
        
        # 添加 customer_id 字段
        if 'customer_id' not in existing_columns:
            print("正在添加 customer_id 字段...")
            cursor.execute("""
                ALTER TABLE prd_product_supplier 
                ADD COLUMN customer_id INTEGER 
                REFERENCES crm_customer(id)
            """)
            print("customer_id 字段添加成功")
        else:
            print("customer_id 字段已存在，跳过")
        
        # 添加 special_requirements 字段
        if 'special_requirements' not in existing_columns:
            print("正在添加 special_requirements 字段...")
            cursor.execute("""
                ALTER TABLE prd_product_supplier 
                ADD COLUMN special_requirements TEXT
            """)
            print("special_requirements 字段添加成功")
        else:
            print("special_requirements 字段已存在，跳过")
        
        # 添加 is_default 字段
        if 'is_default' not in existing_columns:
            print("正在添加 is_default 字段...")
            cursor.execute("""
                ALTER TABLE prd_product_supplier 
                ADD COLUMN is_default BOOLEAN DEFAULT 0
            """)
            print("is_default 字段添加成功")
        else:
            print("is_default 字段已存在，跳过")
        
        conn.commit()
        print("\n迁移完成!")
        
        # 验证迁移结果
        cursor.execute("PRAGMA table_info(prd_product_supplier)")
        final_columns = {row[1] for row in cursor.fetchall()}
        print(f"迁移后的列: {final_columns}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {str(e)}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
