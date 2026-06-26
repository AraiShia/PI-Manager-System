# -*- coding: utf-8 -*-
"""
widgets 模块统一导出

文件：client/widgets/__init__.py
用途：统一导出 widgets 目录下所有可复用的 UI 组件

包含：
- SettingsDialog: 系统设置对话框
- ProductItemEditDialog: 产品项编辑对话框
- StatusIndicatorManager: 状态灯管理器
- PurchaseDialog: 采购订单对话框（主实现）
- OrderSummaryEditDialog: 订单汇总编辑对话框
- OrderSummaryDialogs: 订单汇总相关对话框集合
- OrderImportDialog: 订单导入对话框
- ActionBarFactory: 操作栏工厂
- ProductOEDialog: 产品OE号对话框
- CustomerProductDialog: 客户产品对话框
- PaymentDialog: 付款对话框
- MemoDialog: 备注对话框
- FileUploadDialog: 文件上传对话框
- WizardConfirmDialog: 向导确认对话框
- SingleOrderDialog: 单订单对话框
- ReplyExportDialog: 回复导出对话框
- ProductSupplierDialog: 产品供应商对话框
"""

from .settings_dialog import SettingsDialog
from .product_item_edit_dialog import ProductItemEditDialog
from .status_indicator import StatusIndicatorManager
from .purchase_dialog import PurchaseDialog
from .order_summary_edit_dialog import OrderSummaryEditDialog
from .order_summary_dialogs import (
    CustomerRequirementDialog,
    CustomerModelDialog,
    CustomerReplyDialog,
)
from .order_import_dialog import OrderImportDialog
from .action_bar import ActionBarFactory
from .product_oe_dialog import ProductOEDialog
from .customer_product_dialog import CustomerProductDialog
from .payment_dialog import PaymentDialog
from .memo_dialog import MemoDialog
from .file_upload_dialog import FileUploadDialog
from .wizard_confirm_dialog import WizardConfirmDialog
from .single_order_dialog import SingleOrderDialog
from .reply_export_dialog import ReplyExportDialog
from .product_supplier_dialog import ProductSupplierDialog

# 订单总表模块
from .order_summary import (
    OrderSummaryTab,
    OrderListPanel,
    OrderDetailPanel,
)

__all__ = [
    # Dialog 类
    'SettingsDialog',
    'ProductItemEditDialog',
    'PurchaseDialog',
    'OrderSummaryEditDialog',
    'CustomerRequirementDialog',
    'CustomerModelDialog',
    'CustomerReplyDialog',
    'OrderImportDialog',
    'ProductOEDialog',
    'CustomerProductDialog',
    'PaymentDialog',
    'MemoDialog',
    'FileUploadDialog',
    'WizardConfirmDialog',
    'SingleOrderDialog',
    'ReplyExportDialog',
    'ProductSupplierDialog',
    # 订单总表模块
    'OrderSummaryTab',
    'OrderListPanel',
    'OrderDetailPanel',
    # 工具类
    'StatusIndicatorManager',
    'ActionBarFactory',
]