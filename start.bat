@echo off
REM 이지맥스 세부산출조서 자동화 시스템 - GUI 직접 실행

setlocal enabledelayedexpansion

cd /d "%~dp0"

REM 설정
set MAIN_SCRIPT=main.py
set PYTHON_PATH=C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\pythonw.exe

REM Python 경로 확인
if not exist "%PYTHON_PATH%" (
    echo Python이 설치되지 않았습니다.
    echo Please install Python from https://www.python.org
    pause
    exit /b 1
)

REM 애플리케이션 실행 (GUI 모드, 콘솔 없음)
start "OASIS" "%PYTHON_PATH%" "%MAIN_SCRIPT%"

exit /b 0

exit /b 0
