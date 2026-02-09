@echo off
cd /d "%~dp0"
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" main.py > app_output.txt 2>&1
echo Debug output saved to app_output.txt
pause
