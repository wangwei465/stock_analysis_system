@echo off
chcp 65001 >nul 2>nul
title Stock Analysis System

echo ========================================
echo    Stock Analysis System - Start
echo ========================================
echo.

set "ROOT_DIR=%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [Error] Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [Error] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

echo [Info] Python version:
python --version
echo.
echo [Info] Node.js version:
node --version
echo.

if not exist "%ROOT_DIR%backend\venv" (
    echo [Info] Creating Python virtual environment...
    cd /d "%ROOT_DIR%backend"
    python -m venv venv
    echo [Done] venv created
)

if not exist "%ROOT_DIR%frontend\node_modules" (
    echo [Info] Installing frontend dependencies...
    cd /d "%ROOT_DIR%frontend"
    call npm install
    echo [Done] Frontend dependencies installed
)

echo.
echo [Start] Starting backend service...
start "Backend - FastAPI" cmd /k "cd /d "%ROOT_DIR%backend" && call venv\Scripts\activate.bat && pip install -r requirements.txt -q && echo. && echo [Backend] Starting server... && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo [Wait] Waiting for backend to start...
timeout /t 5 /nobreak >nul

echo.
echo [Start] Starting frontend service...
start "Frontend - React" cmd /k "cd /d "%ROOT_DIR%frontend" && echo [Frontend] Starting server... && npm run dev"

echo.
echo ========================================
echo    Services Started!
echo ========================================
echo.
echo    Backend API:  http://localhost:8000
echo    API Docs:     http://localhost:8000/docs
echo    Frontend:     http://localhost:5173
echo.
echo    Close windows to stop services
echo ========================================
echo.

timeout /t 8 /nobreak >nul
echo [Info] Opening browser...
start http://localhost:5173

echo.
echo Press any key to close this window...
pause >nul
