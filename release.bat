@echo off
REM 本地发布脚本 - 打包并发布新版本
REM 用法: release.bat [版本号] [更新说明] [是否强制更新]

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ========================================
echo   PI Manager 本地发布脚本
echo ========================================
echo.

REM 检查 Python
py --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 获取版本号
set VERSION=%1
if "%VERSION%"=="" (
    set /p VERSION="请输入版本号 (如 1.0.0): "
)
if "%VERSION%"=="" (
    echo [错误] 版本号不能为空
    pause
    exit /b 1
)

REM 获取更新说明
set RELEASE_NOTE=%2
if "%RELEASE_NOTE%"=="" (
    set /p RELEASE_NOTE="请输入更新说明: "
)

REM 是否强制更新
set FORCE_UPDATE=0
set /p FORCE_INPUT="是否强制更新? (0=否, 1=否, 默认0): "
if "%FORCE_INPUT%"=="1" set FORCE_UPDATE=1

echo.
echo ========================================
echo   版本: %VERSION%
echo   更新说明: %RELEASE_NOTE%
echo   强制更新: %FORCE_UPDATE%
echo ========================================
echo.
pause

REM 更新版本号
echo [1/5] 更新版本号...
py -c "
import json, re
from datetime import datetime

version = '%VERSION%'
build_date = datetime.now().strftime('%Y-%m-%d')

# 更新客户端 config.py
with open('client/config.py', 'r', encoding='utf-8') as f:
    content = f.read()
content = re.sub(r'APP_VERSION\s*=\s*\"v?[\d.]+\"', f'APP_VERSION = \"v{version}\"', content)
with open('client/config.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('  - client/config.py updated')

# 更新客户端 version.json
try:
    with open('client/version.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    data['version'] = version
    data['build_date'] = build_date
    with open('client/version.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print('  - client/version.json updated')
except:
    pass

# 更新服务端 version.json
try:
    with open('backend/version.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    data['version'] = version
    data['build_date'] = build_date
    with open('backend/version.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print('  - backend/version.json updated')
except:
    pass
"
if errorlevel 1 (
    echo [错误] 更新版本号失败
    pause
    exit /b 1
)
echo   完成

REM 打包
echo.
echo [2/5] 打包后端...
cd backend
py -m PyInstaller PI-Manager-Server.spec --clean --noconfirm
if errorlevel 1 (
    echo [错误] 后端打包失败
    cd ..
    pause
    exit /b 1
)
cd ..
echo   完成

echo.
echo [3/5] 打包客户端...
cd client
py -m PyInstaller client.spec --clean --noconfirm
if errorlevel 1 (
    echo [错误] 客户端打包失败
    cd ..
    pause
    exit /b 1
)
cd ..
echo   完成

REM 生成发布包
echo.
echo [4/5] 生成发布包...
if not exist "dist" mkdir "dist"

set CLIENT_ZIP=dist\PI-Manager-Client-v%VERSION%-win-x64.zip
set SERVER_ZIP=dist\PI-Manager-Server-v%VERSION%-win-x64.zip

REM 压缩客户端
powershell -Command "Compress-Archive -Path 'client\dist\PI_Manager_Client_v2\*' -DestinationPath '%CLIENT_ZIP%' -Force"
if errorlevel 1 (
    echo [错误] 客户端压缩失败
    pause
    exit /b 1
)

REM 压缩服务端
powershell -Command "Compress-Archive -Path 'backend\dist\PI-Manager-Server\*' -DestinationPath '%SERVER_ZIP%' -Force"
if errorlevel 1 (
    echo [错误] 服务端压缩失败
    pause
    exit /b 1
)

REM 生成 SHA256
powershell -Command "Get-FileHash '%CLIENT_ZIP%' -Algorithm SHA256 | Select-Object -ExpandProperty Hash | Out-File -FilePath '%CLIENT_ZIP%.sha256' -Encoding ascii"
powershell -Command "Get-FileHash '%SERVER_ZIP%' -Algorithm SHA256 | Select-Object -ExpandProperty Hash | Out-File -FilePath '%SERVER_ZIP%.sha256' -Encoding ascii"

echo   完成
echo.
echo   生成的文件:
echo     %CLIENT_ZIP%
echo     %CLIENT_ZIP%.sha256
echo     %SERVER_ZIP%
echo     %SERVER_ZIP%.sha256

REM 上传到更新服务（可选）
echo.
echo [5/5] 上传到更新服务...
echo.
echo   请手动上传到更新服务或 GitHub Releases
echo.

echo ========================================
echo   发布完成！
echo ========================================
echo.
echo 版本: v%VERSION%
echo 发布包位置: %cd%\dist\
echo.
pause
