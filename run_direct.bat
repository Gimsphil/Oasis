@echo off
REM Simple direct execution with console visible
cd /d "%~dp0"
echo [Starting OASIS Application]
echo.
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" main.py 2>&1 | tee app_run_output.txt
echo.
echo [Exit code: %ERRORLEVEL%]
pause
