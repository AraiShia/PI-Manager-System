from sqlalchemy import Column, String, Integer, DECIMAL, DateTime
from app.database import Base
from datetime import datetime

class PubCategory(Base):
    __tablename__ = "pub_category"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_code = Column(String(20), nullable=False, unique=True)
    category_name = Column(String(100), nullable=False)
    parent_id = Column(Integer)
    sort_order = Column(Integer, default=0)

class PubRegion(Base):
    __tablename__ = "pub_region"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    region_code = Column(String(20), nullable=False, unique=True)
    region_name = Column(String(100), nullable=False)
    parent_code = Column(String(20))
    level = Column(Integer, default=1)

class PubCurrency(Base):
    __tablename__ = "pub_currency"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    currency_code = Column(String(10), nullable=False, unique=True)
    currency_name = Column(String(50))
    exchange_rate = Column(DECIMAL(15, 4))
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
