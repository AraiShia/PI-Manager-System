# 产品类别定义（两级结构）
# 一级类别：大类分类（汽配件 C、办公家具 F、百货类 B）
# 二级类别：具体分类（发动机 C01、曲轴 C02、椅子类 F01 等）

from functools import lru_cache

# 一级类别（用于筛选和展示）
PARENT_CATEGORIES = [
    {"code": "C", "name": "汽配件", "description": "汽车零部件及配件"},
    {"code": "F", "name": "办公家具", "description": "办公桌椅及定制家具"},
    {"code": "B", "name": "百货类", "description": "日用百货"},
]

# 二级类别（扁平化存储，通过 parent_code 关联一级类别）
CATEGORIES = [
    # 汽配件 (C)
    {"code": "C01", "name": "发动机", "parent_code": "C", "description": "发动机相关零部件"},
    {"code": "C02", "name": "曲轴", "parent_code": "C", "description": "发动机曲轴"},
    {"code": "C03", "name": "刹车片", "parent_code": "C", "description": "制动系统刹车片"},
    {"code": "C09", "name": "杂项", "parent_code": "C", "description": "其他汽配件"},
    
    # 办公家具 (F)
    {"code": "F01", "name": "椅子类", "parent_code": "F", "description": "各类椅子"},
    {"code": "F02", "name": "桌子类", "parent_code": "F", "description": "各类桌子"},
    {"code": "F88", "name": "工程定制", "parent_code": "F", "description": "定制办公家具"},
    
    # 百货类 (B)
    {"code": "B00", "name": "百货类", "parent_code": "B", "description": "日用百货"},
]


def get_parent_category_options():
    """获取一级类别下拉框选项（用于 QComboBox）"""
    return [(cat["code"], cat["name"]) for cat in PARENT_CATEGORIES]


def get_child_category_options(parent_code):
    """根据父类别代码获取子类别选项
    Args:
        parent_code: 一级类别代码（如 'C'、'F'、'B'）
    Returns:
        list: [(code, name), ...] 子类别选项列表
    """
    print(f"[类别服务] get_child_category_options called, parent_code: {parent_code!r}")
    if not parent_code:
        print(f"[类别服务] parent_code为空，返回空列表")
        return []
    
    result = [(cat["code"], cat["name"]) for cat in CATEGORIES if cat["parent_code"] == parent_code]
    print(f"[类别服务] 找到 {len(result)} 个子类别: {result}")
    return result


def get_category_options():
    """获取所有类别下拉框选项（用于 QComboBox）"""
    return [(cat["code"], cat["name"]) for cat in CATEGORIES]


def get_category_code(name):
    """根据名称获取类别代码"""
    for cat in CATEGORIES:
        if cat["name"] == name:
            return cat["code"]
    return None


def get_category_name(code):
    """根据代码获取类别名称（支持一级和二级）
    Args:
        code: 类别代码（如 'C'、'C01'、'F01'）
    Returns:
        str: 类别名称，如果找不到则返回原代码
    """
    # 先查找二级类别
    for cat in CATEGORIES:
        if cat["code"] == code:
            return cat["name"]
    
    # 再查找一级类别
    for cat in PARENT_CATEGORIES:
        if cat["code"] == code:
            return cat["name"]
    
    # 找不到则返回原代码
    return code


def get_parent_code(category_code):
    """根据二级代码获取一级代码（如 C01 → C）
    Args:
        category_code: 二级类别代码（如 'C01'）
    Returns:
        str: 一级类别代码，如果找不到则返回 None
    """
    for cat in CATEGORIES:
        if cat["code"] == category_code:
            return cat.get("parent_code")
    return None


@lru_cache(maxsize=128)
def get_category_full_path(code):
    """获取类别完整路径（如 "汽配件 > 发动机"）
    Args:
        code: 二级类别代码（如 'C01'）
    Returns:
        str: 完整路径，如 "汽配件 > 发动机"
    """
    if not code:
        return '-'
    
    # 查找二级类别
    for cat in CATEGORIES:
        if cat["code"] == code:
            parent_code = cat.get("parent_code")
            parent_name = get_category_name(parent_code)
            return f"{parent_name} > {cat['name']}"
    
    # 如果是一级类别，直接返回名称
    return get_category_name(code)
