@echo off
chcp 65001 >nul 2>nul
title Stop Services

echo ========================================
echo    Stock Analysis System - Stop
echo ========================================
echo.

echo [Info] Stopping backend service (uvicorn)...
taskkill /f /im uvicorn.exe >nul 2>nul

echo [Info] Stopping frontend service (node)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173"') do taskkill /f /pid %%a >nul 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000"') do taskkill /f /pid %%a >nul 2>nul

echo [Info] Closing service windows...
taskkill /f /fi "WINDOWTITLE eq Backend - FastAPI*" >nul 2>nul
taskkill /f /fi "WINDOWTITLE eq Frontend - React*" >nul 2>nul

echo.
echo [Done] All services stopped
echo.
pause
