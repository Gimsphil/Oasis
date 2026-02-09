@echo off
set PYTHON_PATH=C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe
echo Starting debug run... > debug_output_v2.txt
echo Python Path: %PYTHON_PATH% >> debug_output_v2.txt
if not exist "%PYTHON_PATH%" echo PYTHON NOT FOUND >> debug_output_v2.txt

"%PYTHON_PATH%" -m pip list >> debug_output_v2.txt 2>&1
echo --- Running main.py --- >> debug_output_v2.txt
"%PYTHON_PATH%" main.py >> debug_output_v2.txt 2>&1
echo Exit Code: %ERRORLEVEL% >> debug_output_v2.txt
echo Debug run finished. >> debug_output_v2.txt
