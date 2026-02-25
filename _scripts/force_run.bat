@echo off
set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..") do set PROJECT_DIR=%%~fI
cd /d "%PROJECT_DIR%"
echo [FORCE RUN] Trying base Python 3.14...
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" "main.py"
echo [FORCE RUN] Exit Code: %ERRORLEVEL%
pause
