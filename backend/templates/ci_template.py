"""CI商业发票模板配置"""

from .base_template import TemplateField, TemplateSection, TemplateConfig
from .config import COMPANY_NAME_CN, COMPANY_NAME_EN, COMPANY_ADDRESS

CI_TEMPLATE = TemplateConfig(
    name="CI",
    sheet_name="CI",
    sections=[
        TemplateSection(
            name="header",
            start_row=1,
            end_row=4,
            fields=[
                TemplateField(cell="A1", value_type="static", default=COMPANY_NAME_CN),
                TemplateField(cell="A2", value_type="static", default=COMPANY_NAME_EN),
                TemplateField(cell="A3", value_type="static", default=COMPANY_ADDRESS),
                TemplateField(cell="A4", value_type="static", default="COMMERCIAL INVOICE"),
            ]
        ),
        TemplateSection(
            name="info",
            start_row=5,
            end_row=9,
            fields=[
                TemplateField(cell="A5", value_type="dynamic", data_path="customer.name_address", formatter="concat"),
                TemplateField(cell="E5", value_type="dynamic", data_path="shipment.shipment_no"),
                TemplateField(cell="F6", value_type="dynamic", data_path="shipment_stage.shipment_date", formatter="date_dmy"),
                TemplateField(cell="A8", value_type="dynamic", data_path="shipment.loading_port", default="SHANGHAI CHINA"),
                TemplateField(cell="E8", value_type="dynamic", data_path="shipment.destination_port"),
                TemplateField(cell="A9", value_type="dynamic", data_path="shipment.lc_no"),
                TemplateField(cell="C9", value_type="dynamic", data_path="shipment.payment_terms", default="TT"),
                TemplateField(cell="F9", value_type="dynamic", data_path="shipment.price_terms", default="FOB"),
            ]
        ),
        TemplateSection(
            name="items",
            start_row=11,
            end_row=30,
            repeatable=True,
            repeat_start_row=12,
            repeat_data_path="items",
            fields=[
                TemplateField(cell="A{row}", value_type="static", default="N/M"),
                TemplateField(cell="B{row}", value_type="dynamic", data_path="item.pi_no"),
                TemplateField(cell="C{row}", value_type="dynamic", data_path="item.quantity"),
                TemplateField(cell="D{row}", value_type="dynamic", data_path="item.color"),
                TemplateField(cell="F{row}", value_type="dynamic", data_path="item.unit_price"),
                TemplateField(cell="G{row}", value_type="calculation", data_path="item.total_price"),
            ]
        ),
        TemplateSection(
            name="summary",
            start_row=26,
            end_row=30,
            fields=[
                TemplateField(cell="C26", value_type="calculation", data_path="total_quantity", formatter="sum"),
                TemplateField(cell="G26", value_type="calculation", data_path="total_amount", formatter="sum"),
                TemplateField(cell="E27", value_type="static", default="Order Amount"),
                TemplateField(cell="G27", value_type="dynamic", data_path="shipment.total_amount"),
                TemplateField(cell="E28", value_type="static", default="DEPOSIT APPLIED"),
                TemplateField(cell="G28", value_type="dynamic", data_path="payment.deposit", default=0),
                TemplateField(cell="E29", value_type="static", default="Discount"),
                TemplateField(cell="G29", value_type="dynamic", data_path="shipment.discount", default=0),
                TemplateField(cell="E30", value_type="static", default="Balance PAYMENT"),
                TemplateField(cell="G30", value_type="calculation", data_path="balance", formatter="subtract"),
            ]
        ),
    ]
)