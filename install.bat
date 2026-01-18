@echo off
chcp 65001 >nul 2>nul
title Stock Analysis System - Install

echo ========================================
echo    Stock Analysis System - Install
echo ========================================
echo.

set "ROOT_DIR=%~dp0"

echo [Check] Python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [Error] Python not found
    echo [Tip] Download from https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version

echo.
echo [Check] Node.js...
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [Error] Node.js not found
    echo [Tip] Download from https://nodejs.org/
    pause
    exit /b 1
)
node --version

echo.
echo [Check] npm...
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [Error] npm not found
    pause
    exit /b 1
)
npm --version

echo.
echo ========================================
echo    Installing Dependencies
echo ========================================
echo.

echo [1/4] Creating Python virtual environment...
cd /d "%ROOT_DIR%backend"
if exist venv (
    echo [Info] venv already exists, skipping
) else (
    python -m venv venv
    echo [Done] venv created
)

echo.
echo [2/4] Installing backend dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [Error] Backend install failed
    pause
    exit /b 1
)
echo [Done] Backend dependencies installed
call deactivate

echo.
echo [3/4] Installing frontend dependencies...
cd /d "%ROOT_DIR%frontend"
call npm install
if %errorlevel% neq 0 (
    echo [Error] Frontend install failed
    pause
    exit /b 1
)
echo [Done] Frontend dependencies installed

echo.
echo [4/4] Creating data directory...
if not exist "%ROOT_DIR%backend\data" mkdir "%ROOT_DIR%backend\data"
echo [Done] Data directory created

echo.
echo ========================================
echo    Installation Complete!
echo ========================================
echo.
echo    Run start.bat to start the system
echo.
echo ========================================
echo.
pause
