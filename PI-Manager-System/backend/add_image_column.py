import sqlite3

# 连接到数据库
conn = sqlite3.connect('./data/pimain.db')
cursor = conn.cursor()

try:
    # 检查列是否存在
    cursor.execute("PRAGMA table_info(prd_product)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'default_image_url' not in columns:
        print("Adding default_image_url column...")
        cursor.execute("ALTER TABLE prd_product ADD COLUMN default_image_url TEXT")
        conn.commit()
        print("Column added successfully!")
    else:
        print("Column already exists!")
        
finally:
    conn.close()