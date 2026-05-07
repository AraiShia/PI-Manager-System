from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.product_category import PrdProductCategory
from app.database import Base
from config.product_categories import PRODUCT_CATEGORIES

# 创建数据库连接
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建表
Base.metadata.create_all(bind=engine)

# 创建会话
db = SessionLocal()

# 初始化类别数据
print("初始化产品类别数据...")
sort_order = 1
for code, info in PRODUCT_CATEGORIES.items():
    # 检查是否已存在
    existing = db.query(PrdProductCategory).filter(PrdProductCategory.code == code).first()
    if existing:
        print(f"类别 {code} ({info['name']}) 已存在，跳过")
        continue
    
    category = PrdProductCategory(
        code=code,
        name=info["name"],
        description=info["description"],
        status=1,
        sort_order=sort_order
    )
    db.add(category)
    print(f"添加类别: {code} - {info['name']}")
    sort_order += 1

db.commit()
print("产品类别初始化完成！")

# 验证数据
categories = db.query(PrdProductCategory).all()
print(f"\n数据库中共 {len(categories)} 个类别:")
for cat in categories:
    print(f"  ID: {cat.id}, Code: {cat.code}, Name: {cat.name}")

db.close()