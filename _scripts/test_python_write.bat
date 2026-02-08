@echo off
echo Testing Python Write capability...
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" -c "print('Testing stdout'); open('python_working.txt', 'w').write('Python is alive')"
if exist python_working.txt (
    echo [SUCCESS] Python created the file.
    type python_working.txt
) else (
    echo [FAILURE] Python failed to create the file.
)
pause
