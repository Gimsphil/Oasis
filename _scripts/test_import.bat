@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe test_imports_only.py > import_test.log 2>&1
type import_test.log
pause
