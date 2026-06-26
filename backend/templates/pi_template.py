"""PI模板配置"""

from .base_template import TemplateField, TemplateSection, TemplateConfig
from .config import (
    COMPANY_NAME_EN,
    COMPANY_ADDRESS,
    COMPANY_PHONE,
    COMPANY_TEL,
    COMPANY_EMAIL,
    BANK_NAME,
    BANK_ADDRESS,
    SWIFT_BIC,
    ACCOUNT_NO,
)

PI_TEMPLATE = TemplateConfig(
    name="PI模板",
    sheet_name="PI模板",
    sections=[
        # 公司信息区
        TemplateSection(
            name="header",
            start_row=1,
            end_row=3,
            fields=[
                TemplateField(cell="A1", value_type="static", default=COMPANY_NAME_EN),
                TemplateField(cell="A2", value_type="dynamic", data_path="pi.pi_no", formatter="pi_no"),
                TemplateField(cell="A2", value_type="dynamic", data_path="pi.created_at", formatter="date"),
                TemplateField(cell="A3", value_type="static", default="PROFORMA INVOICE"),
            ]
        ),
        # 买方信息区
        TemplateSection(
            name="buyer",
            start_row=5,
            end_row=9,
            fields=[
                TemplateField(cell="A5", value_type="dynamic", data_path="customer.customer_name", default=""),
                TemplateField(cell="A7", value_type="dynamic", data_path="customer.phone", default=""),
                TemplateField(cell="A8", value_type="dynamic", data_path="customer.address", default=""),
                TemplateField(cell="A9", value_type="dynamic", data_path="customer.country", default=""),
            ]
        ),
        # 卖方信息区
        TemplateSection(
            name="seller",
            start_row=6,
            end_row=9,
            fields=[
                TemplateField(cell="F6", value_type="dynamic", data_path="user.name", default=""),
                TemplateField(cell="F7", value_type="static", default=COMPANY_PHONE),
                TemplateField(cell="F8", value_type="static", default=COMPANY_ADDRESS),
                TemplateField(cell="F9", value_type="dynamic", data_path="pi.delivery_date", default="30 days after the deposit is paid"),
            ]
        ),
        # 产品明细区（可重复）
        TemplateSection(
            name="items",
            start_row=11,
            end_row=23,
            repeatable=True,
            repeat_start_row=12,
            repeat_data_path="items",
            fields=[
                TemplateField(cell="A{row}", value_type="dynamic", data_path="item.product_name"),
                TemplateField(cell="B{row}", value_type="dynamic", data_path="item.product_code"),
                TemplateField(cell="C{row}", value_type="dynamic", data_path="item.image_url"),
                TemplateField(cell="D{row}", value_type="dynamic", data_path="item.detail_desc", default="/"),
                TemplateField(cell="E{row}", value_type="dynamic", data_path="item.specification", default="/"),
                TemplateField(cell="F{row}", value_type="dynamic", data_path="item.pcs_per_carton", default="/"),
                TemplateField(cell="G{row}", value_type="dynamic", data_path="item.color"),
                TemplateField(cell="H{row}", value_type="dynamic", data_path="item.quantity"),
                TemplateField(cell="I{row}", value_type="dynamic", data_path="item.unit_price"),
                TemplateField(cell="J{row}", value_type="calculation", data_path="item.total_price", formatter="multiply"),
            ]
        ),
        # 汇总行
        TemplateSection(
            name="summary",
            start_row=23,
            end_row=24,
            fields=[
                TemplateField(cell="H23", value_type="calculation", data_path="total_quantity", formatter="sum"),
                TemplateField(cell="I23", value_type="calculation", data_path="total_amount", formatter="sum"),
            ]
        ),
        # 银行信息区
        TemplateSection(
            name="bank",
            start_row=25,
            end_row=32,
            fields=[
                TemplateField(cell="F26", value_type="static", default="BANK INFORMATION:"),
                TemplateField(cell="F27", value_type="static", default=f"Beneficiary: {COMPANY_NAME_EN}"),
                TemplateField(cell="F28", value_type="static", default=f"BANK NAME: {BANK_NAME}"),
                TemplateField(cell="F29", value_type="static", default=f"BANK ADDRESS: {BANK_ADDRESS}"),
                TemplateField(cell="F30", value_type="static", default=f"SWIFT BIC: {SWIFT_BIC}"),
                TemplateField(cell="F31", value_type="static", default=f"Tel&Fax: {COMPANY_TEL}"),
                TemplateField(cell="F32", value_type="static", default=f"Account No: {ACCOUNT_NO}"),
            ]
        ),
        # 条款区
        TemplateSection(
            name="terms",
            start_row=27,
            end_row=30,
            fields=[
                TemplateField(cell="A27", value_type="dynamic", data_path="pi.price_terms", default="FOB"),
                TemplateField(cell="A28", value_type="dynamic", data_path="pi.payment_terms", default="T/T 10% deposit ,The 90% balance according to the BL."),
                TemplateField(cell="A29", value_type="static", default="3. SHIPPING MARKS ARE BUYER'S OPTION"),
                TemplateField(cell="A30", value_type="dynamic", data_path="pi.warranty_time", default="13 months after shipping date"),
            ]
        ),
    ]
)