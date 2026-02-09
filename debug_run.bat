@echo off
set PYTHON_PATH=C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe
echo Running Main Script... > debug_output.txt
"%PYTHON_PATH%" main.py >> debug_output.txt 2>&1
echo Done. >> debug_output.txt
