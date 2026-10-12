@echo off
title FORAGRO - Frontend Kiosco y Dashboard
cd /d "%~dp0"
echo ========================================================
echo   Iniciando Servidor Web Estático FORAGRO
echo   Kiosco POP: http://localhost:8080/kiosk/
echo   Dashboard:  http://localhost:8080/dashboard/
echo ========================================================
start http://localhost:8080/kiosk/
python -m http.server 8080
pause
