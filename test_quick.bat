@echo off
REM Simple diagnostic test for the application
REM Using absolute Python path

cd /d "%~dp0"
setlocal enabledelayedexpansion

echo Testing Python environment...
echo.

"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" test_quick.py

echo.
echo Test complete. Press any key to continue...
pause > nul
