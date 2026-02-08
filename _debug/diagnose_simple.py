#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
이지맥스 진단 - 최소 버전
"""

import sys
import os

log_file = os.path.join(os.path.dirname(__file__), "diagnose.log")
log_f = open(log_file, "w", encoding="utf-8")

def log_p(msg):
    print(msg)
    log_f.write(msg + "\n")
    log_f.flush()

try:
    log_p("[STEP 1] 현재 디렉토리")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    log_p(f"  {current_dir}\n")
    
    log_p("[STEP 2] sys.path 추가")
    sys.path.insert(0, current_dir)
    sys.path.insert(0, os.path.join(current_dir, "core"))
    sys.path.insert(0, os.path.join(current_dir, "utils"))
    log_p("  OK\n")
    
    log_p("[STEP 3] PyQt6 임포트")
    from PyQt6.QtWidgets import QApplication, QMainWindow
    log_p("  OK\n")
    
    log_p("[STEP 4] app_style 임포트")
    from app_style import register_fonts, get_main_stylesheet
    log_p("  OK\n")
    
    log_p("[STEP 5] output_detail_tab 임포트")
    from output_detail_tab import OutputDetailTab
    log_p("  OK\n")
    
    log_p("[STEP 6] QApplication 생성")
    app = QApplication(sys.argv)
    log_p("  OK\n")
    
    log_p("[STEP 7] QMainWindow 생성")
    window = QMainWindow()
    window.setWindowTitle("산출내역 - 독립 실행")
    window.resize(1200, 800)
    log_p("  OK\n")
    
    log_p("[STEP 8] OutputDetailTab 생성")
    tab_manager = OutputDetailTab(window)
    log_p("  OK\n")
    
    log_p("[STEP 9] create_tab() 호출")
    central_widget = tab_manager.create_tab()
    if central_widget is None:
        log_p("  ERROR: None 반환\n")
        log_f.close()
        sys.exit(1)
    log_p("  OK\n")
    
    log_p("[STEP 10] 스타일 적용")
    font_name = register_fonts(current_dir)
    app.setStyleSheet(get_main_stylesheet(font_name))
    log_p(f"  OK (폰트: {font_name})\n")
    
    log_p("[STEP 11] 윈도우 표시")
    window.setCentralWidget(central_widget)
    window.show()
    window.raise_()
    window.activateWindow()
    log_p("  OK\n")
    
    log_p("="*50)
    log_p("ALL TESTS PASSED!")
    log_p("="*50)
    log_f.close()
    
    sys.exit(app.exec())

except Exception as e:
    log_p(f"\nERROR: {e}\n")
    import traceback
    log_p(traceback.format_exc())
    log_f.close()
    sys.exit(1)
