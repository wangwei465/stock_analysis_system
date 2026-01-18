@echo off
chcp 65001 >nul 2>nul
title Backend - FastAPI

echo ========================================
echo    Backend Service - FastAPI
echo ========================================
echo.

set "ROOT_DIR=%~dp0"

cd /d "%ROOT_DIR%backend"

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [Warning] venv not found, using global Python
)

echo [Info] Starting backend service...
echo [Info] API Docs: http://localhost:8000/docs
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
