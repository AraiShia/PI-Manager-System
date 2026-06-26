"""国内采购合同模板导出器。"""
import os
from typing import Any, Dict

from .xlsx_template_renderer import XlsxTemplateRenderer

_TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "templates",
)


class ContractExporter:
    """国内采购合同模板导出器（基于 xlsx 模板）。"""

    def __init__(self):
        self.renderer = XlsxTemplateRenderer(
            template_path=os.path.join(
                _TEMPLATES_DIR, "assets", "template_contract.xlsx"
            ),
            mapping_path=os.path.join(
                _TEMPLATES_DIR, "xlsx_mapping", "contract_mapping.yaml"
            ),
        )

    def export_contract(self, contract_data: Dict[str, Any]) -> bytes:
        """导出国内采购合同 xlsx 字节流。"""
        return self.renderer.render(contract_data)
