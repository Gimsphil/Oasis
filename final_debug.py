#!/usr/bin/env python3
import sys
import traceback
import os

output_file = r"d:\오아시스\SANCHUL_Sheet_1\final_debug_output.txt"

try:
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("START\n")
        f.flush()
        
        f.write(f"Python: {sys.executable}\n")
        f.write(f"Version: {sys.version}\n")
        f.write(f"Args: {sys.argv}\n")
        f.write(f"CWD: {os.getcwd()}\n")
        f.flush()
        
        import subprocess
        f.write("Imported subprocess\n")
        f.flush()
        
        f.write("About to run main.py...\n")
        f.flush()
        
        result = subprocess.run([sys.executable, "main.py"],
                              capture_output=True, text=True,
                              cwd=r"d:\오아시스\SANCHUL_Sheet_1",
                              timeout=30)  # increased timeout
        
        f.write(f"DONE - Return: {result.returncode}\n")
        f.write(f"OUT ({len(result.stdout)} chars): {result.stdout[:1000] if result.stdout else 'NONE'}\n")
        f.write(f"ERR ({len(result.stderr)} chars): {result.stderr[:1000] if result.stderr else 'NONE'}\n")
        f.flush()
        
except subprocess.TimeoutExpired as e:
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"\nTIMEOUT EXPIRED AFTER {e.timeout}s\n")
except Exception as e:
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"EXCEPTION: {e}\n")
        f.write(traceback.format_exc())
