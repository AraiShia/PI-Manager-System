@echo off
echo ========================================
echo   快速打包 - 仅客户端
echo ========================================
cd /d "%~dp0client"
py -m PyInstaller client.spec --clean --noconfirm
if errorlevel 1 (
    echo [错误] 客户端打包失败
    pause
    exit /b 1
)
echo.
echo 客户端打包完成！
echo 输出: client\dist\PI_Manager_Client_v2\
pause
