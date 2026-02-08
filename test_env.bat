@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo Testing Python Environment
echo ========================================

echo.
echo [1] Python Version:
".venv\Scripts\python.exe" --version

echo.
echo [2] Testing simple print:
".venv\Scripts\python.exe" -c "print('Hello from Python!')"

echo.
echo [3] Testing main.py import:
".venv\Scripts\python.exe" -c "import sys; sys.path.insert(0, '.'); sys.path.insert(0, 'core'); sys.path.insert(0, 'utils'); from PyQt6.QtWidgets import QApplication; print('PyQt6 OK'); import app_style; print('app_style OK')"

echo.
echo [4] Running main.py:
".venv\Scripts\python.exe" main.py

echo.
echo ========================================
echo Test Complete
echo ========================================
pause
