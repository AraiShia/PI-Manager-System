"""
重复产品检测工具

提供预览行与订单项的重复判定键提取、重复分组、去重索引计算。
"""
from typing import Any, Dict, List, Optional, Set, Tuple


def _normalize(value: Any) -> str:
    """将值规范化为去除首尾空格的字符串，None 返回空字符串。"""
    if value is None:
        return ""
    return str(value).strip()


def extract_preview_duplicate_key(
    row: Any,
    headers: Optional[List[str]] = None,
    model_col_idx: Optional[int] = None,
) -> Tuple[str, str]:
    """
    为预览表中的一行提取重复判定键和展示文本。

    返回 (key, display)。key 为空字符串表示无法判定（不参与重复统计）。
    """
    if isinstance(row, dict):
        product_id = row.get('product_id')
        if product_id is not None and _normalize(product_id):
            display = _normalize(row.get('customer_code') or row.get('oe_number') or product_id)
            return (f"product_id:{product_id}", display)

        code = _normalize(row.get('customer_code', ''))
        oe = _normalize(row.get('oe_number', ''))
        if code or oe:
            display = code or oe
            return (f"code_oe:{code}|{oe}", display)
        return ("", "")

    # Excel 原始行（list / tuple），按 Model/客户产品编号列判定
    if isinstance(row, (list, tuple)) and model_col_idx is not None:
        if 0 <= model_col_idx < len(row):
            model = _normalize(row[model_col_idx])
            if model:
                return (f"model:{model}", model)
    return ("", "")


def find_preview_duplicates(
    rows: List[Any],
    headers: Optional[List[str]] = None,
    model_col_idx: Optional[int] = None,
    existing_keys: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """
    查找预览行中的重复分组。

    Args:
        rows: 预览行列表，元素可以是 dict（手动新增）或 list（Excel 原始行）。
        headers: Excel 表头，用于定位 Model 列（可选）。
        model_col_idx: Model 列在 Excel 行中的索引（可选）。
        existing_keys: 已存在产品的判定键集合（如当前订单已有产品、客户-产品表已有 Model）。

    Returns:
        重复分组列表，每个分组包含：
        - key: 判定键
        - display: 展示文本
        - indices: 在 rows 中出现的索引列表
        - external: 是否仅因与 existing_keys 冲突而标记为重复
    """
    existing_keys = existing_keys or set()
    groups: Dict[str, Dict[str, Any]] = {}

    for idx, row in enumerate(rows):
        key, display = extract_preview_duplicate_key(row, headers, model_col_idx)
        if not key:
            continue
        if key not in groups:
            groups[key] = {
                "key": key,
                "display": display,
                "indices": [],
                "external": False,
            }
        groups[key]["indices"].append(idx)

    duplicates: List[Dict[str, Any]] = []
    for key, group in groups.items():
        if len(group["indices"]) >= 2:
            duplicates.append(group)
        elif key in existing_keys:
            group["external"] = True
            duplicates.append(group)

    duplicates.sort(key=lambda g: g["indices"][0] if g["indices"] else 0)
    return duplicates


def filter_duplicate_indices(
    row_count: int,
    duplicate_groups: List[Dict[str, Any]],
) -> List[int]:
    """
    计算选择"跳过重复行"后应保留的行索引。

    - 内部重复：保留第一次出现，跳过后续。
    - 与外部已存在产品冲突：跳过所有冲突行。
    """
    skip: Set[int] = set()
    for group in duplicate_groups:
        indices = group.get("indices", [])
        if not indices:
            continue
        if group.get("external"):
            skip.update(indices)
        else:
            skip.update(indices[1:])
    return [i for i in range(row_count) if i not in skip]
