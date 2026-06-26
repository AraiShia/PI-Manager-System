# -*- coding: utf-8 -*-
"""
Dialog 模块统一导出

文件：client/dialogs/__init__.py
用途：统一导出 dialogs 目录下所有可复用的 Dialog 组件

包含模块：
- auth: 登录窗口、系统设置
- common: 发票上传、字段编辑
- order: 订单编辑、回复历史
- customer: 客户相关 Dialog（客户编辑、详情、地址、联系人）
- supplier: 供应商相关 Dialog（供应商编辑、方案编辑）
- quote: 报价相关 Dialog
- pi: PI 相关 Dialog
- shipment: 出货相关 Dialog
- payment: 付款相关 Dialog
- inventory: 库存相关 Dialog
- purchase: 采购相关 Dialog

调用方式：
```python
from dialogs import (
    LoginWindow, SettingsDialog,
    InvoiceUploadDialog, FieldEditDialog,
    OrderEditDialog, ReplyHistoryDialog,
    CustomerDialog, CustomerDetailDialog, AddressDialog, ContactDialog,
    SupplierDialog, SupplierSchemeDialog,
    QuoteDialog, QuoteProductDialog,
    PIDialog,
    PurchaseDialog,
    ShipmentDialog, ShipmentStageDialog,
    CustomerPaymentDialog, SupplierPaymentDialog, SupplierPaymentStageDialog,
    InventoryDialog,
)
```
"""

from .auth import LoginWindow
from .common import InvoiceUploadDialog, FieldEditDialog
from .order import OrderEditDialog, ReplyHistoryDialog
from .customer import CustomerDialog, CustomerDetailDialog, AddressDialog, ContactDialog
from .supplier import SupplierDialog, SupplierSchemeDialog
from .quote import QuoteDialog, QuoteProductDialog
from .pi import PIDialog
from .purchase import PurchaseDialog
from .shipment import ShipmentDialog, ShipmentStageDialog
from .payment import CustomerPaymentDialog, SupplierPaymentDialog, SupplierPaymentStageDialog
# SettingsDialog 已迁移到 widgets/settings_dialog.py
# TODO: InventoryDialog 待完整迁移后启用
# from .inventory import InventoryDialog

__all__ = [
    # 认证 - LoginWindow 在 auth.py，SettingsDialog 已迁移到 widgets/settings_dialog.py
    'LoginWindow',
    # 通用
    'InvoiceUploadDialog',
    'FieldEditDialog',
    # 订单
    'OrderEditDialog',
    'ReplyHistoryDialog',
    # 客户
    'CustomerDialog',
    'CustomerDetailDialog',
    'AddressDialog',
    'ContactDialog',
    # 供应商
    'SupplierDialog',
    'SupplierSchemeDialog',
    # 报价
    'QuoteDialog',
    'QuoteProductDialog',
    # PI
    'PIDialog',
    # 采购
    'PurchaseDialog',
    # 出货
    'ShipmentDialog',
    'ShipmentStageDialog',
    # 付款
    'CustomerPaymentDialog',
    'SupplierPaymentDialog',
    'SupplierPaymentStageDialog',
    # 库存 - TODO: InventoryDialog 待完整迁移后启用
]