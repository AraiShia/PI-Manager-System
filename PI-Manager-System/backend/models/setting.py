"""
系统设置模型
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class SysSetting(Base):
    """系统设置表"""
    __tablename__ = "sys_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True, comment="设置键")
    value = Column(String(500), nullable=True, comment="设置值")
    description = Column(String(200), nullable=True, comment="设置描述")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    @staticmethod
    def get_default_settings():
        """获取默认设置"""
        return {
            "default_profit_margin": "25",      # 默认毛利率25%
            "exchange_rate": "7.24",              # 默认汇率
        }