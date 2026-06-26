"""国内采购合同导出器"""

from typing import Dict, Any
from .base_exporter import BaseExporter
from templates import PURCHASE_TEMPLATE
from templates.config import COMPANY_NAME_CN, COMPANY_ADDRESS, CONTRACT_CLAUSES


class PurchaseExporter(BaseExporter):
    """国内采购合同导出器"""

    def __init__(self):
        super().__init__(PURCHASE_TEMPLATE)

    def export_purchase(self, purchase_data: Dict[str, Any]) -> bytes:
        """导出国内采购合同"""
        return self.export(purchase_data)

    def _fill_dynamic_content(self, ws: Any, data: Dict[str, Any]):
        """填充采购合同动态内容"""
        purchase = data.get("purchase", {})
        supplier = data.get("supplier", {})
        user = data.get("user", {})
        items = data.get("items", [])

        # 头部
        ws["A1"] = COMPANY_NAME_CN
        ws["A2"] = "采购合同"

        # 合同编号和日期
        ws["A3"] = f"合同编号  {purchase.get('po_no', '')}"
        ws["G3"] = f"合同日期: {self._format_date(purchase.get('created_at'))}"

        # 卖方信息
        ws["B5"] = supplier.get("supplier_name", "")
        ws["B6"] = supplier.get("contact_name", "")
        ws["B7"] = f"{supplier.get('phone', '')}"
        ws["B8"] = supplier.get("address", "")

        # 买方信息
        ws["G5"] = COMPANY_NAME_CN
        ws["G6"] = user.get("name", "")
        ws["G7"] = user.get("phone", "")
        ws["G8"] = COMPANY_ADDRESS

        # 表头
        headers = ["图片", "维那型号\n客户编号", "工厂型号", "产品名称", "描述", "规格/CM", "外包装尺寸", "数量", "单位", "净重/毛重", "单价（含税）", "总金额（含税）"]
        for col, header in enumerate(headers, 1):
            ws.cell(row=9, column=col, value=header)

        # 产品明细
        row = 10
        total_qty = 0
        total_amount = 0.0

        for item in items:
            qty = item.get("quantity", 0)
            unit_price = item.get("price_including_tax", 0)
            amount = qty * unit_price

            ws.cell(row=row, column=2, value=f"{item.get('weina_code', '')}\n{item.get('customer_code', '')}")
            ws.cell(row=row, column=3, value=item.get("factory_code", ""))
            ws.cell(row=row, column=4, value=item.get("product_name", ""))
            ws.cell(row=row, column=5, value=item.get("detail_requirement", ""))
            ws.cell(row=row, column=6, value=item.get("specification", ""))
            ws.cell(row=row, column=7, value=item.get("package_size", ""))
            ws.cell(row=row, column=8, value=qty)
            ws.cell(row=row, column=9, value="个")
            ws.cell(row=row, column=10, value=f"{item.get('net_weight', '')}/{item.get('gross_weight', '')}")
            ws.cell(row=row, column=11, value=unit_price)
            ws.cell(row=row, column=12, value=amount)

            total_qty += qty
            total_amount += amount
            row += 1

        # 汇总行
        ws["A12"] = "总计"
        ws["H12"] = total_qty
        ws["L12"] = total_amount

        # 产品要求
        ws["B13"] = purchase.get("product_requirement", "")
        ws["B14"] = purchase.get("package_requirement", "")

        # 交货信息
        ws["A16"] = f"交货日期  {self._format_date(purchase.get('delivery_date'))}"
        ws["A17"] = f"交货地址  {purchase.get('delivery_address', '')}"

        # 收款信息
        ws["B18"] = f"供应商收款名称  {supplier.get('bank_account_name', '')}"
        ws["G18"] = f"收货联系人  {purchase.get('receiver_contact', '')}"
        ws["B19"] = f"开户行及账号  {supplier.get('bank_name', '')} {supplier.get('bank_account', '')}"
        ws["G19"] = f"联系电话  {purchase.get('receiver_phone', '')}"

        # 付款方式
        ws["A20"] = f"付款方式  {purchase.get('payment_method', '')}"

        # 合同条款
        ws["A22"] = "合同条款："
        for i, clause in enumerate(CONTRACT_CLAUSES):
            ws.cell(row=23 + i, column=1, value=clause)

        # 签章区
        ws["A28"] = f"卖方：{supplier.get('supplier_name', '')}"
        ws["G28"] = f"买方：{COMPANY_NAME_CN}"
        ws["A30"] = f"单位地址： {supplier.get('address', '')}"
        ws["G30"] = f"单位地址：{COMPANY_ADDRESS}"

    def _format_date(self, date_value: Any) -> str:
        """格式化日期为 YYYY/MM/DD"""
        if hasattr(date_value, "strftime"):
            return date_value.strftime("%Y/%m/%d")
        return str(date_value) if date_value else ""