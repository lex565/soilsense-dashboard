@echo off
title SoilSense Backend Server
color 0A
cls

echo.
echo =====================================================
echo   SOILSENSE BACKEND
echo =====================================================
echo.
echo Checking dependencies...
cd /d D:\soilsense\backend

if not exist venv (
    echo Installing Python dependencies (first run only)...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -q -r requirements.txt
    echo ✓ Dependencies installed
) else (
    call venv\Scripts\activate.bat
)

echo.
echo =====================================================
echo   STARTING SERVER
echo =====================================================
echo.
echo Server will start on: http://localhost:8000
echo API Docs:           http://localhost:8000/docs
echo.
echo Dashboard connected to: http://localhost:8000
echo.
echo Press Ctrl+C to stop server
echo.

python app.py

pause
