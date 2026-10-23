# Project FRIDAY - PowerShell Launcher
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[FRIDAY] Virtual environment not found. Running setup..." -ForegroundColor Yellow
    cmd.exe /c install_friday.bat
}

Write-Host "[FRIDAY] Starting FRIDAY Personal Desktop Assistant..." -ForegroundColor Cyan
Start-Process -FilePath "$PSScriptRoot\.venv\Scripts\pythonw.exe" -ArgumentList "app\main.py $args"
