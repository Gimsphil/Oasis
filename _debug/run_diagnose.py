import sys
import os
import time

log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagnose_log.txt")

def log(msg):
    with open(log_file, "a", encoding="utf-8") as f:
        timestamp = time.strftime("%H:%M:%S")
        f.write(f"[{timestamp}] {msg}\n")

# 로그 파일 초기화
with open(log_file, "w", encoding="utf-8") as f:
    f.write("=== Diagnostic Start ===\n")

log("1. Python Basic: OK")
log(f"   Interpreter: {sys.executable}")
log(f"   CWD: {os.getcwd()}")

try:
    log("2. Attempting to import PyQt6...")
    from PyQt6.QtWidgets import QApplication
    log("   PyQt6 Import: SUCCESS")
except Exception as e:
    log(f"   PyQt6 Import: FAILED - {e}")
    sys.exit(1)

try:
    log("3. Attempting to import lighting_power_manager...")
    import lighting_power_manager
    log("   lighting_power_manager Import: SUCCESS")
except Exception as e:
    log(f"   lighting_power_manager Import: FAILED - {e}")
    import traceback
    log(traceback.format_exc())

try:
    log("4. Attempting to import output_detail_tab...")
    import output_detail_tab
    log("   output_detail_tab Import: SUCCESS")
except Exception as e:
    log(f"   output_detail_tab Import: FAILED - {e}")
    import traceback
    log(traceback.format_exc())

log("=== Diagnostic End ===")
