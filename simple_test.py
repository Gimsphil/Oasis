#!/usr/bin/env python3
import sys
import os

# 인코딩 수정
if sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("Test: 인코딩이 수정되었습니다")
print("Python version:", sys.version)
print("CWD:", os.getcwd())

os.chdir(r"d:\오아시스\SANCHUL_Sheet_1")
print("New CWD:", os.getcwd())

try:
    print("Trying to import PyQt6...")
    from PyQt6.QtWidgets import QApplication
    print("✅ PyQt6 imported successfully!")
except Exception as e:
    print(f"❌ PyQt6 import failed: {e}")
    sys.exit(1)

print("\nTrying to exec main.py...")
with open("main.py") as f:
    code = f.read()
    exec(code)
