"""导出模板配置模块"""

from .config import (
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
    CONTRACT_CLAUSES,
)

from .base_template import (
    TemplateField,
    TemplateSection,
    TemplateConfig,
)

from .pi_template import PI_TEMPLATE
from .ci_template import CI_TEMPLATE
from .pl_template import PL_TEMPLATE
from .purchase_template import PURCHASE_TEMPLATE

__all__ = [
    "COMPANY_NAME_CN",
    "COMPANY_NAME_EN",
    "COMPANY_ADDRESS",
    "COMPANY_PHONE",
    "COMPANY_TEL",
    "COMPANY_EMAIL",
    "BANK_NAME",
    "BANK_ADDRESS",
    "SWIFT_BIC",
    "ACCOUNT_NO",
    "DEFAULT_LOADING_PORT",
    "DEFAULT_MARKS",
    "CONTRACT_CLAUSES",
    "TemplateField",
    "TemplateSection",
    "TemplateConfig",
    "PI_TEMPLATE",
    "CI_TEMPLATE",
    "PL_TEMPLATE",
    "PURCHASE_TEMPLATE",
]