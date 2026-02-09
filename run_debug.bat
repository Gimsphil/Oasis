@echo off
REM Run main.py with console output
cd /d "%~dp0"
echo Starting application...
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" main.py
echo Exit code: %ERRORLEVEL%
pause
