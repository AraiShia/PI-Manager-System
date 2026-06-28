# -*- mode: python ; coding: utf-8 -*-
"""
PI Manager Client - PyInstaller spec file
客户端打包配置
"""

import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# 客户端根目录
client_dir = os.path.dirname(os.path.abspath(SPEC))

# 收集 PySide6 相关模块
hiddenimports = [
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtNetwork',
    'PySide6.QtSvg',
    'PySide6.QtSvgWidgets',
    'requests',
    'openpyxl',
    'pymysql',
    'sqlalchemy',
    'sqlalchemy.dialects',
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.dialects.mysql',
]

# 添加项目模块
hiddenimports += collect_submodules('api')
hiddenimports += collect_submodules('config')
hiddenimports += collect_submodules('dialogs')
hiddenimports += collect_submodules('services')
hiddenimports += collect_submodules('utils')
hiddenimports += collect_submodules('widgets')

# PySide6 数据文件
datas = []

# 收集配置文件
config_path = os.path.join(client_dir, 'config', 'local_settings.json')
if os.path.exists(config_path):
    datas.append((config_path, 'config'))

a = Analysis(
    ['main.py'],
    pathex=[client_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PI_Manager_Client_v2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PI_Manager_Client_v2',
)
