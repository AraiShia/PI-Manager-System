from sqlalchemy import Column, String, DateTime, Integer
from app.database import Base
from datetime import datetime

class SysDepartment(Base):
    __tablename__ = "sys_department"
    
    dept_id = Column(String(10), primary_key=True)
    dept_name = Column(String(50), nullable=False)
    db_name = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    status = Column(Integer, default=1)
