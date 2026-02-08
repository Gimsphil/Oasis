import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from output_detail_tab import OutputDetailTab 
from app_style import register_fonts, get_main_stylesheet

def main():
    print("Starting Application...")
    app = QApplication(sys.argv)
    
    # 폰트 및 스타일
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        sys.path.insert(0, os.path.join(current_dir, "core"))
        sys.path.insert(0, os.path.join(current_dir, "utils"))

    font = register_fonts(current_dir)
    app.setStyleSheet(get_main_stylesheet(font))

    window = QMainWindow()
    window.setWindowTitle("산출내역 - 독립 실행")
    window.resize(1200, 800)
    
    tab_manager = OutputDetailTab(window)
    central_widget = tab_manager.create_tab()
    window.setCentralWidget(central_widget)
    
    window.show()
    print("Window Shown")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
