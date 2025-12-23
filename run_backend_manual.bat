@echo off
echo ==========================================
echo   Simple Backend Launcher
echo ==========================================

REM 1. Fix Long Path Issues (Mount Z: Drive)
if exist "Z:\" subst Z: /d
subst Z: "%~dp0ai-timetable-scheduler\backend"

REM 2. Run the Server
echo Starting Backend Server...
REM Crucial change: Switch to Z: drive so uvicorn finds 'app'
cd /d Z:\
cmd /k "set PYTHONPATH=Z:\pkg && Z:\venv_short\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
