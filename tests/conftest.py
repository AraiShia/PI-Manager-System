import os
import sys

# 将 backend 加入导入路径，使测试能直接导入后端模块
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database import Base
from models.customer_product import PrdCustomerProduct
from models.customer import CrmCustomer


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def customer_factory(db):
    def _make(customer_code="TEST", dept_id="S"):
        customer = CrmCustomer(
            dept_id=dept_id,
            customer_code=customer_code,
            customer_name=f"Customer {customer_code}",
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer
    return _make
