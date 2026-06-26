# -*- coding: utf-8 -*-
"""purchase 相关 Dialog（延迟加载）"""

class PurchaseDialog:
    def __init__(self, api_client, dept_id, purchase=None):
        from main import PurchaseDialog as PUD
        self._dialog = PUD(api_client, dept_id, purchase)
    def exec(self):
        return self._dialog.exec()