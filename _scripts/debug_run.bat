@echo off
echo Starting Python...
"d:\이지맥스\OutputDetail_Standalone\.venv\Scripts\python.exe" "d:\이지맥스\OutputDetail_Standalone\main.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%
) else (
    echo.
    echo Application exited successfull.
)
pause
