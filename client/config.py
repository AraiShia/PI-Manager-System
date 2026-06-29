# -*- coding: utf-8 -*-
import os

class Config:
    API_BASE_URL = os.environ.get("PI_API_URL", "http://localhost:8000")

    # 自动更新配置
    APP_VERSION = "v1.0.0.28"  # 客户端版本号
    UPDATE_SERVER_URL = os.environ.get("PI_UPDATE_SERVER", "https://updateservice.wakabashia.tj.cn")  # 更新服务地址
    AUTO_CHECK_UPDATE = True  # 是否自动检查更新

    # 机器码 → 部门（租户）映射表
    # 用于客户端机器码自动识别所属公司/租户。
    # key: 机器码（由 utils.machine_id.get_machine_code() 获取）
    # value: 部门 ID，需与 DEPARTMENT_DB_CONFIG 的 key 一致
    MACHINE_DEPT_MAP = {
        # 示例："33e1fd4c360c11b2a85cc36ef7e73db1": "S",
    }

    # 部门数据库配置映射（隐藏，不对外显示）
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

    # 默认数据库配置（用于环境变量覆盖）
    DB_HOST = os.environ.get("PI_DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("PI_DB_PORT", "3306"))
    DB_USER = os.environ.get("PI_DB_USER", "pi_user")
    DB_PASSWORD = os.environ.get("PI_DB_PASSWORD", "pi@pass123")
    DB_NAME = os.environ.get("PI_DB_NAME", "pi_manager")