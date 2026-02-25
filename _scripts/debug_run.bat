@echo off
set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..") do set PROJECT_DIR=%%~fI
cd /d "%PROJECT_DIR%"
echo Starting Python...
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" "main.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%
) else (
    echo.
    echo Application exited successfull.
)
pause
