# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=['d:\\TraeProjects\\PI Manager\\PI-Manager-System\\backend'],
    binaries=[],
    datas=[
        ('d:\\TraeProjects\\PI Manager\\PI-Manager-System\\backend\\app', 'app'),
        ('d:\\TraeProjects\\PI Manager\\PI-Manager-System\\backend\\routers', 'routers'),
        ('d:\\TraeProjects\\PI Manager\\PI-Manager-System\\backend\\crud', 'crud'),
        ('d:\\TraeProjects\\PI Manager\\PI-Manager-System\\backend\\models', 'models'),
        ('d:\\TraeProjects\\PI Manager\\PI-Manager-System\\backend\\schemas', 'schemas'),
        ('d:\\TraeProjects\\PI Manager\\PI-Manager-System\\backend\\utils', 'utils'),
        ('d:\\TraeProjects\\PI Manager\\PI-Manager-System\\backend\\static', 'static'),
        ('d:\\TraeProjects\\PI Manager\\PI-Manager-System\\backend\\data', 'data'),
    ],
    hiddenimports=[
        'uvicorn',
        'fastapi',
        'pydantic',
        'sqlalchemy',
        'sqlite3',
        'typing_extensions',
        'starlette',
        'jinja2',
        'markdown',
    ],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PI_Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
