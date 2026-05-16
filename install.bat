@echo off
setlocal
cd /d "%~dp0"

echo ==============================================
echo   BPK1 Mobile Clinic  ^|  Python Setup
echo ==============================================
echo   Use this if you want to run from source
echo   (Python must be installed on this machine)
echo ==============================================
echo.

:: ── Check Python ──────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo.
    echo   1. Download Python 3.11+ from:
    echo      https://www.python.org/downloads/
    echo.
    echo   2. During installation, tick:
    echo      [x] Add Python to PATH
    echo.
    echo   3. Re-run this script after installing Python.
    echo.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo Found: %%v

:: ── Install packages ──────────────────────────────────────────────────────────
echo.
echo Installing packages (internet required)...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed.
    echo         Check your internet connection and try again.
    pause & exit /b 1
)

echo.
echo ==============================================
echo   Setup complete!
echo   Double-click run.bat to start the app.
echo ==============================================
echo.
pause
