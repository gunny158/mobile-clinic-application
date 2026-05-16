@echo off
setlocal
cd /d "%~dp0"

echo ==============================================
echo   BPK1 Mobile Clinic  ^|  Build Executable
echo ==============================================
echo.

:: ── Check Python ──────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo         Download Python 3.11+ from https://www.python.org/downloads/
    echo         Make sure to tick "Add Python to PATH" during install.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo Found: %%v

:: ── Install / upgrade PyInstaller ─────────────────────────────────────────────
echo.
echo [1/3] Installing PyInstaller and dependencies...
pip install --upgrade pyinstaller
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed. See error above.
    pause & exit /b 1
)

:: ── Build ─────────────────────────────────────────────────────────────────────
echo.
echo [2/3] Building executable (this may take a few minutes)...
python -m PyInstaller mobile_clinic.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. See output above.
    pause & exit /b 1
)

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo [3/3] Done!
echo.
echo ==============================================
echo   OUTPUT FOLDER:
echo   dist\BPK1_MobileClinic\
echo.
echo   Copy that entire folder to any Windows PC.
echo   Run:  BPK1_MobileClinic.exe
echo   No Python needed on the target machine.
echo ==============================================
echo.
pause
