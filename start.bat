@echo off
title Heta AI - Local Backend Launcher
color 0b
echo.
echo  ============================================
echo       HETA AI  -  Starting Backend...
echo  ============================================
echo.
echo Please ensure you have GEMINI_API_KEY set in backend/.env
echo.

:: ── Step 1: Start Backend ──
echo [1/1] Starting FastAPI Backend...
cd /d "%~dp0backend"
start "Heta Backend" cmd /k "call venv\Scripts\activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
cd /d "%~dp0"

echo.
echo  ============================================
echo         BACKEND SERVICE IS RUNNING!
echo  ============================================
echo.
echo   API endpoint :  http://localhost:8000
echo   API Docs     :  http://localhost:8000/docs
echo.
echo   Connect the Flutter App to http://10.0.2.2:8000 for Android Emulator
echo   or your machine's IP for a physical device.
echo.
echo   Close the terminal window to stop.
echo.
pause
