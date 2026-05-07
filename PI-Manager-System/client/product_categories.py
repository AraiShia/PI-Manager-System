# 产品类别定义
# 类别代码 类别名称 类别描述

CATEGORIES = [
    {"code": "A", "name": "发动机部件", "description": "发动机相关零部件"},
    {"code": "B", "name": "传动系统", "description": "变速箱、传动轴等"},
    {"code": "C", "name": "悬挂系统", "description": "减震器、弹簧等"},
    {"code": "D", "name": "制动系统", "description": "刹车片、刹车盘等"},
    {"code": "E", "name": "电气系统", "description": "电瓶、发电机等"},
    {"code": "F", "name": "冷却系统", "description": "散热器、水泵等"},
    {"code": "G", "name": "燃油系统", "description": "油泵、喷油嘴等"},
    {"code": "H", "name": "排气系统", "description": "排气管、消音器等"},
    {"code": "I", "name": "转向系统", "description": "方向盘、转向机等"},
    {"code": "J", "name": "车身部件", "description": "保险杠、车门等"},
]

def get_category_options():
    """获取类别下拉框选项（用于QComboBox）"""
    return [(cat["code"], cat["name"]) for cat in CATEGORIES]

def get_category_code(name):
    """根据名称获取类别代码"""
    for cat in CATEGORIES:
        if cat["name"] == name:
            return cat["code"]
    return None

def get_category_name(code):
    """根据代码获取类别名称"""
    for cat in CATEGORIES:
        if cat["code"] == code:
            return cat["name"]
    return code