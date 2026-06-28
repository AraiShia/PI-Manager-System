# -*- mode: python ; coding: utf-8 -*-
"""
PI Manager Server - PyInstaller spec file
后端服务打包配置
"""

import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# 后端根目录
backend_dir = os.path.dirname(os.path.abspath(SPEC))

# 收集所有子模块
hiddenimports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'fastapi',
    'starlette',
    'sqlalchemy',
    'sqlalchemy.dialects',
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.dialects.mysql',
    'pydantic',
    'pydantic.v1',
    'pymysql',
    'openpyxl',
    'xlrd',
    'yaml',
    'multipart',
    'cryptography',
]

# 添加项目模块
hiddenimports += collect_submodules('app')
hiddenimports += collect_submodules('config')
hiddenimports += collect_submodules('crud')
hiddenimports += collect_submodules('exporters')
hiddenimports += collect_submodules('models')
hiddenimports += collect_submodules('routers')
hiddenimports += collect_submodules('schemas')
hiddenimports += collect_submodules('services')
hiddenimports += collect_submodules('tasks')
hiddenimports += collect_submodules('templates')
hiddenimports += collect_submodules('utils')

# 收集数据文件
datas = [
    (os.path.join(backend_dir, 'templates'), 'templates'),
]

a = Analysis(
    ['run.py'],
    pathex=[backend_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='PI-Manager-Server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
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
    name='PI-Manager-Server',
)
