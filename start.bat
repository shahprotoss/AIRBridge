@echo off
cd /d "%~dp0"
py -3.13 -m pip install -r requirements.txt
py -3.13 make_icon.py
py -3.13 app.py
