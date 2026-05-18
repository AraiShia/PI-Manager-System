#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
迁移脚本：为 qo_quote 和 qo_quote_item 表添加缺失的列
"""
import sqlite3
import sys
from pathlib import Path

def get_db_path():
    candidates = [
        Path(__file__).parent / "data" / "pimain.db",
        Path(__file__).parent / "app.db",
        Path(__file__).parent / "data" / "app.db",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None

def get_columns(cursor, table):
    cursor.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cursor.fetchall()]

def main():
    db_path = get_db_path()
    if not db_path:
        print("ERROR: Database not found!")
        sys.exit(1)

    print(f"Database: {db_path}\n")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # --- qo_quote_item ---
    print("=== qo_quote_item ===")
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qo_quote_item'")
    if not c.fetchone():
        print("Table qo_quote_item does not exist!")
    else:
        cols = get_columns(c, "qo_quote_item")
        print(f"Current columns: {cols}")

        expected = {
            "quote_id": "INTEGER",
            "product_id": "INTEGER",
            "oe_number": "VARCHAR(100)",
            "customer_code": "VARCHAR(100)",
            "detail_desc": "VARCHAR(500)",
            "quantity": "DECIMAL(15,4)",
            "unit_price": "DECIMAL(15,4)",
            "total_price": "DECIMAL(15,4)",
            "remark": "TEXT",
        }
        for col, typ in expected.items():
            if col not in cols:
                try:
                    c.execute(f"ALTER TABLE qo_quote_item ADD COLUMN {col} {typ}")
                    print(f"  + {col} ({typ}) added")
                except sqlite3.Error as e:
                    print(f"  ! {col}: {e}")
            else:
                print(f"  ok {col}")

    # --- qo_quote ---
    print("\n=== qo_quote ===")
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qo_quote'")
    if not c.fetchone():
        print("Table qo_quote does not exist!")
    else:
        cols = get_columns(c, "qo_quote")
        print(f"Current columns: {cols}")

        expected = {
            "dept_id": "VARCHAR(10)",
            "quote_no": "VARCHAR(50)",
            "customer_id": "INTEGER",
            "total_amount": "DECIMAL(15,4)",
            "currency": "VARCHAR(10)",
            "valid_until": "DATETIME",
            "status": "INTEGER",
            "remark": "TEXT",
            "converted_pi_id": "INTEGER",
            "created_by": "INTEGER",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        }
        for col, typ in expected.items():
            if col not in cols:
                try:
                    c.execute(f"ALTER TABLE qo_quote ADD COLUMN {col} {typ}")
                    print(f"  + {col} ({typ}) added")
                except sqlite3.Error as e:
                    print(f"  ! {col}: {e}")
            else:
                print(f"  ok {col}")

    conn.commit()
    
    # --- pi_proforma_invoice ---
    print("\n=== pi_proforma_invoice ===")
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pi_proforma_invoice'")
    if not c.fetchone():
        print("Table pi_proforma_invoice does not exist!")
    else:
        cols = get_columns(c, "pi_proforma_invoice")
        print(f"Current columns: {cols}")
        
        expected = {
            "dept_id": "VARCHAR(10)",
            "pi_no": "VARCHAR(50)",
            "customer_id": "INTEGER",
            "total_amount": "DECIMAL(15,4)",
            "currency": "VARCHAR(10)",
            "status": "INTEGER",
            "created_by": "INTEGER",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        }
        for col, typ in expected.items():
            if col not in cols:
                try:
                    c.execute(f"ALTER TABLE pi_proforma_invoice ADD COLUMN {col} {typ}")
                    print(f"  + {col} ({typ}) added")
                except sqlite3.Error as e:
                    print(f"  ! {col}: {e}")
            else:
                print(f"  ok {col}")
    
    # --- pi_proforma_invoice_item ---
    print("\n=== pi_proforma_invoice_item ===")
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pi_proforma_invoice_item'")
    if not c.fetchone():
        print("Table pi_proforma_invoice_item does not exist!")
    else:
        cols = get_columns(c, "pi_proforma_invoice_item")
        print(f"Current columns: {cols}")
        
        expected = {
            "pi_id": "INTEGER",
            "product_id": "INTEGER",
            "oe_number": "VARCHAR(100)",
            "quantity": "DECIMAL(15,4)",
            "unit_price": "DECIMAL(15,4)",
            "total_price": "DECIMAL(15,4)",
            "customer_code": "VARCHAR(100)",
            "detail_desc": "VARCHAR(500)",
            "remark": "TEXT",
        }
        for col, typ in expected.items():
            if col not in cols:
                try:
                    c.execute(f"ALTER TABLE pi_proforma_invoice_item ADD COLUMN {col} {typ}")
                    print(f"  + {col} ({typ}) added")
                except sqlite3.Error as e:
                    print(f"  ! {col}: {e}")
            else:
                print(f"  ok {col}")
    
    # --- pi_payment_stage ---
    print("\n=== pi_payment_stage ===")
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pi_payment_stage'")
    if not c.fetchone():
        print("Table pi_payment_stage does not exist!")
    else:
        cols = get_columns(c, "pi_payment_stage")
        print(f"Current columns: {cols}")
        
        expected = {
            "pi_id": "INTEGER",
            "stage_type": "VARCHAR(50)",
            "stage_no": "INTEGER",
            "amount": "DECIMAL(15,4)",
            "due_date": "DATETIME",
            "paid_date": "DATETIME",
            "status": "INTEGER",
        }
        for col, typ in expected.items():
            if col not in cols:
                try:
                    c.execute(f"ALTER TABLE pi_payment_stage ADD COLUMN {col} {typ}")
                    print(f"  + {col} ({typ}) added")
                except sqlite3.Error as e:
                    print(f"  ! {col}: {e}")
            else:
                print(f"  ok {col}")
    
    conn.commit()
    print("\n=== Done ===")
    conn.close()

if __name__ == "__main__":
    main()
