@echo off
REM 이지맥스 세부산출조서 자동화 시스템 - main.py 직접 실행 래퍼
REM 이 파일은 main.py를 pythonw.exe로 실행하여 PowerShell 콘솔 없이 GUI만 표시합니다.

chcp 65001 > nul
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..") do set PROJECT_DIR=%%~fI
cd /d "%PROJECT_DIR%"

set PYTHONW_EXE=C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\pythonw.exe
set MAIN_SCRIPT=main.py

if not exist "%PYTHONW_EXE%" (
    set PYTHONW_EXE=pythonw.exe
)

if not exist "%PYTHONW_EXE%" (
    set PYTHONW_EXE=C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe
)

if not exist "%PYTHONW_EXE%" (
    echo [ERROR] Python 실행 파일을 찾을 수 없습니다.
    echo Tried: C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\pythonw.exe
    echo Tried: pythonw.exe
    echo Tried: C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe
    pause
    exit /b 1
)

REM GUI 애플리케이션 실행 (콘솔 없이)
start "" "!PYTHONW_EXE!" "!MAIN_SCRIPT!"

exit /b 0
