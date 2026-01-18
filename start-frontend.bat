@echo off
chcp 65001 >nul 2>nul
title Frontend - React

echo ========================================
echo    Frontend Service - React
echo ========================================
echo.

set "ROOT_DIR=%~dp0"

cd /d "%ROOT_DIR%frontend"

echo [Info] Starting frontend service...
echo [Info] URL: http://localhost:5173
echo.

npm run dev

pause
