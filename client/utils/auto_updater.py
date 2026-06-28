"""
自动更新检查模块
检查 GitHub Releases 上的最新版本
"""

import os
import sys
import json
import requests
from typing import Optional, Dict, Any
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
        except:
            pass
    return '1.0.0'


def get_update_check_url() -> str:
    """获取更新检查地址"""
    version_file = os.path.join(get_app_dir(), "version.json")
    if not os.path.exists(version_file):
        version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "version.json")
    
    if os.path.exists(version_file):
        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('update_check_url', '')
        except:
            pass
    return ''


def compare_versions(v1: str, v2: str) -> int:
    """比较版本号
    返回: 1 if v1 > v2, -1 if v1 < v2, 0 if equal
    """
    try:
        parts1 = [int(x) for x in v1.strip('v').split('.')]
        parts2 = [int(x) for x in v2.strip('v').split('.')]
        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))
        for a, b in zip(parts1, parts2):
            if a > b:
                return 1
            if a < b:
                return -1
        return 0
    except:
        return 0


def check_latest_version() -> Optional[Dict[str, Any]]:
    """检查最新版本
    返回: {'version': 'x.x.x', 'body': '更新说明', 'download_url': '下载地址', 'html_url': '发布页面'}
    """
    url = get_update_check_url()
    if not url:
        return None
    
    try:
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'PI-Manager-Client'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        
        data = response.json()
        tag_name = data.get('tag_name', '')
        version = tag_name.strip('v')
        
        assets = data.get('assets', [])
        download_url = ''
        for asset in assets:
            name = asset.get('name', '').lower()
            if 'client' in name and 'win' in name and name.endswith('.zip'):
                download_url = asset.get('browser_download_url', '')
                break
        
        if not download_url and assets:
            download_url = assets[0].get('browser_download_url', '')
        
        return {
            'version': version,
            'tag_name': tag_name,
            'body': data.get('body', ''),
            'name': data.get('name', ''),
            'download_url': download_url,
            'html_url': data.get('html_url', ''),
            'published_at': data.get('published_at', '')
        }
    except Exception as e:
        print(f"[更新检查] 失败: {e}")
        return None


class UpdateCheckThread(QThread):
    """后台更新检查线程"""
    check_finished = Signal(bool, dict)  # has_update, version_info
    check_failed = Signal(str)  # error_message
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def run(self):
        try:
            current_version = get_current_version()
            latest = check_latest_version()
            
            if not latest:
                self.check_failed.emit("无法获取最新版本信息")
                return
            
            latest_version = latest.get('version', '0.0.0')
            has_update = compare_versions(latest_version, current_version) > 0
            
            self.check_finished.emit(has_update, latest)
        except Exception as e:
            self.check_failed.emit(str(e))
