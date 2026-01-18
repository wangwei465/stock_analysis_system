@echo off
chcp 65001 >nul 2>nul
title Backend Test (Simple)

echo ========================================
echo    Backend Simple Test
echo ========================================
echo.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%backend"

echo [1] Activating venv...
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo [OK] venv activated
) else (
    echo [ERROR] venv not found
    pause
    exit /b 1
)

echo.
echo [2] Testing basic imports (no network)...
python -c "print('Testing FastAPI...'); from fastapi import FastAPI; print('[OK] FastAPI')"
if %errorlevel% neq 0 goto :error

python -c "print('Testing SQLModel...'); from sqlmodel import SQLModel; print('[OK] SQLModel')"
if %errorlevel% neq 0 goto :error

python -c "print('Testing pandas...'); import pandas; print('[OK] pandas')"
if %errorlevel% neq 0 goto :error

python -c "print('Testing numpy...'); import numpy; print('[OK] numpy')"
if %errorlevel% neq 0 goto :error

echo.
echo [3] Testing AKShare import (may be slow)...
python -c "print('Testing AKShare (this may take a moment)...'); import akshare; print('[OK] AKShare')"
if %errorlevel% neq 0 (
    echo [WARNING] AKShare import failed, but server may still work
)

echo.
echo [4] Testing app config...
python -c "from app.config import settings; print(f'[OK] Config loaded: {settings.app_name}')"
if %errorlevel% neq 0 goto :error

echo.
echo [5] Starting server (press Ctrl+C to stop)...
echo.
echo    API: http://localhost:8000
echo    Docs: http://localhost:8000/docs
echo.

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

pause
exit /b 0

:error
echo.
echo [ERROR] Test failed! Check the error message above.
pause
exit /b 1
