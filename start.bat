@echo off
REM Skrypt startowy środowiska deweloperskiego Django TiMo dla Windows
REM Uruchamia serwer deweloperski na porcie 8001

cd %~dp0
call venv\Scripts\activate
python manage.py runserver 0.0.0.0:8001