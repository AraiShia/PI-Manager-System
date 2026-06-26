from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base


class ShPendingShipmentItem(Base):
    """待出货产品队列表"""
    __tablename__ = 'sh_pending_shipment_item'

    id = Column(Integer, primary_key=True, autoincrement=True)
    pi_id = Column(Integer, nullable=False)           # 来源PI ID
    pi_item_id = Column(Integer, nullable=False)       # 来源PI明细ID
    product_id = Column(Integer)                      # 产品ID
    customer_id = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(String(50))
    status = Column(Integer, default=1)                # 1:待确认 2:已确认 3:已出货
