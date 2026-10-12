@echo off
title FORAGRO - Backend FastAPI
cd /d "%~dp0backend"
echo ========================================================
echo   Iniciando Backend FORAGRO - Inge. Agro IA (FastAPI)
echo   Puerto: http://localhost:8000
echo   Docs:   http://localhost:8000/docs
echo ========================================================
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
