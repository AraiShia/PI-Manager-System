"""导出相关 Pydantic 模型"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ExportRequest(BaseModel):
    """导出请求"""
    format: Optional[str] = "template"  # template | simple
    edited_fields: Optional[Dict[str, Any]] = None  # 编辑后的字段


class PreviewResponse(BaseModel):
    """预览响应"""
    summary: Dict[str, Any]
    items: List[Dict[str, Any]]
    validation_errors: List[str]


class ExportResponse(BaseModel):
    """导出响应"""
    filename: str
    content_type: str