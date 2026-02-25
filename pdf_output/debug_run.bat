@echo off
chcp 65001 >nul
echo =============================================
echo  PDF 산출 모듈 독립 실행 (Debug Mode)
echo =============================================
echo.

cd /d "%~dp0\.."
python pdf_output\debug_run.py

echo.
echo 종료하려면 아무 키나 누르세요...
pause >nul
