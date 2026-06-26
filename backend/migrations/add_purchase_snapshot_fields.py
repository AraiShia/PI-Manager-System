"""为 po_purchase_order_item 添加采购快照字段"""

import os
import sys

from sqlalchemy import text


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.database import engine


def upgrade():
    statements = [
        "ALTER TABLE po_purchase_order_item ADD COLUMN product_name_snapshot VARCHAR(255)",
        "ALTER TABLE po_purchase_order_item ADD COLUMN customer_model_snapshot VARCHAR(100)",
        "ALTER TABLE po_purchase_order_item ADD COLUMN line_1688_url VARCHAR(500)",
    ]

    with engine.connect() as conn:
        for sql in statements:
            try:
                conn.execute(text(sql))
            except Exception as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
        conn.commit()


if __name__ == "__main__":
    upgrade()
