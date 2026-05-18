import sqlite3
import sys

conn = sqlite3.connect('app.db')
cursor = conn.cursor()

# 检查并添加缺失的列
tables_columns = {
    'po_purchase_order_item': [
        ('factory_code', 'TEXT'),
        ('product_image', 'TEXT'),
        ('color', 'TEXT'),
        ('detail_requirement', 'TEXT'),
        ('price_ex_factory', 'REAL'),
        ('price_ex_factory_tax', 'REAL'),
        ('price_fob', 'REAL'),
        ('price_fob_tax', 'REAL'),
        ('inbound_status', 'INTEGER DEFAULT 1')
    ],
    'po_1688_purchase': [
        ('supplier_name', 'TEXT'),
        ('product_remark', 'TEXT'),
        ('invoice_type', 'TEXT'),
        ('labeling_fee', 'REAL'),
        ('shipping_fee', 'REAL'),
        ('shipping_method', 'TEXT'),
        ('carton_count', 'INTEGER'),
        ('status', 'INTEGER DEFAULT 1')
    ],
    'sh_shipment': [
        ('total_amount', 'REAL'),
        ('total_cartons', 'INTEGER'),
        ('total_gross_weight', 'REAL'),
        ('total_volume', 'REAL')
    ],
    'sh_shipment_item': [
        ('pi_item_id', 'INTEGER'),
        ('unit_price', 'REAL'),
        ('total_price', 'REAL'),
        ('carton_no', 'TEXT'),
        ('net_weight', 'REAL'),
        ('gross_weight', 'REAL'),
        ('dimension', 'TEXT')
    ],
    'ar_customer_payment': [
        ('actual_amount', 'REAL'),
        ('is_fully_paid', 'INTEGER DEFAULT 0'),
        ('order_ids', 'TEXT'),
        ('remark', 'TEXT')
    ],
    'inv_inventory': [
        ('customer_product_code', 'TEXT'),
        ('inventory_customer_price', 'REAL'),
        ('color', 'TEXT'),
        ('stock_status_color', 'TEXT'),
        ('stock_type', 'INTEGER DEFAULT 1')
    ]
}

# 创建新表（如果不存在）
new_tables = {
    'po_inbound_batch': '''
        CREATE TABLE IF NOT EXISTS po_inbound_batch (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dept_id TEXT NOT NULL,
            po_id INTEGER NOT NULL,
            batch_no TEXT,
            inbound_date TEXT,
            product_id INTEGER NOT NULL,
            quantity REAL,
            inspector TEXT,
            remark TEXT,
            status INTEGER DEFAULT 1,
            created_by INTEGER,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (po_id) REFERENCES po_purchase_order(id),
            FOREIGN KEY (product_id) REFERENCES prd_product(id)
        )
    ''',
    'sh_ci_document': '''
        CREATE TABLE IF NOT EXISTS sh_ci_document (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id INTEGER NOT NULL,
            invoice_no TEXT,
            invoice_date TEXT,
            exporter TEXT,
            exporter_address TEXT,
            exporter_phone TEXT,
            exporter_fax TEXT,
            importer TEXT,
            importer_address TEXT,
            importer_phone TEXT,
            importer_fax TEXT,
            loading_port TEXT,
            destination_port TEXT,
            transport_way TEXT,
            payment_terms TEXT,
            total_amount REAL,
            marks TEXT,
            created_at TEXT,
            FOREIGN KEY (shipment_id) REFERENCES sh_shipment(id)
        )
    ''',
    'sh_pl_document': '''
        CREATE TABLE IF NOT EXISTS sh_pl_document (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id INTEGER NOT NULL,
            pl_no TEXT,
            pl_date TEXT,
            total_cartons INTEGER,
            total_gross_weight REAL,
            total_net_weight REAL,
            total_volume REAL,
            remark TEXT,
            created_at TEXT,
            FOREIGN KEY (shipment_id) REFERENCES sh_shipment(id)
        )
    ''',
    'ap_supplier_payment_stage': '''
        CREATE TABLE IF NOT EXISTS ap_supplier_payment_stage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id INTEGER NOT NULL,
            stage_type TEXT,
            stage_name TEXT,
            amount REAL NOT NULL,
            paid_amount REAL DEFAULT 0,
            status INTEGER DEFAULT 1,
            payment_date TEXT,
            payment_proof TEXT,
            remark TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (payment_id) REFERENCES ap_supplier_payment(id)
        )
    '''
}

# 为每个表添加缺失的列
for table_name, columns in tables_columns.items():
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_cols = [col[1] for col in cursor.fetchall()]

    for col_name, col_type in columns:
        if col_name not in existing_cols:
            try:
                cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}')
                print(f'Added {col_name} to {table_name}')
            except Exception as e:
                print(f'Error adding {col_name} to {table_name}: {e}')

# 创建新表
for table_name, create_sql in new_tables.items():
    try:
        cursor.execute(create_sql)
        print(f'Created table {table_name}')
    except Exception as e:
        print(f'Error creating {table_name}: {e}')

conn.commit()
conn.close()
print('Database migration completed!')