"""
产品操作审计日志模型
记录产品关键操作
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.sql import func
from app.database import Base
import json


class PrdProductAuditLog(Base):
    """产品操作审计日志"""
    __tablename__ = "prd_product_audit_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, nullable=False, index=True)
    action_type = Column(String(50), nullable=False, default='TEMP_TO_FORMAL')
    operator_id = Column(Integer, ForeignKey("sys_users.id"))
    operation_time = Column(DateTime, server_default=func.now(), index=True)
    
    original_data = Column(Text, nullable=True)
    updated_fields = Column(Text, nullable=True)
    
    source = Column(String(100), default='order_detail_double_click')
    source_order_id = Column(Integer)
    duration_ms = Column(Integer, default=0)
    remark = Column(Text)
    
    __table_args__ = (
        Index('idx_audit_log_product_id', 'product_id'),
        Index('idx_audit_log_operation_time', 'operation_time'),
        Index('idx_audit_log_action_type', 'action_type'),
    )
    
    def set_original_data(self, data: dict):
        self.original_data = json.dumps(data, ensure_ascii=False)
    
    def get_original_data(self) -> dict:
        return json.loads(self.original_data) if self.original_data else {}
    
    def set_updated_fields(self, data: dict):
        self.updated_fields = json.dumps(data, ensure_ascii=False)
    
    def get_updated_fields(self) -> dict:
        return json.loads(self.updated_fields) if self.updated_fields else {}