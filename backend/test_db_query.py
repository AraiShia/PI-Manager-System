from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.product import PrdProduct
from app.database import Base

# 创建数据库连接
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/pimain.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 测试查询
db = SessionLocal()
try:
    print("Testing database query...")
    # 尝试查询产品
    products = db.query(PrdProduct).all()
    print(f"Found {len(products)} products")
    if products:
        print(f"First product: {products[0].product_code}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()