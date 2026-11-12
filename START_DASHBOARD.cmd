@echo off
setlocal
cd /d "%~dp0"
set "DASHBOARD_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%DASHBOARD_PYTHON%" set "DASHBOARD_PYTHON=python"
"%DASHBOARD_PYTHON%" -c "import openpyxl" >nul 2>nul
if errorlevel 1 (
  echo Installing the official Excel-file reader for data refresh...
  "%DASHBOARD_PYTHON%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Python 3.10 or later is required. See README.md for setup.
    pause
    exit /b 1
  )
)
echo Starting Malaysia GDP Nowcast. Keep this window open while using the dashboard.
echo Press Ctrl+C here to stop the local server.
"%DASHBOARD_PYTHON%" scripts\serve.py --open-browser
if errorlevel 1 pause
