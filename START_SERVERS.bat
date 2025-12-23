@echo off
echo ==========================================
echo   AI Timetable Scheduler - Quick Start
echo ==========================================
echo.
echo IMPORTANT: This project has path length issues.
echo.
echo Recommended Solutions:
echo 1. Move this folder to C:\Projects\Timetable\
echo 2. OR enable long paths (requires admin)
echo.
echo Current Status:
echo - Backend: Most dependencies installed
echo - Frontend: Dependencies installed
echo - Missing: numpy, pandas, ortools (due to path length)
echo.
echo ==========================================
echo.
pause
echo.
echo Starting servers with current setup...
echo.
echo [1/2] Starting Backend...
start "AI Timetable Backend" cmd /k "cd ai-timetable-scheduler\backend && venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Starting Frontend...
start "AI Timetable Frontend" cmd /k "cd ai-timetable-scheduler\frontend && npm run dev"

echo.
echo ==========================================
echo   Servers Starting!
echo ==========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Login: admin / admin123
echo.
echo NOTE: Timetable generation may not work
echo       without ortools. Please follow
echo       SETUP_INSTRUCTIONS.md to fix.
echo ==========================================
pause
