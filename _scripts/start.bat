@echo off
REM 이지맥스 세부산출조서 자동화 시스템 - GUI 직접 실행
REM pythonw.exe 사용 (콘솔 없이 GUI만 표시)

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..") do set PROJECT_DIR=%%~fI
cd /d "%PROJECT_DIR%"

REM 설정
set APP_PYTHON=C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\pythonw.exe
set MAIN_SCRIPT=main.py

if not exist "%APP_PYTHON%" (
    set APP_PYTHON=pythonw.exe
)

if not exist "%APP_PYTHON%" (
    set APP_PYTHON=C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe
)

if not exist "%APP_PYTHON%" (
    echo [ERROR] Python 실행 파일을 찾을 수 없습니다.
    pause
    exit /b 1
)

start "" "%APP_PYTHON%" "%MAIN_SCRIPT%"

exit /b 0
