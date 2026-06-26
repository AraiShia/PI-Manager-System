# -*- coding: utf-8 -*-
"""inventory 相关 Dialog（延迟加载）"""

class InventoryDialog:
    def __init__(self, api_client, dept_id=None, inventory=None, product_id=None, oe_number=None):
        from main import InventoryDialog as ID
        self._dialog = ID(api_client, dept_id, inventory, product_id, oe_number)
    
    def exec(self):
        return self._dialog.exec()