import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from models.product_category import PrdProductCategory

# 创建数据库连接
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建表
Base.metadata.create_all(bind=engine)

# 创建会话
db = SessionLocal()

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
categories = db.query(PrdProductCategory).order_by(PrdProductCategory.sort_order).all()
print(f"\n数据库中共 {len(categories)} 个类别:")
for cat in categories:
    print(f"  ID: {cat.id}, Code: {cat.code}, Name: {cat.name}")

db.close()