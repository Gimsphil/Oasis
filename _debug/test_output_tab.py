import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from output_detail_tab import OutputDetailTab
import traceback

def main():
    print("Start OutputDetailTab Test")
    try:
        app = QApplication(sys.argv)
        window = QMainWindow()
        window.resize(1200, 800)
        
        print("Creating OutputDetailTab instance...")
        tab = OutputDetailTab(window)
        
        print("Creating tab widget...")
        widget = tab.create_tab()
        
        window.setCentralWidget(widget)
        window.show()
        print("Window shown. Entering event loop...")
        
        sys.exit(app.exec())
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    main()
