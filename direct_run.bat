@echo off
cd /d "%~dp0"
echo === Direct Python Execution ===
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" main.py
echo.
echo Exit Code: %ERRORLEVEL%
pause
