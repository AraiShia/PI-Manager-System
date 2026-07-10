"""
本地设置管理模块
用于存储和管理本地配置文件（不涉及数据库）

数据源优先级：
1. system_config.json (集中式配置，包含产品类目、部门、系统参数)
2. local_settings.json (用户自定义覆盖)
3. DEFAULT_SETTINGS (硬编码兜底)

更新日期：2026-06-22
新增功能：支持从 data/config/system_config.json 读取系统级默认值
"""
import json
import os

# 获取配置目录
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

# 本地配置文件（按机器码隔离）
# 若 utils.machine_id 可用，则使用 local_settings_<machine_code>.json，
# 否则降级为通用的 local_settings.json。
try:
    from utils.machine_id import get_machine_code
    _machine_code = get_machine_code()
    _machine_suffix = f"_{_machine_code}"
except Exception:
    _machine_suffix = ""

SETTINGS_FILE = os.path.join(
    CONFIG_DIR, f"local_settings{_machine_suffix}.json"
)
GENERIC_SETTINGS_FILE = os.path.join(CONFIG_DIR, "local_settings.json")

# 尝试定位 system_config.json（支持开发环境和打包环境）
def _find_system_config_path():
    """
    查找 system_config.json 文件路径
    
    搜索顺序：
    1. data/config/system_config.json (相对于项目根目录)
    2. ../data/config/system_config.json (相对于 client 目录)
    3. ../../data/config/system_config.json (更深层级)
    """
    # 可能的基础路径列表
    base_paths = [
        os.path.join(os.path.dirname(CONFIG_DIR), 'data', 'config'),  # 项目根目录/data/config
        os.path.join(os.path.dirname(os.path.dirname(CONFIG_DIR)), 'data', 'config'),  # 上两级
        os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'config'),  # 相对路径
    ]
    
    for base in base_paths:
        path = os.path.join(base, 'system_config.json')
        if os.path.exists(path):
            return path
    
    return None


# system_config.json 路径（运行时动态查找）
SYSTEM_CONFIG_FILE = _find_system_config_path()

# 默认设置（最终兜底）
DEFAULT_SETTINGS = {
    "default_profit_margin": 25.0,
    "exchange_rate": 7.24
}


def load_system_config():
    """
    从 system_config.json 加载系统级默认配置
    
    Returns:
        dict: 配置字典，包含业务参数和产品类目等
              如果文件不存在或解析失败，返回空字典
    """
    if not SYSTEM_CONFIG_FILE:
        print("[DEBUG] system_config.json 未找到，将使用本地默认值")
        return {}
    
    try:
        with open(SYSTEM_CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        # 提取业务参数（与 SettingsDialog 字段对齐）
        business_params = config.get('system_config', {}).get('business_parameters', {})
        
        # 构建返回字典
        result = {}
        
        # 毛利率
        if 'default_profit_margin' in business_params:
            margin_cfg = business_params['default_profit_margin']
            result['default_profit_margin'] = float(margin_cfg.get('value', 25.0))
        
        # 汇率
        if 'exchange_rate' in business_params:
            rate_cfg = business_params['exchange_rate']
            result['exchange_rate'] = float(rate_cfg.get('value', 7.24))
        
        # 操作员信息（可选）
        operator_info = config.get('system_config', {}).get('operator_info', {})
        if 'operator_name' in operator_info:
            result['operator_name'] = ''
        if 'operator_id' in operator_info:
            result['operator_id'] = ''
        if 'dept_id' in operator_info:
            dept_cfg = operator_info['dept_id']
            result['dept_id'] = dept_cfg.get('default', 'S')
        if 'operator_role' in operator_info:
            role_cfg = operator_info['operator_role']
            result['operator_role'] = role_cfg.get('default', 'operator')
        
        print(f"[INFO] 已从 system_config.json 加载 {len(result)} 个配置项")
        print(f"[DEBUG] system_config.json 路径: {SYSTEM_CONFIG_FILE}")
        
        return result
        
    except Exception as e:
        print(f"[WARN] 读取 system_config.json 失败: {e}")
        return {}


def load_local_settings():
    """
    加载本地设置（三级降级策略）
    
    优先级：
    1. system_config.json (系统级默认值)
    2. local_settings.json (用户自定义覆盖)
    3. DEFAULT_SETTINGS (硬编码兜底)
    
    Returns:
        dict: 合并后的设置字典
    """
    # 第一级：从 system_config.json 获取系统级默认值
    settings = load_system_config()
    
    # 第二级：用机器码隔离的本地配置覆盖（用户自定义值优先）
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
                settings.update(user_settings)  # 用户设置覆盖系统默认
                print(f"[INFO] 已应用 {len(user_settings)} 个用户自定义设置")
        elif os.path.exists(GENERIC_SETTINGS_FILE):
            # 向后兼容：若不存在机器码隔离文件，则读取旧版通用配置
            with open(GENERIC_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
                settings.update(user_settings)
                print(f"[INFO] 已从通用配置迁移 {len(user_settings)} 个设置项")
        else:
            # 文件不存在，创建默认配置文件
            save_local_settings(DEFAULT_SETTINGS)
            print(f"[INFO] {os.path.basename(SETTINGS_FILE)} 不存在，已创建默认配置")
    except Exception as e:
        print(f"[WARN] 加载本地设置失败: {e}")
    
    # 第三级：确保所有必需字段都有值（硬编码兜底）
    for key, default_value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = default_value
    
    return settings


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
