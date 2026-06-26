# -*- coding: utf-8 -*-
"""产品相关 Dialog

这些类在 main.py 中定义，使用延迟导入避免循环依赖。
"""


class SupplierSchemeDialog:
    def __init__(self, api_client, supplier_id=None, scheme=None, product_id=None):
        from main import SupplierSchemeDialog as SSD
        self._dialog = SSD(api_client, supplier_id, scheme, product_id)
    
    def exec(self):
        return self._dialog.exec()


class CustomerDialog:
    def __init__(self, api_client, customer=None):
        from main import CustomerDialog as CD
        self._dialog = CD(api_client, customer)
    
    def exec(self):
        return self._dialog.exec()


class CustomerDetailDialog:
    def __init__(self, api_client, customer):
        from main import CustomerDetailDialog as CDD
        self._dialog = CDD(api_client, customer)
    
    def exec(self):
        return self._dialog.exec()


class AddressDialog:
    def __init__(self, api_client, address=None, customer_id=None):
        from main import AddressDialog as AD
        self._dialog = AD(api_client, address, customer_id)
    
    def exec(self):
        return self._dialog.exec()


class ContactDialog:
    def __init__(self, api_client, contact=None, customer_id=None):
        from main import ContactDialog as CD
        self._dialog = CD(api_client, contact, customer_id)
    
    def exec(self):
        return self._dialog.exec()


class SupplierDialog:
    def __init__(self, api_client, supplier=None):
        from main import SupplierDialog as SD
        self._dialog = SD(api_client, supplier)
    
    def exec(self):
        return self._dialog.exec()


class QuoteDialog:
    def __init__(self, api_client, dept_id, quote=None):
        from main import QuoteDialog as QD
        self._dialog = QD(api_client, dept_id, quote)
    
    def exec(self):
        return self._dialog.exec()


class QuoteProductDialog:
    def __init__(self, api_client, quote_product=None, quote_id=None, suppliers=None):
        from main import QuoteProductDialog as QPD
        self._dialog = QPD(api_client, quote_product, quote_id, suppliers)
    
    def exec(self):
        return self._dialog.exec()


class PIDialog:
    """2026-06-23 修复循环递归：直接用 main.PIDialog 作为 class alias（不再实例化包装）"""
    def __init__(self, api_client, dept_id, pi=None):
        from main import PIDialog
        self._dialog = PIDialog(api_client, dept_id, pi)
    
    def exec(self):
        return self._dialog.exec()


class PurchaseDialog:
    def __init__(self, api_client, dept_id, purchase=None):
        from main import PurchaseDialog as PUD
        self._dialog = PUD(api_client, dept_id, purchase)
    
    def exec(self):
        return self._dialog.exec()


class ShipmentDialog:
    def __init__(self, api_client, dept_id, shipment=None):
        from main import ShipmentDialog as SD
        self._dialog = SD(api_client, dept_id, shipment)
    
    def exec(self):
        return self._dialog.exec()


class ShipmentStageDialog:
    def __init__(self, api_client, shipment, stage=None):
        from main import ShipmentStageDialog as SSD
        self._dialog = SSD(api_client, shipment, stage)
    
    def exec(self):
        return self._dialog.exec()