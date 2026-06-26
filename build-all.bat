@echo off
REM PI Manager Build Script - Build both server and client

echo ========================================
echo PI Manager Build Script
echo ========================================

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo.
echo [1/6] Checking Python...
py --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

echo.
echo [2/6] Installing pyinstaller...
py -m pip install pyinstaller --quiet

echo.
echo [3/6] Cleaning previous builds...
if exist "backend\build" rmdir /s /q "backend\build"
if exist "backend\dist" rmdir /s /q "backend\dist"
if exist "client\build" rmdir /s /q "client\build"
if exist "client\dist" rmdir /s /q "client\dist"

echo.
echo [4/6] Installing backend dependencies...
cd backend
py -m pip install -r requirements.txt --quiet
cd ..

echo.
echo [5/6] Installing client dependencies...
cd client
py -m pip install -r requirements.txt --quiet
cd ..

echo.
echo [6/6] Building packages...
echo.

REM Build backend server
echo ========================================
echo Building Backend Server...
echo ========================================
cd backend
py -m PyInstaller PI-Manager-Server.spec --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] Backend build failed!
    goto :error
)
cd ..

REM Build client
echo ========================================
echo Building Client...
echo ========================================
cd client
py -m PyInstaller client.spec --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] Client build failed!
    goto :error
)
cd ..

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Backend: %SCRIPT_DIR%backend\dist\PI-Manager-Server\PI-Manager-Server.exe
echo Client: %SCRIPT_DIR%client\dist\PI_Manager_Client_v2\PI_Manager_Client_v2.exe
echo.
echo Usage:
echo 1. Start backend server first
echo 2. Then start client
echo.
goto :end

:error
echo.
echo ========================================
echo Build failed. Please check the logs.
echo ========================================

:end
pause