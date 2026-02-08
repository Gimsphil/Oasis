@echo off
chcp 65001
echo [BAT] Starting Python execution... > bat_log.txt
"d:\이지맥스\OutputDetail_Standalone\.venv\Scripts\python.exe" "d:\이지맥스\OutputDetail_Standalone\main.py" >> bat_log.txt 2>&1
echo [BAT] Exit Code: %ERRORLEVEL% >> bat_log.txt
