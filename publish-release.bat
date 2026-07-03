@echo off
REM 本地发布脚本 - 发布新版本到更新服务
REM 用法: publish-release.bat [版本号] [更新说明] [是否强制更新]

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ========================================
echo   PI Manager 版本发布脚本
echo   发布到更新服务
echo ========================================
echo.

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

set TAG=v%VERSION%

REM 获取更新说明
set RELEASE_NOTE=%2
if "%RELEASE_NOTE%"=="" (
    set /p RELEASE_NOTE="请输入更新说明: "
)
if "%RELEASE_NOTE%"=="" set RELEASE_NOTE=新版本发布

REM 是否强制更新
set FORCE_UPDATE=false
set /p FORCE_INPUT="是否强制更新? (y/N): "
if /i "%FORCE_INPUT%"=="y" set FORCE_UPDATE=true

REM 获取更新服务地址和 Token
set UPDATE_SERVICE_URL=
set UPDATE_SERVICE_TOKEN=
if exist "publish-config.txt" (
    for /f "tokens=1,2 delims==" %%a in (publish-config.txt) do (
        if "%%a"=="UPDATE_SERVICE_URL" set UPDATE_SERVICE_URL=%%b
        if "%%a"=="UPDATE_SERVICE_TOKEN" set UPDATE_SERVICE_TOKEN=%%b
    )
)

if "%UPDATE_SERVICE_URL%"=="" (
    set /p UPDATE_SERVICE_URL="请输入更新服务地址 (如 https://updateservice.wakabashia.tj.cn): "
)
if "%UPDATE_SERVICE_TOKEN%"=="" (
    set /p UPDATE_SERVICE_TOKEN="请输入管理 Token: "
)

REM 保存配置
(
echo UPDATE_SERVICE_URL=%UPDATE_SERVICE_URL%
echo UPDATE_SERVICE_TOKEN=%UPDATE_SERVICE_TOKEN%
) > publish-config.txt

echo.
echo ========================================
echo   版本: %TAG%
echo   更新说明: %RELEASE_NOTE%
echo   强制更新: %FORCE_UPDATE%
echo   更新服务: %UPDATE_SERVICE_URL%
echo ========================================
echo.
set /p CONFIRM="确认发布? (y/N): "
if /i not "%CONFIRM%"=="y" (
    echo 已取消
    pause
    exit /b 0
)

echo.
echo 正在发布客户端...
curl -s -X POST "%UPDATE_SERVICE_URL%/api/admin/release" ^
  -H "X-Admin-Token: %UPDATE_SERVICE_TOKEN%" ^
  -H "Content-Type: application/json" ^
  -d "{\"tag\": \"%TAG%\", \"component\": \"client\", \"changelog\": \"%RELEASE_NOTE%\", \"force_update\": %FORCE_UPDATE%}"
echo.

echo.
echo 正在发布服务端...
curl -s -X POST "%UPDATE_SERVICE_URL%/api/admin/release" ^
  -H "X-Admin-Token: %UPDATE_SERVICE_TOKEN%" ^
  -H "Content-Type: application/json" ^
  -d "{\"tag\": \"%TAG%\", \"component\": \"server\", \"changelog\": \"%RELEASE_NOTE%\", \"force_update\": %FORCE_UPDATE%}"
echo.

echo.
echo ========================================
echo   发布完成！
echo ========================================
echo.
echo 验证:
echo   GET %UPDATE_SERVICE_URL%/api/version/client/%TAG%
echo   GET %UPDATE_SERVICE_URL%/api/version/server/%TAG%
echo.
pause
