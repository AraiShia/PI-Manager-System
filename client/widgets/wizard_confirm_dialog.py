from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Signal


class WizardConfirmDialog(QDialog):
    """临时产品转正对话框（复用 CustomerProductDialog）
    
    本类作为包装器，调用已有的 CustomerProductDialog 实现转正功能。
    """
    
    product_confirmed = Signal(int, dict)
    
    def __init__(self, api_client, temp_product: dict, customer_id: int, parent=None):
        super().__init__(parent)
        
        self.api_client = api_client
        self.temp_product = temp_product
        self.customer_id = customer_id
        
        self.setWindowTitle("转正为正式产品")
        self.setMinimumSize(900, 700)
        
        self._setup_ui()
    
    def _setup_ui(self):
        from widgets.customer_product_dialog import CustomerProductDialog

        self.dialog = CustomerProductDialog(
            api_client=self.api_client,
            product=self.temp_product,
            parent=self,
            mode="confirm_temp"
        )
        self.dialog._preset_customer_id = self.customer_id

        main_layout = self.layout()
        if main_layout is None:
            from PySide6.QtWidgets import QVBoxLayout
            main_layout = QVBoxLayout(self)

        main_layout.addWidget(self.dialog)

        # 2026-06-12 修复：连接 product_confirmed 信号（Signal(bool, int)）
        # 2026-06-16 修复：信号改为 (bool, dict)，回调签名改为 (success, updated_product)
        self.dialog.product_confirmed.connect(self._on_dialog_finished)
        self.dialog.rejected.connect(self.reject)

    def _on_dialog_finished(self, success: bool, updated_product: dict):
        if success and updated_product:
            product_id = updated_product.get('id')
            if product_id is None:
                # 兼容旧信号：如果 updated_product 是 int（product_id）
                if isinstance(updated_product, int):
                    product_id = updated_product
                    updated_product = None
            try:
                if updated_product is None and product_id:
                    updated_product = self.api_client.get_product_detail(product_id)
                self.product_confirmed.emit(product_id, updated_product or {})
                self.accept()
            except Exception as e:
                self.product_confirmed.emit(product_id or 0, None)
                self.accept()
        else:
            self.reject()
    
    def exec(self) -> int:
        return self.dialog.exec()
    
    def accept(self):
        super().accept()
    
    def reject(self):
        super().reject()