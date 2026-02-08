@echo off
REM 이지맥스 세부산출조서 자동화 시스템 - GUI 직접 실행
REM pythonw.exe 사용 (콘솔 없이 GUI만 표시)

setlocal enabledelayedexpansion

cd /d "%~dp0"

REM 설정
set VENV_PYTHON=.venv\Scripts\pythonw.exe
set MAIN_SCRIPT=main.py
set PROJECT_DIR=%cd%

REM pythonw.exe가 없으면 python.exe 사용
if not exist "%VENV_PYTHON%" (
    set VENV_PYTHON=.venv\Scripts\python.exe
)

REM 가상환경 확인
if not exist "%VENV_PYTHON%" (
    REM 시스템 Python 사용
    start "" pythonw.exe "%MAIN_SCRIPT%"
) else (
    REM 가상환경 Python 사용
    start "" "%VENV_PYTHON%" "%MAIN_SCRIPT%"
)

exit /b 0
