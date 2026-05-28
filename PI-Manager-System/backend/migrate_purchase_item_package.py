# -*- coding: utf-8 -*-
"""
迁移脚本：创建采购订单明细项包装规格关联表
日期：2026-05-28
"""

from sqlalchemy import text
from app.database import engine, SessionLocal


def upgrade():
    """创建 po_purchase_order_item_package 表"""
    with engine.connect() as conn:
        # 检查表是否存在
        result = conn.execute(text("SHOW TABLES LIKE 'po_purchase_order_item_package'"))
        if result.fetchone():
            print("表 po_purchase_order_item_package 已存在，跳过创建")
            return
        
        # 创建表
        sql = """
        CREATE TABLE `po_purchase_order_item_package` (
            `id`                  BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
            `po_item_id`          BIGINT NOT NULL COMMENT '采购明细项ID FK → po_purchase_order_item.id',
            `packing_type`        VARCHAR(50) COMMENT '包装方式: 纸箱/托盘/木箱/无',
            `units_per_carton`    INT COMMENT '每箱数量/打包规格',
            `carton_length_cm`    DECIMAL(10,2) COMMENT '纸箱长度(cm)',
            `carton_width_cm`     DECIMAL(10,2) COMMENT '纸箱宽度(cm)',
            `carton_height_cm`    DECIMAL(10,2) COMMENT '纸箱高度(cm)',
            `created_at`          DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            `updated_at`          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            UNIQUE KEY `uk_po_item_id` (`po_item_id`),
            FOREIGN KEY (`po_item_id`) REFERENCES `po_purchase_order_item`(`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采购订单明细项包装规格关联表';
        """
        conn.execute(text(sql))
        
        # 创建索引
        conn.execute(text("CREATE INDEX `idx_po_item_package_created` ON `po_purchase_order_item_package`(`created_at`)"))
        
        conn.commit()
        print("表 po_purchase_order_item_package 创建成功")


def downgrade():
    """删除 po_purchase_order_item_package 表"""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS `po_purchase_order_item_package`"))
        conn.commit()
        print("表 po_purchase_order_item_package 已删除")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "down":
        downgrade()
    else:
        upgrade()