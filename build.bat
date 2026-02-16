@echo off
title Build Pinch
cd /d "%~dp0"

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Building Pinch.exe with PyInstaller...
pyinstaller --onefile --noconsole --name "Pinch" ^
    --paths "src" ^
    --collect-data certifi ^
    --hidden-import pinch ^
    --hidden-import pinch.app ^
    --hidden-import pinch.config ^
    --hidden-import pinch.auth ^
    --hidden-import pinch.usage_api ^
    --hidden-import pinch.usage_monitor ^
    --hidden-import pinch.shared_state ^
    --hidden-import pinch.taskbar_overlay ^
    --hidden-import pinch.tray_icon ^
    --hidden-import pinch.popup_view ^
    --hidden-import pinch.autostart ^
    --hidden-import pinch.theme ^
    --hidden-import pinch.utils ^
    --hidden-import pinch.settings ^
    --hidden-import pinch.settings_ui ^
    --hidden-import pinch.setup_wizard ^
    --hidden-import pystray._win32 ^
    src/run_pinch.py

echo.
echo Build complete! .exe is at: dist\Pinch.exe
pause
