@echo off
"C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe" -c "with open(r'd:\오아시스\SANCHUL_Sheet_1\main.py', encoding='utf-8') as f: lines=f.readlines(); [print(f'{i+1:3d}: {lines[i]}', end='') for i in range(135, min(145, len(lines)))]"
pause
