import sqlite3

# 产品类别配置
PRODUCT_CATEGORIES = {
    "01": {"name": "发动机", "description": "汽配件类 - 发动机零件"},
    "02": {"name": "曲轴", "description": "汽配件类 - 曲轴零件"},
    "03": {"name": "刹车片", "description": "汽配件类 - 刹车片"},
    "04": {"name": "杂项", "description": "汽配件类 - 其他杂项"},
    "11": {"name": "椅子类", "description": "办公家具类 - 椅子"},
    "12": {"name": "桌子类", "description": "办公家具类 - 桌子"},
    "88": {"name": "工程定制", "description": "办公家具类 - 工程定制"},
    "21": {"name": "百货类", "description": "百货类"}
}

# 连接数据库
conn = sqlite3.connect('app.db')
cursor = conn.cursor()

# 创建类别表（如果不存在）
cursor.execute('''
CREATE TABLE IF NOT EXISTS prd_product_category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    status INTEGER DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# 创建索引
cursor.execute('CREATE INDEX IF NOT EXISTS ix_prd_product_category_code ON prd_product_category(code)')
cursor.execute('CREATE INDEX IF NOT EXISTS ix_prd_product_category_status ON prd_product_category(status)')

# 初始化类别数据
print("初始化产品类别数据...")
sort_order = 1
for code, info in PRODUCT_CATEGORIES.items():
    # 检查是否已存在
    cursor.execute('SELECT id FROM prd_product_category WHERE code = ?', (code,))
    existing = cursor.fetchone()
    if existing:
        print(f"类别 {code} ({info['name']}) 已存在，跳过")
        continue
    
    cursor.execute('''
    INSERT INTO prd_product_category (code, name, description, status, sort_order)
    VALUES (?, ?, ?, ?, ?)
    ''', (code, info["name"], info["description"], 1, sort_order))
    print(f"添加类别: {code} - {info['name']}")
    sort_order += 1

conn.commit()
print("产品类别初始化完成！")

# 验证数据
cursor.execute('SELECT id, code, name FROM prd_product_category ORDER BY sort_order')
categories = cursor.fetchall()
print(f"\n数据库中共 {len(categories)} 个类别:")
for cat in categories:
    print(f"  ID: {cat[0]}, Code: {cat[1]}, Name: {cat[2]}")

conn.close()