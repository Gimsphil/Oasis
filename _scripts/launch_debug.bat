@echo off
set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..") do set PROJECT_DIR=%%~fI
cd /d "%PROJECT_DIR%"
echo ==================================================
echo [DEBUG] Launching main.py using Python314
echo ==================================================
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" "main.py"
echo.
echo ==================================================
echo [DEBUG] Execution finished.
echo If you see this, Python exited. Check above for errors.
echo Return Code: %ERRORLEVEL%
echo ==================================================
pause
