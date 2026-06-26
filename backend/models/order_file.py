from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class OrderFile(Base):
    __tablename__ = "order_file"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pi_id = Column(Integer, ForeignKey("pi_proforma_invoice.id"), nullable=False, index=True)
    product_id = Column(Integer, nullable=True, index=True)
    file_type = Column(String(50), nullable=False)
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_ext = Column(String(20))
    uploaded_by = Column(Integer)
    uploaded_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<OrderFile(id={self.id}, pi_id={self.pi_id}, file_type='{self.file_type}', original_name='{self.original_name}')>"
