# -*- coding: utf-8 -*-
import sys
import os

# 로그 파일에 기록
with open("test_run.log", "w", encoding="utf-8") as f:
    f.write("Script started\n")

try:
    with open("test_run.log", "a", encoding="utf-8") as f:
        f.write(f"Python: {sys.version}\n")
        f.write(f"CWD: {os.getcwd()}\n")

    # PyQt6 테스트
    from PyQt6.QtWidgets import QApplication, QLabel
    with open("test_run.log", "a", encoding="utf-8") as f:
        f.write("PyQt6 imported OK\n")

    app = QApplication(sys.argv)
    with open("test_run.log", "a", encoding="utf-8") as f:
        f.write("QApplication created OK\n")

    label = QLabel("테스트 성공!")
    label.setFixedSize(300, 100)
    label.show()

    with open("test_run.log", "a", encoding="utf-8") as f:
        f.write("Window shown OK\n")

    sys.exit(app.exec())

except Exception as e:
    import traceback
    with open("test_run.log", "a", encoding="utf-8") as f:
        f.write(f"ERROR: {e}\n")
        f.write(traceback.format_exc())
    print(f"ERROR: {e}")
