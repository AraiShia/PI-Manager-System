#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查PI相关数据库表结构"""
import sqlite3
from pathlib import Path

def get_db_path():
    candidates = [
        Path(__file__).parent / "data" / "pimain.db",
        Path(__file__).parent / "app.db",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None

def check_tables(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    tables = ['pi_proforma_invoice', 'pi_proforma_invoice_item', 'pi_payment_stage']
    
    for table in tables:
        c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if c.fetchone():
            print(f"\n=== {table} ===")
            c.execute(f"PRAGMA table_info({table})")
            for col in c.fetchall():
                print(f"  {col[1]}: {col[2]}")
        else:
            print(f"\n=== {table} === NOT FOUND")
    
    # 检查是否有数据
    print("\n=== 数据统计 ===")
    for table in tables:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0]
        print(f"  {table}: {count} rows")
    
    conn.close()

if __name__ == "__main__":
    db_path = get_db_path()
    if db_path:
        print(f"Database: {db_path}")
        check_tables(db_path)
    else:
        print("Database not found!")
