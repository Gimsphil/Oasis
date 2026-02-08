import sys
import os
import datetime

log_file = "startup_debug.log"

def log(msg):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{msg}\n")
    print(msg)

try:
    log(f"--- check_env.py started at {datetime.datetime.now()} ---")
    log(f"Python: {sys.executable}")
    log(f"CWD: {os.getcwd()}")
    log(f"sys.path: {sys.path}")

    try:
        import PyQt6
        log(f"PyQt6 imported: {PyQt6.__file__}")
        
        from PyQt6 import QtWidgets
        log("PyQt6.QtWidgets imported")
        
        app = QtWidgets.QApplication(sys.argv)
        log("QApplication created")
        
    except ImportError as e:
        log(f"ImportError: {e}")
    except Exception as e:
        log(f"Error initializing PyQt: {e}")

except Exception as e:
    print(f"Fatal error: {e}")
