"""PL装箱单模板配置"""

from .base_template import TemplateField, TemplateSection, TemplateConfig
from .config import COMPANY_NAME_CN, COMPANY_NAME_EN, COMPANY_ADDRESS

PL_TEMPLATE = TemplateConfig(
    name="PL",
    sheet_name="PL",
    sections=[
        TemplateSection(
            name="header",
            start_row=1,
            end_row=4,
            fields=[
                TemplateField(cell="A1", value_type="static", default=COMPANY_NAME_CN),
                TemplateField(cell="A2", value_type="static", default=COMPANY_NAME_EN),
                TemplateField(cell="A3", value_type="static", default=COMPANY_ADDRESS),
                TemplateField(cell="A4", value_type="static", default="PACKING LIST"),
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
                TemplateField(cell="G8", value_type="dynamic", data_path="shipment.destination_port"),
            ]
        ),
        TemplateSection(
            name="items",
            start_row=11,
            end_row=26,
            repeatable=True,
            repeat_start_row=12,
            repeat_data_path="items",
            fields=[
                TemplateField(cell="A{row}", value_type="static", default="N/M"),
                TemplateField(cell="B{row}", value_type="dynamic", data_path="item.pi_no"),
                TemplateField(cell="C{row}", value_type="dynamic", data_path="item.product_name"),
                TemplateField(cell="D{row}", value_type="dynamic", data_path="item.carton_count"),
                TemplateField(cell="E{row}", value_type="dynamic", data_path="item.quantity"),
                TemplateField(cell="F{row}", value_type="dynamic", data_path="item.gross_weight"),
                TemplateField(cell="G{row}", value_type="dynamic", data_path="item.net_weight"),
                TemplateField(cell="H{row}", value_type="calculation", data_path="item.volume", formatter="carton_volume"),
            ]
        ),
        TemplateSection(
            name="summary",
            start_row=26,
            end_row=26,
            fields=[
                TemplateField(cell="D26", value_type="calculation", data_path="total_cartons", formatter="sum"),
                TemplateField(cell="E26", value_type="calculation", data_path="total_quantity", formatter="sum"),
                TemplateField(cell="F26", value_type="calculation", data_path="total_gross_weight", formatter="sum"),
                TemplateField(cell="G26", value_type="calculation", data_path="total_net_weight", formatter="sum"),
            ]
        ),
    ]
)