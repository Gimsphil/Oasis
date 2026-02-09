#!/usr/bin/env python3
"""
Direct launcher using Python subprocess
"""
import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Write output to file for debugging
with open("app_launcher_debug.txt", "w", encoding="utf-8") as log:
    log.write(f"Python: {sys.executable}\n")
    log.write(f"CWD: {os.getcwd()}\n")
    log.write(f"Python version: {sys.version}\n\n")
    
    log.write("Attempting to import PyQt6...\n")
    try:
        import PyQt6
        log.write(f"PyQt6 found: {PyQt6.__file__}\n\n")
    except ImportError as e:
        log.write(f"PyQt6 NOT found: {e}\n\n")
    
    log.write("Running main.py...\n")
    log.write("="*60 + "\n\n")
    
    result = subprocess.run([sys.executable, "main.py"], capture_output=True, text=True)
    log.write("STDOUT:\n")
    log.write(result.stdout)
    log.write("\n\nSTDERR:\n")
    log.write(result.stderr)
    log.write(f"\n\nReturn code: {result.returncode}\n")

print("Debug output written to app_launcher_debug.txt")
