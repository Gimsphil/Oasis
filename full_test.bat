@echo off
cd /d "%~dp0"
echo Testing PyQt6 import...
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" -c "import PyQt6; print('PyQt6 SUCCESS')" 2>&1 | tee pyqt_test.txt
echo.
echo Testing app startup...
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" main.py 2>&1 | tee app_run_test.txt
echo.
echo Files generated. Press any key to view them...
pause > nul
type pyqt_test.txt
echo.
type app_run_test.txt
pause
