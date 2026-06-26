"""数据库迁移脚本 - 添加 prd_product_audit_log 表

使用方法:
    cd backend
    python -c "from migrations.add_audit_log_table import upgrade; upgrade()"
    或
    python migrations/add_audit_log_table.py
"""
import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

from app.database import engine
from sqlalchemy import text


def upgrade():
    """创建审计日志表"""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS prd_product_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                action_type VARCHAR(50) NOT NULL DEFAULT 'TEMP_TO_FORMAL',
                operator_id INTEGER,
                operation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                original_data TEXT,
                updated_fields TEXT,
                source VARCHAR(100) DEFAULT 'order_detail_double_click',
                source_order_id INTEGER,
                duration_ms INTEGER DEFAULT 0,
                remark TEXT
            )
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_audit_log_product_id 
                ON prd_product_audit_log(product_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_audit_log_operation_time 
                ON prd_product_audit_log(operation_time)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_audit_log_action_type 
                ON prd_product_audit_log(action_type)
        """))
        
        conn.commit()
    print("[迁移] prd_product_audit_log 表创建完成")


def downgrade():
    """删除审计日志表"""
    sql = text("DROP TABLE IF EXISTS prd_product_audit_log;")
    with engine.connect() as conn:
        conn.execute(sql)
        conn.commit()
    print("[迁移] prd_product_audit_log 表已删除")


if __name__ == "__main__":
    print("=" * 50)
    print("审计日志表迁移脚本")
    print("=" * 50)
    print("\n请选择操作:")
    print("1. 创建表 (upgrade)")
    print("2. 删除表 (downgrade)")
    
    choice = input("\n请输入选项 (1/2): ").strip()
    
    if choice == "1":
        upgrade()
    elif choice == "2":
        confirm = input("确认删除表？此操作不可逆 (y/N): ").strip().lower()
        if confirm == 'y':
            downgrade()
        else:
            print("取消删除操作")
    else:
        print("无效选项")