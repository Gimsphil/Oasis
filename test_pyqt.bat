@echo off
cd /d "%~dp0"
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" -c "import PyQt6; print('PyQt6 import success')" > pyqt_test.txt 2>&1
type pyqt_test.txt
pause
