@echo off
title PI Order Management System

echo ======================================
echo    PI Order Management System
echo ======================================
echo.

cd /d "%~dp0"

if not exist "backend\main.py" (
    echo [ERROR] Backend not found
    pause
    exit /b 1
)

if not exist "client\main.py" (
    echo [ERROR] Client not found
    pause
    exit /b 1
)

echo [1/4] Checking Python...
py --version
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

echo.
echo [2/4] Installing backend dependencies...
cd backend
py -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Backend dependencies install failed!
    cd ..
    pause
    exit /b 1
)
cd ..

echo.
echo [3/4] Installing client dependencies...
cd client
py -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Client dependencies install failed!
    cd ..
    pause
    exit /b 1
)
cd ..

echo.
echo [4/4] Starting services...
start "PI-Manager-Backend" /min cmd /c "cd backend && py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo Waiting for backend...
ping -n 4 127.0.0.1 >nul

start "" py main.py

echo.
echo ======================================
echo    Started!
echo    Backend: http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo ======================================
echo.
echo Press any key to exit...
pause >nul