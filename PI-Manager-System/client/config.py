# -*- coding: utf-8 -*-
import os

class Config:
    API_BASE_URL = os.environ.get("PI_API_URL", "http://localhost:8000")
    
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