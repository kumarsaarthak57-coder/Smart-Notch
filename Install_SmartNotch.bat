@echo off
@echo off
title Smart Notch - 1-Click Installer
color 0B
echo ==================================================
echo        SMART NOTCH - AUTOMATIC INSTALLER
echo ==================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed on this PC!
    echo Opening Microsoft Store to install Python...
    start ms-windows-store://pdp/?productid=9NCVDN91XZQP
    echo Please install Python first, then double-click this file again.
    pause
    exit /b
)

echo [1/3] Installing required Python libraries...
pip install --quiet --upgrade PyQt6 keyboard soundcard numpy

echo [2/3] Creating Desktop Shortcut with custom icon...
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\Smart Notch.lnk'); $s.TargetPath = 'pythonw.exe'; $s.Arguments = '\"%~dp0main.py\"'; $s.WorkingDirectory = '%~dp0'; $s.IconLocation = '%~dp0notch_icon.ico'; $s.Save()"

echo [3/3] Launching Smart Notch...
start "" pythonw.exe "%~dp0main.py"

echo.
echo [SUCCESS] Smart Notch is now running!
echo You can launch it anytime from the "Smart Notch" icon on your Desktop.
pause