#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 런처 스크립트
"""
import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("🚀 OASIS Application Launcher")
print("=" * 60)
print()

# 옵션 1: GUI 모드 (pythonw.exe)
print("Running main.py in GUI mode...")
result = subprocess.run([sys.executable, "main.py"], capture_output=True, text=True)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print("\nReturn Code:", result.returncode)
