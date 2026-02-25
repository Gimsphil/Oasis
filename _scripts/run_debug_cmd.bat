@echo off
chcp 65001
set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..") do set PROJECT_DIR=%%~fI
cd /d "%PROJECT_DIR%"
echo [BAT] Starting Python execution... > "%SCRIPT_DIR%bat_log.txt"
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" "main.py" >> "%SCRIPT_DIR%bat_log.txt" 2>&1
echo [BAT] Exit Code: %ERRORLEVEL% >> "%SCRIPT_DIR%bat_log.txt"
