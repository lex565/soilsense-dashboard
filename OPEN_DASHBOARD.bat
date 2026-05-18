@echo off
title SoilSense Dashboard
color 0A
echo.
echo =========================================
echo   SOILSENSE DASHBOARD
echo =========================================
echo.
echo Opening dashboard in browser...
echo.
echo Make sure backend is running!
echo (Run RUN_BACKEND.bat first)
echo.
timeout /t 2

start "" "D:\soilsense\frontend\index.html"

pause
