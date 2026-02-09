@echo off
cd /d "%~dp0"
echo === OASIS Application - Debug Mode ===
echo.
echo Python: C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe
echo Script: main.py
echo CWD: %CD%
echo.
echo Running...
echo.
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" main.py
echo.
echo Done! Press any key to exit...
pause > nul
