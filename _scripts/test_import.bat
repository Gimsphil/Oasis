@echo off
set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..") do set PROJECT_DIR=%%~fI
cd /d "%PROJECT_DIR%"
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" "_debug\test_imports_only.py" > "%SCRIPT_DIR%import_test.log" 2>&1
type "%SCRIPT_DIR%import_test.log"
pause
