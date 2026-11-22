@echo off
setlocal
cd /d "%~dp0"
py -3.13 -m pip install -r requirements.txt || exit /b 1
py -3.13 make_icon.py || exit /b 1
py -3.13 -m PyInstaller --noconfirm --clean --onefile --windowed --name AIRBridge --icon "assets\airbridge.ico" --add-data "web;web" --add-data "assets;assets" --collect-all customtkinter --collect-all qrcode --hidden-import PIL._tkinter_finder --hidden-import winotify app.py || exit /b 1
echo.
echo EXE ready: "%CD%\dist\AIRBridge.exe"
pause
