import sqlite3

conn = sqlite3.connect('app.db')
cursor = conn.cursor()

# 获取所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("数据库中的表:")
for table in tables:
    print(f"  {table[0]}")

# 检查 prd_product_category 表
print("\nprd_product_category 表的内容:")
cursor.execute("SELECT * FROM prd_product_category")
rows = cursor.fetchall()
print(f"共 {len(rows)} 条记录")
for row in rows:
    print(f"  {row}")

conn.close()