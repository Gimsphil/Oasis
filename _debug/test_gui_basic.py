import sys
import os

try:
    log_file = "gui_test_log.txt"
    with open(log_file, "w") as f:
        f.write("Starting GUI Test\n")

    from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow

    app = QApplication(sys.argv)
    window = QMainWindow()
    label = QLabel("Hello World", window)
    window.setCentralWidget(label)
    window.show()

    with open(log_file, "a") as f:
        f.write("Window Shown\n")

    # 자동 종료 (테스트용)
    from PyQt6.QtCore import QTimer
    QTimer.singleShot(1000, app.quit)
    
    app.exec()
    
    with open(log_file, "a") as f:
        f.write("App Executed Successfully\n")

except Exception as e:
    with open("gui_test_error.txt", "w") as f:
        import traceback
        f.write(traceback.format_exc())
