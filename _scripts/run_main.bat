@echo off
REM 이지맥스 세부산출조서 자동화 시스템 - main.py 직접 실행 래퍼
REM 이 파일은 main.py를 pythonw.exe로 실행하여 PowerShell 콘솔 없이 GUI만 표시합니다.

chcp 65001 > nul
setlocal enabledelayedexpansion

cd /d "%~dp0"

set PYTHONW_EXE=.venv\Scripts\pythonw.exe
set MAIN_SCRIPT=main.py

if not exist "%PYTHONW_EXE%" (
    echo [ERROR] pythonw.exe를 찾을 수 없습니다.
    echo Location: %PYTHONW_EXE%
    
    REM pythonw.exe가 없으면 일반 python.exe 사용
    set PYTHONW_EXE=.venv\Scripts\python.exe
    echo [INFO] Falling back to python.exe: !PYTHONW_EXE!
)

REM GUI 애플리케이션 실행 (콘솔 없이)
start "" "!PYTHONW_EXE!" "!MAIN_SCRIPT!"

exit /b 0
