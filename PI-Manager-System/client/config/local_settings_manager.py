"""
本地设置管理模块
用于存储和管理本地配置文件（不涉及数据库）
"""
import json
import os

# 获取配置目录
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(CONFIG_DIR, "local_settings.json")

# 默认设置
DEFAULT_SETTINGS = {
    "default_profit_margin": 25.0,
    "exchange_rate": 7.24
}


def load_local_settings():
    """加载本地设置"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                return settings
        else:
            # 文件不存在，返回默认值并创建
            save_local_settings(DEFAULT_SETTINGS)
            return DEFAULT_SETTINGS
    except Exception as e:
        print(f"[WARN] 加载本地设置失败: {e}")
        return DEFAULT_SETTINGS.copy()


def save_local_settings(settings):
    """保存本地设置"""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ERROR] 保存本地设置失败: {e}")
        return False


def get_setting(key, default=None):
    """获取单个设置值"""
    settings = load_local_settings()
    return settings.get(key, default)


def set_setting(key, value):
    """设置单个值并保存"""
    settings = load_local_settings()
    settings[key] = value
    return save_local_settings(settings)


# 便捷函数
def get_profit_margin():
    """获取毛利率"""
    return get_setting("default_profit_margin", 25.0)


def get_exchange_rate():
    """获取汇率"""
    return get_setting("exchange_rate", 7.24)


def save_profit_margin(margin):
    """保存毛利率"""
    return set_setting("default_profit_margin", margin)


def save_exchange_rate(rate):
    """保存汇率"""
    return set_setting("exchange_rate", rate)