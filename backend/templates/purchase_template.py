"""国内采购合同模板配置"""

from .base_template import TemplateField, TemplateSection, TemplateConfig
from .config import COMPANY_NAME_CN, COMPANY_ADDRESS

PURCHASE_TEMPLATE = TemplateConfig(
    name="国内采购合同",
    sheet_name="国内采购合同",
    sections=[
        TemplateSection(
            name="header",
            start_row=1,
            end_row=3,
            fields=[
                TemplateField(cell="A1", value_type="static", default=COMPANY_NAME_CN),
                TemplateField(cell="A2", value_type="static", default="采购合同"),
                TemplateField(cell="A3", value_type="dynamic", data_path="purchase.po_no"),
                TemplateField(cell="G3", value_type="dynamic", data_path="purchase.created_at", formatter="date"),
            ]
        ),
        TemplateSection(
            name="parties",
            start_row=4,
            end_row=8,
            fields=[
                TemplateField(cell="B5", value_type="dynamic", data_path="supplier.supplier_name"),
                TemplateField(cell="G5", value_type="static", default=COMPANY_NAME_CN),
                TemplateField(cell="B6", value_type="dynamic", data_path="supplier.contact_name"),
                TemplateField(cell="G6", value_type="dynamic", data_path="user.name"),
                TemplateField(cell="B7", value_type="dynamic", data_path="supplier.phone"),
                TemplateField(cell="G7", value_type="dynamic", data_path="user.phone"),
                TemplateField(cell="B8", value_type="dynamic", data_path="supplier.address"),
                TemplateField(cell="G8", value_type="static", default=COMPANY_ADDRESS),
            ]
        ),
        TemplateSection(
            name="items",
            start_row=9,
            end_row=12,
            repeatable=True,
            repeat_start_row=10,
            repeat_data_path="items",
            fields=[
                TemplateField(cell="A{row}", value_type="dynamic", data_path="item.product_image"),
                TemplateField(cell="B{row}", value_type="dynamic", data_path="item.weina_code"),
                TemplateField(cell="B{row}", value_type="dynamic", data_path="item.customer_code"),
                TemplateField(cell="C{row}", value_type="dynamic", data_path="item.factory_code"),
                TemplateField(cell="D{row}", value_type="dynamic", data_path="item.product_name"),
                TemplateField(cell="E{row}", value_type="dynamic", data_path="item.detail_requirement"),
                TemplateField(cell="F{row}", value_type="dynamic", data_path="item.specification"),
                TemplateField(cell="G{row}", value_type="dynamic", data_path="item.package_size"),
                TemplateField(cell="H{row}", value_type="dynamic", data_path="item.quantity"),
                TemplateField(cell="I{row}", value_type="static", default="个"),
                TemplateField(cell="J{row}", value_type="dynamic", data_path="item.weight"),
                TemplateField(cell="K{row}", value_type="dynamic", data_path="item.price_including_tax"),
                TemplateField(cell="L{row}", value_type="calculation", data_path="item.total_price"),
            ]
        ),
        TemplateSection(
            name="requirements",
            start_row=13,
            end_row=14,
            fields=[
                TemplateField(cell="B13", value_type="dynamic", data_path="purchase.product_requirement"),
                TemplateField(cell="B14", value_type="dynamic", data_path="purchase.package_requirement"),
            ]
        ),
        TemplateSection(
            name="delivery",
            start_row=16,
            end_row=20,
            fields=[
                TemplateField(cell="A16", value_type="dynamic", data_path="purchase.delivery_date", formatter="date"),
                TemplateField(cell="A17", value_type="dynamic", data_path="purchase.delivery_address"),
                TemplateField(cell="B18", value_type="dynamic", data_path="supplier.bank_account_name"),
                TemplateField(cell="G18", value_type="dynamic", data_path="purchase.receiver_contact"),
                TemplateField(cell="B19", value_type="dynamic", data_path="supplier.bank_info", formatter="concat"),
                TemplateField(cell="G19", value_type="dynamic", data_path="purchase.receiver_phone"),
                TemplateField(cell="A20", value_type="dynamic", data_path="purchase.payment_method"),
            ]
        ),
        TemplateSection(
            name="clauses",
            start_row=22,
            end_row=26,
            fields=[
                TemplateField(cell="A22", value_type="static", default="合同条款："),
            ]
        ),
        TemplateSection(
            name="signatures",
            start_row=28,
            end_row=32,
            fields=[
                TemplateField(cell="A28", value_type="dynamic", data_path="supplier.supplier_name"),
                TemplateField(cell="G28", value_type="static", default=COMPANY_NAME_CN),
                TemplateField(cell="A30", value_type="dynamic", data_path="supplier.address"),
                TemplateField(cell="G30", value_type="static", default=COMPANY_ADDRESS),
            ]
        ),
    ]
)