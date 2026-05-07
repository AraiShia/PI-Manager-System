# 产品类别配置文件
# 格式：类别代码 -> (类别名称, 类别描述)

PRODUCT_CATEGORIES = {
    "01": {"name": "发动机", "description": "汽配件类 - 发动机零件"},
    "02": {"name": "曲轴", "description": "汽配件类 - 曲轴零件"},
    "03": {"name": "刹车片", "description": "汽配件类 - 刹车片"},
    "04": {"name": "杂项", "description": "汽配件类 - 其他杂项"},
    "11": {"name": "椅子类", "description": "办公家具类 - 椅子"},
    "12": {"name": "桌子类", "description": "办公家具类 - 桌子"},
    "88": {"name": "工程定制", "description": "办公家具类 - 工程定制"},
    "21": {"name": "百货类", "description": "百货类"}
}

def get_category_name(code: str) -> str:
    """根据类别代码获取类别名称"""
    return PRODUCT_CATEGORIES.get(code, {}).get("name", f"未知类别({code})")

def get_category_description(code: str) -> str:
    """根据类别代码获取类别描述"""
    return PRODUCT_CATEGORIES.get(code, {}).get("description", "")

def get_category_code(name: str) -> str:
    """根据类别名称获取类别代码"""
    for code, info in PRODUCT_CATEGORIES.items():
        if info["name"] == name:
            return code
    return "01"  # 默认返回发动机类别

def get_all_categories() -> list:
    """获取所有类别列表"""
    return [(code, info["name"], info["description"]) for code, info in PRODUCT_CATEGORIES.items()]

def get_category_options() -> list:
    """获取用于下拉框的类别选项列表"""
    return [(code, info["name"]) for code, info in PRODUCT_CATEGORIES.items()]