"""基础模板类定义"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, List, Dict


@dataclass
class TemplateField:
    """模板字段定义"""
    cell: str                          # 单元格位置，如 "A1", "B12"
    value_type: str                    # 值类型：static, dynamic, calculation
    data_path: str = ""                # 数据路径，如 "customer.customer_name"
    formatter: Optional[str] = None    # 格式化函数名
    default: Any = None                # 默认值
    required: bool = False             # 是否必填


@dataclass
class TemplateSection:
    """模板区块定义"""
    name: str                          # 区块名称
    fields: List[TemplateField] = field(default_factory=list)
    start_row: int = 0                 # 起始行
    end_row: int = 0                   # 结束行
    repeatable: bool = False           # 是否可重复（如产品明细行）
    repeat_start_row: int = 0         # 重复项起始行
    repeat_data_path: str = ""         # 重复数据路径，如 "items"


@dataclass
class TemplateConfig:
    """完整模板配置"""
    name: str                          # 模板名称
    sheet_name: str                    # Excel工作表名称
    sections: List[TemplateSection] = field(default_factory=list)
    styles: Dict[str, Any] = field(default_factory=dict)  # 样式配置