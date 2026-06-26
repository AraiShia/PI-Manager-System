"""基础导出器"""

from io import BytesIO
from typing import Any, Dict, List, Optional
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side

from templates import TemplateConfig, TemplateField, TemplateSection
from templates.config import (
    COMPANY_NAME_CN,
    COMPANY_NAME_EN,
    COMPANY_ADDRESS,
    COMPANY_PHONE,
    COMPANY_TEL,
    COMPANY_EMAIL,
    BANK_NAME,
    BANK_ADDRESS,
    SWIFT_BIC,
    ACCOUNT_NO,
    DEFAULT_LOADING_PORT,
    DEFAULT_MARKS,
)


class BaseExporter:
    """导出器基类"""

    def __init__(self, template: TemplateConfig):
        self.template = template

    def export(self, data: Dict[str, Any]) -> bytes:
        """导出为Excel字节流"""
        wb = Workbook()
        ws = wb.active
        ws.title = self.template.sheet_name

        self._fill_static_content(ws)
        self._fill_dynamic_content(ws, data)
        self._apply_styles(ws)

        return self._save_to_bytes(wb)

    def _fill_static_content(self, ws):
        """填充静态内容"""
        for section in self.template.sections:
            if section.name == "header":
                for field in section.fields:
                    if field.value_type == "static":
                        self._set_cell(ws, field.cell, field.default)

    def _fill_dynamic_content(self, ws: Any, data: Dict[str, Any]):
        """填充动态内容"""
        for section in self.template.sections:
            if section.repeatable and section.repeat_data_path:
                # 处理可重复区块（如产品明细）
                items = self._get_nested_value(data, section.repeat_data_path) or []
                for idx, item in enumerate(items):
                    row = section.repeat_start_row + idx
                    for field in section.fields:
                        cell = field.cell.replace("{row}", str(row))
                        value = self._resolve_value(field, item, data)
                        if value is not None:
                            self._set_cell(ws, cell, value)
            else:
                # 处理普通区块
                for field in section.fields:
                    if field.value_type == "dynamic":
                        value = self._resolve_value(field, data, data)
                        if value is not None:
                            self._set_cell(ws, field.cell, value)

    def _resolve_value(
        self, field: TemplateField, data: Dict[str, Any], context: Dict[str, Any]
    ) -> Optional[Any]:
        """解析字段值"""
        if field.value_type == "static":
            return field.default

        value = self._get_nested_value(data, field.data_path)
        if value is None:
            return field.default

        # 应用格式化器
        if field.formatter:
            value = self._apply_formatter(value, field.formatter, data)

        return value

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Optional[Any]:
        """获取嵌套数据值，如 'customer.name' -> data['customer']['name']"""
        if not path:
            return None

        parts = path.split(".")
        value = data

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

            if value is None:
                return None

        return value

    def _apply_formatter(self, value: Any, formatter: str, data: Dict[str, Any]) -> Any:
        """应用格式化器"""
        formatters = {
            "date": lambda v: self._format_date(v),
            "date_dmy": lambda v: self._format_date_dmy(v),
            "pi_no": lambda v: f"PI.NO.:{v}" if v else "",
            "concat": lambda v: v if isinstance(v, str) else str(v),
            "sum": lambda v: self._calculate_sum(data),
            "multiply": lambda v: v,
        }
        fmt = formatters.get(formatter)
        return fmt(value) if fmt else value

    def _format_date(self, date_value: Any) -> str:
        """格式化日期为 YYYY/MM/DD"""
        if hasattr(date_value, "strftime"):
            return date_value.strftime("%Y/%m/%d")
        return str(date_value)

    def _format_date_dmy(self, date_value: Any) -> str:
        """格式化日期为 DD/MM/YYYY"""
        if hasattr(date_value, "strftime"):
            return date_value.strftime("%d/%m/%Y")
        return str(date_value)

    def _calculate_sum(self, data: Dict[str, Any]) -> float:
        """计算汇总值"""
        return 0.0

    def _set_cell(self, ws: Any, cell: str, value: Any):
        """设置单元格值"""
        ws[cell] = value

    def _apply_styles(self, ws: Any):
        """应用样式"""
        pass

    def _save_to_bytes(self, wb: Workbook) -> bytes:
        """保存为字节流"""
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()