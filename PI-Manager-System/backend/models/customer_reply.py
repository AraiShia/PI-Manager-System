"""
客户回复模型
"""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class CustomerReply(Base):
    """客户回复表"""
    __tablename__ = "customer_replies"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pi_id = Column(Integer, ForeignKey("pi_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    reply_date = Column(Date, nullable=False)
    reply_content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<CustomerReply(id={self.id}, pi_id={self.pi_id}, date={self.reply_date})>"
