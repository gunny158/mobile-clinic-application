@echo off
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo [ERROR] App crashed. Run install.bat first if you haven't already.
    pause
)
