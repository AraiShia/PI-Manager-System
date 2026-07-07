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

db = SessionLocal()

# 测试查询
print("查询产品类别:")
categories = db.query(PrdProductCategory).all()
print(f"查询结果数量: {len(categories)}")
for cat in categories:
    print(f"  ID: {cat.id}, Code: {cat.code}, Name: {cat.name}")

# 检查表名
print(f"\n模型表名: {PrdProductCategory.__tablename__}")

db.close()