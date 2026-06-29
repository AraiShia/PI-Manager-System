# 配置模块
"""
client/config - 本地配置管理

包含：
- config.py (父级): API配置、数据库配置 (Config类)
- local_settings_manager.py: 本地设置文件读写
- product_categories.py: 产品类目定义
"""

# 导入 Config 类（从父级 config.py）
import sys
import os

# 获取 client 目录的父目录路径
_client_dir = os.path.dirname(os.path.dirname(__file__))
_config_py_path = os.path.join(_client_dir, 'config.py')

# 动态导入 Config 类
if os.path.exists(_config_py_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("parent_config", _config_py_path)
    parent_config_module = importlib.util.module_from_spec(spec)
    sys.modules['parent_config'] = parent_config_module
    spec.loader.exec_module(parent_config_module)
    Config = parent_config_module.Config
else:
    # 如果不存在，创建一个默认的 Config 类
    class Config:
        API_BASE_URL = "http://localhost:8000"
        APP_VERSION = "v1.0.0.28"
        UPDATE_SERVER_URL = "https://updateservice.wakabashia.tj.cn"
        AUTO_CHECK_UPDATE = True
        # 2026-06-29 修复：兜底 Config 缺少 MACHINE_DEPT_MAP / DEPARTMENT_DB_CONFIG，
        # 防止打包后 utils.machine_id 调用 Config.MACHINE_DEPT_MAP、
        # auth.py 读取 Config.DEPARTMENT_DB_CONFIG 填充部门下拉时崩溃/为空
        MACHINE_DEPT_MAP = {}
        DEPARTMENT_DB_CONFIG = {
            "S": {
                "name": "S - 索英普",
                "db_name": "pi_manager_s",
                "db_host": "localhost",
                "db_port": 3306,
                "db_user": "pi_user",
                "db_password": "pi@pass123"
            },
            "W": {
                "name": "W - 维那",
                "db_name": "pi_manager_w",
                "db_host": "localhost",
                "db_port": 3306,
                "db_user": "pi_user",
                "db_password": "pi@pass123"
            },
            "M": {
                "name": "M - 马迪那",
                "db_name": "pi_manager_m",
                "db_host": "localhost",
                "db_port": 3306,
                "db_user": "pi_user",
                "db_password": "pi@pass123"
            },
            "D": {
                "name": "D - 银达",
                "db_name": "pi_manager_d",
                "db_host": "localhost",
                "db_port": 3306,
                "db_user": "pi_user",
                "db_password": "pi@pass123"
            }
        }
        DB_HOST = "localhost"
        DB_PORT = 3306
        DB_USER = "pi_user"
        DB_PASSWORD = "pi@pass123"
        DB_NAME = "pi_manager"

# 导入本地设置管理器
from .local_settings_manager import (
    load_local_settings,
    save_local_settings,
    get_setting,
    set_setting,
    get_profit_margin,
    get_exchange_rate,
    save_profit_margin,
    save_exchange_rate,
    load_system_config
)

__all__ = [
    # Config 类（从父级 config.py 导入）
    'Config',
    
    # 本地设置管理器
    'load_local_settings',
    'save_local_settings',
    'get_setting',
    'set_setting',
    'get_profit_margin',
    'get_exchange_rate',
    'save_profit_margin',
    'save_exchange_rate',
    'load_system_config'
]
