import sys
import os
import traceback

log_file = "diagnosis_log.txt"

def log(msg):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

try:
    if os.path.exists(log_file):
        os.remove(log_file)
    log("Diagnosis Started")
    
    # Check paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    log(f"Current Dir: {current_dir}")
    
    # Try importing main
    log("Importing main...")
    import main
    log("Main imported successfully")
    
    # Run main logic manually to catch errors
    log("Initializing Application...")
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    log("QApplication created")
    
    # Import core components
    log("Importing OutputDetailTab...")
    from output_detail_tab import OutputDetailTab
    log("OutputDetailTab imported")
    
    log("Creating MainWindow...")
    window = main.StandaloneMainWindow()
    log("MainWindow created")
    
    log("Showing Window...")
    window.show()
    log("Window shown")
    
    # Don't run exec loop, just check if we got this far
    log("Diagnosis Setup Complete. (Skipping app.exec for diagnosis)")
    
except Exception:
    log("CRITICAL FAILURE:")
    log(traceback.format_exc())
