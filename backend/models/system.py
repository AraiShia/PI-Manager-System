from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, JSON, ForeignKey
from app.database import Base
from datetime import datetime

class SysNumberRule(Base):
    __tablename__ = "sys_number_rule"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_type = Column(String(50), nullable=False, unique=True)
    rule_pattern = Column(String(200), nullable=False)
    current_value = Column(Integer, default=0)
    reset_frequency = Column(String(20), default="YEAR")
    last_reset_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class SysNumberHistory(Base):
    __tablename__ = "sys_number_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_type = Column(String(50), nullable=False)
    generated_no = Column(String(100), nullable=False)
    related_id = Column(Integer)
    related_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)

class SysOperationLog(Base):
    __tablename__ = "sys_operation_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(String(10))
    table_name = Column(String(100), nullable=False)
    record_id = Column(Integer, nullable=False)
    operation_type = Column(String(20), nullable=False)
    old_data = Column(JSON)
    new_data = Column(JSON)
    operator_id = Column(Integer)
    operator_ip = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)
