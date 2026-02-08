import sys
import traceback
import os

log_file = "import_test_log.txt"

def log(msg):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

# 초기화
with open(log_file, "w", encoding="utf-8") as f:
    f.write("Test Started\n")

try:
    log("1. Importing PyQt6.QtWidgets...")
    from PyQt6.QtWidgets import QApplication, QWidget
    log("   Success.")
except:
    log("   Failed: " + traceback.format_exc())

try:
    log("2. Importing lighting_power_manager...")
    import lighting_power_manager
    log("   Success.")
except:
    log("   Failed: " + traceback.format_exc())

try:
    log("3. Importing output_detail_tab...")
    import output_detail_tab
    log("   Success.")
except:
    log("   Failed: " + traceback.format_exc())

try:
    log("4. Importing main...")
    import main
    log("   Success.")
except:
    log("   Failed: " + traceback.format_exc())

log("Test Finished.")
