@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo ====== OASIS Debug Console ======
echo.

REM Install PyQt6 if not already installed
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo PyQt6 not found. Installing...
    "C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" -m pip install PyQt6 --user
)

echo Running main.py...
echo.
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" main.py

echo.
echo Exit code: %ERRORLEVEL%
echo Press any key to exit...
pause > nul
