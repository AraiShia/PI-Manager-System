"""导出辅助工具

提供导出模板所需的公共数据补充，例如从系统设置读取业务员信息。
"""

from typing import Dict, Any, Optional


def get_salesman_info(db: Any) -> Dict[str, str]:
    """从系统设置表中读取业务员姓名和联系电话。

    Args:
        db: SQLAlchemy Session，用于查询 SysSetting。

    Returns:
        dict: {"name": str, "phone": str}，未设置时返回空字符串。
    """
    name = ""
    phone = ""
    try:
        from models.setting import SysSetting

        name_setting = db.query(SysSetting).filter(SysSetting.key == "operator_name").first()
        if name_setting and name_setting.value:
            name = str(name_setting.value)

        phone_setting = db.query(SysSetting).filter(SysSetting.key == "operator_phone").first()
        if phone_setting and phone_setting.value:
            phone = str(phone_setting.value)
    except Exception as e:
        print(f"[WARN] 读取业务员信息失败: {e}")

    return {"name": name, "phone": phone}


def inject_salesman_info(data: Dict[str, Any], db: Any) -> Dict[str, Any]:
    """将业务员信息注入到导出数据字典的 user 字段中。

    如果 data 中已存在 user 字段，仅补充缺失的 name/phone。

    Args:
        data: 原始导出数据。
        db: SQLAlchemy Session。

    Returns:
        dict: 注入业务员信息后的数据字典。
    """
    if data is None:
        data = {}
    salesman = get_salesman_info(db)
    user = data.get("user", {})
    if not isinstance(user, dict):
        user = {}
    user.setdefault("name", salesman["name"])
    user.setdefault("phone", salesman["phone"])
    data["user"] = user
    return data
