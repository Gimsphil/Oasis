@echo off
REM Install required packages using pip
cd /d "%~dp0"
echo Installing Python packages...
echo.

"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" -m pip install PyQt6 pandas numpy openpyxl xlrd python-dateutil pytz --user

echo.
echo Installation complete!
echo.
pause
