@echo off
REM Check if PyQt6 is installed
cd /d "%~dp0"
echo Checking Python and PyQt6 installation...
echo.
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" -c "import sys; print(f'Python: {sys.executable}'); import PyQt6; print(f'PyQt6 found at: {PyQt6.__file__}')" 2>&1 | tee install_check.log
echo.
pause
