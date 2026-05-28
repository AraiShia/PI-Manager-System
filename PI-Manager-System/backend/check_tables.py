import sqlite3
import os

db_path = os.path.join("data", "pimain.db")
print(f"检查数据库: {db_path}")
print(f"文件存在: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    print(f"\n数据库表 ({len(tables)} 个):")
    for t in tables:
        cursor.execute(f"PRAGMA table_info({t[0]})")
        cols = [c[1] for c in cursor.fetchall()]
        marker = ""
        if 'memo_record' in t[0] or 'order_file' in t[0]:
            marker = " [NEW]"
        print(f"  - {t[0]} ({len(cols)} cols){marker}")
    conn.close()
else:
    print("数据库文件不存在")