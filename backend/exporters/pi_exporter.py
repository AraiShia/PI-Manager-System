"""PI 模板导出器 - 薄壳，调用通用 XlsxTemplateRenderer。

接受 get_pi_invoice_detail 返回的扁平结构（或显式嵌套结构），
在内部适配为 mapping 期望的 {pi, customer, user, company, items} 嵌套形式。
"""
import os
from typing import Any, Dict

from .xlsx_template_renderer import XlsxTemplateRenderer
from .export_helper import get_salesman_info

# 模板与 mapping 路径（相对 backend 根目录）
_TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "templates",
)


def _format_date(value: Any) -> str:
    """统一日期格式为 YYYY/MM/DD。"""
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y/%m/%d")
    s = str(value)
    # ISO 2026-05-21 -> 2026/05/21
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10].replace("-", "/")
    return s


class PIExporter:
    """PI 模板导出器（基于 xlsx 模板复用）。"""

    def __init__(self):
        self.renderer = XlsxTemplateRenderer(
            template_path=os.path.join(
                _TEMPLATES_DIR, "assets", "template_pi.xlsx"
            ),
            mapping_path=os.path.join(
                _TEMPLATES_DIR, "xlsx_mapping", "pi_mapping.yaml"
            ),
        )

    def export_pi(self, pi_data: Dict[str, Any], db: Any = None) -> bytes:
        """导出 PI xlsx 字节流。

        Args:
            pi_data: PI 数据字典。
            db: SQLAlchemy Session，用于读取系统设置中的业务员信息。
        """
        nested = self._shape_data(pi_data, db)
        return self.renderer.render(nested)

    @staticmethod
    def _shape_data(flat: Dict[str, Any], db: Any = None) -> Dict[str, Any]:
        """扁平 -> 嵌套。已是嵌套则原样返回。"""
        if not flat:
            return {}
        # 已经是嵌套形式：直接透传
        if isinstance(flat.get("pi"), dict) and isinstance(flat.get("customer"), dict):
            # 注入/补充业务员信息
            if db is not None:
                salesman = get_salesman_info(db)
                user = flat.get("user", {})
                if isinstance(user, dict):
                    user.setdefault("name", salesman["name"])
                    user.setdefault("phone", salesman["phone"])
                else:
                    user = {"name": salesman["name"], "phone": salesman["phone"]}
                flat["user"] = user
            return flat

        # 计算总金额（用于 SAY TOTAL）
        items = flat.get("items", [])
        total_amount = sum(
            float(item.get("total_price") or item.get("quantity", 0) * float(item.get("unit_price", 0)))
            for item in items if isinstance(item, dict)
        )

        # 格式化金额为英文大写（简化版）
        def _format_amount_to_words(amount):
            """将数字金额转换为英文大写格式"""
            try:
                num = float(amount)
                return f"USD {num:,.2f}"
            except (ValueError, TypeError):
                return "USD 0.00"

        return {
            "pi": {
                "pi_no": flat.get("pi_no", ""),
                "order_date": _format_date(flat.get("order_date") or flat.get("created_at")),
                "delivery_date": flat.get("delivery_date", "30 days after the deposit is paid"),
                "price_terms": flat.get("price_terms", "FOB"),
                "payment_terms": flat.get(
                    "payment_terms",
                    "T/T 10% deposit ,The 90% balance according to the BL.",
                ),
                "warranty_time": flat.get("warranty_time", "13 months after shipping date"),
                "say_total": _format_amount_to_words(total_amount),
                "remark": flat.get("remark", ""),
            },
            "customer": {
                "customer_name": flat.get("customer_name", ""),
                "phone": flat.get("phone", ""),
                "address": flat.get("address", ""),
                "country": flat.get("country", ""),
            },
            "user": {
                "name": flat.get("user_name") or (get_salesman_info(db)["name"] if db else ""),
                "phone": flat.get("user_phone") or (get_salesman_info(db)["phone"] if db else ""),
            },
            "company": {
                "phone": flat.get("company_phone") or (get_salesman_info(db)["phone"] if db else "+86 132 8282 0031"),
                "address": flat.get(
                    "company_address",
                    "Nanyuan Street, Lingping town of Hangzhou City, Zhejiang China, ZIP CODE 311000\nTEL: 0086-571-86144203\nEmail:  Lisa@viiner.com"
                ),
            },
            "items": [
                {
                    **item,
                    # 确保必要字段存在（PI模板10列：NAME/CODE/PHOTO/Description/Specification/pcs/ctn/Color/QTY/PRICE/Amount）
                    "product_name": item.get("product_name") or item.get("detail_desc") or "",
                    "photo": item.get("photo") or item.get("image_url") or item.get("product_image") or "",
                    "product_code": item.get("product_code") or item.get("model") or item.get("oe_number") or "",
                    "detail_desc": item.get("detail_desc") or item.get("description") or "",
                    "specification": item.get("specification") or "",
                    "pcs_per_carton": item.get("pcs_per_carton") or item.get("units_per_carton") or "",
                    "color": item.get("color") or "",
                }
                for item in items if isinstance(item, dict)
            ],
        }
