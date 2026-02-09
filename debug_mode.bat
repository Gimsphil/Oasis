@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo.
echo ===== OASIS Application Debug Mode =====
echo.
echo Python: C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe
echo Script: main.py
echo Working Dir: !CD!
echo Time: %date% %time%
echo.

REM Run with explicit error handling
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" -u main.py 2>&1

echo.
echo ===== Execution Completed =====
echo Exit Code: %ERRORLEVEL%
echo Time: %date% %time%
echo.
echo Press any key to exit...
pause > nul
