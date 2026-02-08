#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI 디버깅 스크립트
"""

import sys
import os
import traceback

# 로그 파일에 출력
log_file = os.path.join(os.path.dirname(__file__), "gui_debug.log")
log_f = open(log_file, "w", encoding="utf-8")

def log(msg):
    """콘솔과 파일에 모두 출력"""
    print(msg)
    log_f.write(msg + "\n")
    log_f.flush()

log("=" * 80)
log("GUI DEBUG TEST")
log("=" * 80)

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
module_paths = [
    current_dir,
    os.path.join(current_dir, "core"),
    os.path.join(current_dir, "utils")
]

for path in module_paths:
    if path not in sys.path:
        sys.path.insert(0, path)

log(f"\n[DEBUG] Current directory: {current_dir}")
log(f"[DEBUG] Log file: {log_file}")
log(f"[DEBUG] sys.path: {sys.path[:3]}")

# PyQt6 임포트 테스트
log("\n[STEP 1] Testing PyQt6 import...")
try:
    from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout
    from PyQt6.QtCore import Qt
    log("[OK] PyQt6 imported successfully")
except Exception as e:
    log(f"[ERROR] PyQt6 import failed: {e}")
    log_f.close()
    sys.exit(1)

# 모듈 임포트 테스트
log("\n[STEP 2] Testing module imports...")
try:
    from output_detail_tab import OutputDetailTab
    log("[OK] output_detail_tab imported successfully")
except Exception as e:
    log(f"[ERROR] output_detail_tab import failed: {e}")
    log(traceback.format_exc())
    log_f.close()
    sys.exit(1)

# GUI 생성 테스트
log("\n[STEP 3] Creating GUI...")
try:
    app = QApplication(sys.argv)
    log("[OK] QApplication created")
    
    window = QMainWindow()
    window.setWindowTitle("Test Window")
    window.resize(1200, 800)
    log("[OK] QMainWindow created")
    
    # 간단한 테스트 위젯
    log("\n[STEP 3-1] Creating test widget...")
    test_widget = QWidget()
    test_layout = QVBoxLayout(test_widget)
    test_label = QLabel("✅ Test GUI is working!")
    test_layout.addWidget(test_label)
    
    window.setCentralWidget(test_widget)
    log("[OK] Test widget created and set")
    
    window.show()
    log("[OK] Window shown")
    
    # OutputDetailTab 생성 테스트
    log("\n[STEP 4] Creating OutputDetailTab...")
    tab = OutputDetailTab(window)
    log("[OK] OutputDetailTab instance created")
    
    log("\n[STEP 5] Calling create_tab()...")
    central_widget = tab.create_tab()
    log(f"[OK] create_tab() returned: {central_widget}")
    log(f"[DEBUG] Widget type: {type(central_widget)}")
    
    if central_widget is None:
        log("[ERROR] create_tab() returned None!")
    else:
        log("[OK] Widget is valid, replacing...")
        window.setCentralWidget(central_widget)
        log("[OK] Widget set as central widget")
    
    window.show()
    log("[OK] Window displayed")
    
    log("\n[SUCCESS] All tests passed!")
    log("[INFO] Window should be visible on screen now")
    log("[INFO] Close the window to exit")
    
    log_f.close()
    sys.exit(app.exec())
    
except Exception as e:
    log(f"\n[ERROR] GUI creation failed: {e}")
    log(traceback.format_exc())
    log_f.close()
    sys.exit(1)
