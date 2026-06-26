from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base

class SysUser(Base):
    __tablename__ = "sys_users"
    
    id = Column(Integer, primary_key=True, index=True, comment="用户ID")
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    real_name = Column(String(50), nullable=False, comment="真实姓名")
    email = Column(String(100), comment="邮箱")
    phone = Column(String(20), comment="电话")
    is_admin = Column(Boolean, default=False, nullable=False, comment="是否管理员")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    dept_id = Column(String(10), comment="所属部门ID")
    last_login = Column(DateTime(timezone=True), comment="最后登录时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    notes = Column(Text, comment="备注")
