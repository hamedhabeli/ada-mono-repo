@echo off
title ADA Cloud Multi-Agent System - Startup Script

echo =======================================================
echo     Welcome to ADA Cloud Multi-Agent System (R&D)
echo =======================================================
echo.

:: Step 1: Install Python dependencies if not fully installed
echo [1/3] Preparing Python Backend...
cd backend
python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo.
    echo [WARNING] Some python dependencies failed to install. Continuing anyway...
    echo.
)
cd ..

:: Step 2: Install Node.js dependencies if not fully installed
echo [2/3] Preparing React Frontend...
cd frontend
call npm install
if %ERRORLEVEL% neq 0 (
    echo.
    echo [WARNING] npm install failed. Continuing anyway...
    echo.
)
cd ..

:: Step 3: Launch servers in separate terminal windows
echo [3/3] Launching local servers...

echo.
echo Starting FastAPI Backend (Port 8000)...
start "FastAPI Backend" cmd /k "cd backend && python -m uvicorn main:app --reload"

echo Starting Vite React Frontend (Port 5173)...
start "Vite React Frontend" cmd /k "cd frontend && npm run dev"

echo Waiting for servers to initialize...
timeout /t 5 >nul

echo.
echo Opening browser at http://localhost:5173 ...
start http://localhost:5173

echo.
echo =======================================================
echo  ADA is now running! 
echo  - Close the opened command prompt windows to stop the servers.
echo =======================================================
echo.
pause
