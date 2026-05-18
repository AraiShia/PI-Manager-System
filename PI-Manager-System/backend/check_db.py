import sqlite3

db_path = "data/pimain.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查 sh_shipment_item 表结构
cursor.execute("PRAGMA table_info(sh_shipment_item)")
columns = cursor.fetchall()
print("sh_shipment_item table structure:")
for col in columns:
    print(f"  {col[1]}: {col[2]}")

# 检查表是否存在
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sh_shipment_item'")
table_exists = cursor.fetchone()
print(f"\nTable exists: {bool(table_exists)}")

# 检查 stage_id 列
has_stage_id = any(col[1] == 'stage_id' for col in columns)
print(f"Has stage_id column: {has_stage_id}")

conn.close()