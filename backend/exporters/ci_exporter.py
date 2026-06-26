"""CI 模板导出器 - 薄壳。"""
import os
from typing import Any, Dict

from .xlsx_template_renderer import XlsxTemplateRenderer

_TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "templates",
)


class CIExporter:
    """CI 模板导出器（基于 xlsx 模板复用）。"""

    def __init__(self):
        self.renderer = XlsxTemplateRenderer(
            template_path=os.path.join(
                _TEMPLATES_DIR, "assets", "template_ci.xlsx"
            ),
            mapping_path=os.path.join(
                _TEMPLATES_DIR, "xlsx_mapping", "ci_mapping.yaml"
            ),
        )

    def export_ci(self, ci_data: Dict[str, Any]) -> bytes:
        """导出 CI xlsx 字节流。"""
        return self.renderer.render(ci_data)
