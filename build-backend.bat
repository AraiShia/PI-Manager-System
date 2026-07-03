@echo off
echo ========================================
echo   快速打包 - 仅后端
echo ========================================
cd /d "%~dp0backend"
py -m PyInstaller PI-Manager-Server.spec --clean --noconfirm
if errorlevel 1 (
    echo [错误] 后端打包失败
    pause
    exit /b 1
)
echo.
echo 后端打包完成！
echo 输出: backend\dist\PI-Manager-Server\
pause
