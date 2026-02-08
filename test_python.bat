@echo off
cd /d d:\오아시스\SANCHUL_Sheet_1
echo Testing Python environment...
python -c "print('Hello from Python'); import os; print('CWD:', os.getcwd()); open('python_test.txt', 'w').write('Test successful')"
echo Done.
pause
