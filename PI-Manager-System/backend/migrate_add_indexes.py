# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为 prd_product_supplier 表添加索引以优化搜索性能
"""
import sqlite3
import os

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
        
        # 检查并添加 factory_code 索引
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='ix_prd_product_supplier_factory_code'")
        if not cursor.fetchone():
            print("正在添加 factory_code 索引...")
            cursor.execute("CREATE INDEX ix_prd_product_supplier_factory_code ON prd_product_supplier(factory_code)")
            print("factory_code 索引添加成功")
        else:
            print("factory_code 索引已存在，跳过")
        
        # 检查并添加 product_id 索引
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='ix_prd_product_supplier_product_id'")
        if not cursor.fetchone():
            print("正在添加 product_id 索引...")
            cursor.execute("CREATE INDEX ix_prd_product_supplier_product_id ON prd_product_supplier(product_id)")
            print("product_id 索引添加成功")
        else:
            print("product_id 索引已存在，跳过")
        
        conn.commit()
        print("\n迁移完成!")
        
        # 验证索引
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='prd_product_supplier'")
        indexes = [row[0] for row in cursor.fetchall()]
        print(f"prd_product_supplier 表的索引: {indexes}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {str(e)}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
