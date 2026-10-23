@echo off
setlocal
title Project FRIDAY - Installation & Setup Wizard

cd /d "%~dp0"
echo =======================================================
echo          PROJECT FRIDAY - ENVIRONMENT SETUP
echo =======================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH. Please install Python 3.11 - 3.13 from python.org.
    pause
    exit /b 1
)

echo [1/3] Creating virtual environment (.venv)...
if not exist ".venv" (
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo [2/3] Upgrading pip and installing required dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation encountered errors.
    pause
    exit /b 1
)

echo [3/3] Initializing default configuration and directories...
if not exist ".env" (
    copy .env.example .env >nul
    echo Created default .env from template.
)

if not exist "data" mkdir data
if not exist "logs" mkdir logs

echo.
echo =======================================================
echo     FRIDAY SETUP COMPLETE!
echo     Launch FRIDAY anytime by double-clicking run_friday.bat
echo =======================================================
echo.
pause
