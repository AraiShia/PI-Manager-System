"""
自动更新检查模块
对接 https://updateservice.wakabashia.tj.cn API
与 main.py 中的 check_for_updates() 逻辑保持一致

🔧 2026-06-29 重写：原实现调用 GitHub API，不符合更新服务 API 规范
"""

import os
import sys
import json
import requests
from typing import Optional, Dict, Any, Tuple
from PySide6.QtCore import QThread, Signal


def get_app_dir() -> str:
    """获取应用程序目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_current_version() -> str:
    """获取当前版本号"""
    version_file = os.path.join(get_app_dir(), "version.json")
    if not os.path.exists(version_file):
        version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "version.json")

    if os.path.exists(version_file):
        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('version', '1.0.0')
        except Exception:
            pass
    return '1.0.0'


def get_update_server_url() -> str:
    """获取更新服务地址"""
    version_file = os.path.join(get_app_dir(), "version.json")
    if not os.path.exists(version_file):
        version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "version.json")

    if os.path.exists(version_file):
        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('update_check_url', '')
        except Exception:
            pass
    return ''


def _strip_version_prefix(version: str) -> str:
    """
    🔧 2026-06-29 新增（A3 修复）：
    从 'client/v1.0.0.10' 或 'v1.0.0.10' 中提取纯版本号 '1.0.0.10'
    """
    # 先去掉开头可能的 "client/" 或 "server/" 前缀
    for prefix in ('client/', 'server/'):
        if version.startswith(prefix):
            version = version[len(prefix):]
    # 再去掉开头的 'v' 前缀
    return version.lstrip('v')


def _normalize_version_parts(version: str) -> list:
    """
    将版本号字符串拆分为数字段（处理 A3 修复后的纯版本号）
    例如: '1.0.0.25' -> [1, 0, 0, 25]
    """
    stripped = _strip_version_prefix(version)
    parts = []
    for part in stripped.split('.'):
        try:
            parts.append(int(part))
        except ValueError:
            # 跳过无法转为整数的部分（如 0a, 1b）
            parts.append(0)
    return parts


def compare_versions(v1: str, v2: str) -> int:
    """
    🔧 2026-06-29 修复（A3）：
    原实现只 strip('v')，无法处理 'client/v1.0.0.10' 格式。
    修复后先去掉 'client/'/'server/' 前缀，再去掉 'v' 前缀。

    返回: 1 if v1 > v2, -1 if v1 < v2, 0 if equal
    """
    try:
        parts1 = _normalize_version_parts(v1)
        parts2 = _normalize_version_parts(v2)
        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))
        for a, b in zip(parts1, parts2):
            if a > b:
                return 1
            if a < b:
                return -1
        return 0
    except Exception:
        return 0


def _check_min_compatible(current_version: str, min_compatible: str) -> Tuple[bool, str]:
    """
    🔧 2026-06-29 新增（A4 修复）：
    检查当前版本是否低于最低兼容版本。

    Args:
        current_version: 当前版本（如 '1.0.0.21'）
        min_compatible: 最低兼容版本（如 '1.0.0'）

    Returns:
        (is_blocked, message)
        - is_blocked=True 时必须阻止启动
    """
    if not min_compatible:
        return False, ""
    # current < min_compatible 时阻塞
    if compare_versions(current_version, min_compatible) < 0:
        return True, (
            f"当前版本 ({current_version}) 低于最低兼容版本 ({min_compatible})，"
            f"请先升级到最新版本后再启动。"
        )
    return False, ""


def check_latest_version() -> Optional[Dict[str, Any]]:
    """
    🔧 2026-06-29 重写（A2 修复）：
    对接更新服务 API: GET /api/version/client/{current_version}
    返回格式与 main.py check_for_updates() 一致。

    返回: {
        'has_update': bool,
        'latest_version': str,  # 纯版本号（不含 client/ 前缀），如 '1.0.0.25'
        'min_compatible': str,  # 最低兼容版本（可能为空）
        'changelog': str,
        'force_update': bool,
        'download_url': str,    # 可能为相对路径
        'sha256_url': str,       # 可能为相对路径
        'is_blocked': bool,     # 是否低于最低兼容版本
        'block_message': str,
    }
    """
    from config import Config

    update_server = Config.UPDATE_SERVER_URL
    if not update_server:
        return None

    # 🔧 2026-06-30 修复：API 要求版本号带 "v" 前缀
    current_version = Config.APP_VERSION
    if not current_version.startswith("v"):
        current_version = f"v{current_version}"
    url = f"{update_server}/api/version/client/{current_version}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"[Update] 检查更新失败: HTTP {response.status_code}")
            return None

        data = response.json()

        latest_raw = data.get("latest", "")
        latest_version = _strip_version_prefix(latest_raw)

        # 🔧 2026-06-30 修复：min_compatible 在 VersionCheckResponse 中不存在，
        # 它在 VersionResponse.components.client.min_compatible 中
        # 由于 check_version API 不返回 min_compatible，暂时设为空
        # 后续可考虑同时调用 /api/version 获取全局信息来补充
        min_compatible = ""
        is_blocked, block_message = _check_min_compatible(current_version, min_compatible)

        changelog = data.get("changelog", "")
        force_update = data.get("force", False)
        download_url = data.get("download_url", "")
        sha256_url = data.get("sha256_url", "")

        # A6 修复：统一处理相对路径拼接（在返回值层面处理，调用方无需再处理）
        if download_url and not download_url.startswith("http"):
            download_url = f"{update_server}{download_url}"
        if sha256_url and not sha256_url.startswith("http"):
            sha256_url = f"{update_server}{sha256_url}"

        return {
            'has_update': data.get("has_update", False),
            'latest_version': latest_version,
            'min_compatible': min_compatible,
            'changelog': changelog,
            'force_update': force_update,
            'download_url': download_url,
            'sha256_url': sha256_url,
            'is_blocked': is_blocked,
            'block_message': block_message,
        }
    except Exception as e:
        print(f"[Update] 检查更新异常: {e}")
        return None


class UpdateCheckThread(QThread):
    """
    🔧 2026-06-29 重写：
    使用更新服务 API，不再调用 GitHub API。
    与 main.py check_for_updates() 逻辑对齐。
    """
    check_finished = Signal(bool, dict)  # has_update, version_info
    check_failed = Signal(str)           # error_message

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            latest = check_latest_version()

            if not latest:
                self.check_failed.emit("无法获取最新版本信息")
                return

            # 如果低于最低兼容版本，直接触发 update dialog 显示阻止消息
            if latest.get('is_blocked'):
                self.check_finished.emit(True, latest)
                return

            has_update = latest.get('has_update', False)
            self.check_finished.emit(has_update, latest)
        except Exception as e:
            self.check_failed.emit(str(e))
