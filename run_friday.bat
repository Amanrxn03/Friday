@echo off
setlocal
title Project FRIDAY - AI Desktop Companion

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [FRIDAY] Virtual environment not found. Running initial setup...
    call install_friday.bat
    if errorlevel 1 (
        echo [FRIDAY] Installation failed.
        pause
        exit /b 1
    )
)

echo [FRIDAY] Starting FRIDAY Personal Desktop Assistant...
start "" ".venv\Scripts\pythonw.exe" "app\main.py" %*
if errorlevel 1 (
    echo [FRIDAY] Failed to launch with pythonw. Falling back to python console...
    ".venv\Scripts\python.exe" "app\main.py" %*
)
