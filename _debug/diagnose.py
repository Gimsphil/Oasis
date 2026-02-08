#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
이지맥스 시스템 진단 스크립트
각 모듈을 단계별로 로드하여 문제를 찾습니다.
"""

import sys
import os
import traceback

# 로그 파일 생성
log_file = os.path.join(os.path.dirname(__file__), "diagnose.log")
log_f = open(log_file, "w", encoding="utf-8")

def log_print(msg):
    """콘솔과 파일에 동시 출력"""
    print(msg)
    log_f.write(msg + "\n")
    log_f.flush()

log_print("\n" + "="*70)
log_print("이지맥스 시스템 진단")
log_print("="*70 + "\n")

current_dir = os.path.dirname(os.path.abspath(__file__))
log_print(f"[STEP 1] 현재 디렉토리 확인")
log_print(f"  경로: {current_dir}")
log_print(f"  파일 존재: {os.path.isdir(current_dir)}")
log_print(f"  로그 파일: {log_file}")
log_print()

# sys.path 설정
print(f"[STEP 2] sys.path 설정")
module_paths = [
    current_dir,
    os.path.join(current_dir, "core"),
    os.path.join(current_dir, "utils")
]

for path in module_paths:
    if path not in sys.path:
        sys.path.insert(0, path)
    print(f"  추가: {path}")
print()

# PyQt6 테스트
print(f"[STEP 3] PyQt6 임포트")
try:
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from PyQt6.QtCore import Qt
    print(f"  ✅ PyQt6 성공")
except Exception as e:
    print(f"  ❌ PyQt6 실패: {e}")
    traceback.print_exc()
    sys.exit(1)
print()

# app_style 테스트
print(f"[STEP 4] app_style 임포트")
try:
    from app_style import register_fonts, get_main_stylesheet
    print(f"  ✅ app_style 성공")
except Exception as e:
    print(f"  ❌ app_style 실패: {e}")
    traceback.print_exc()
    sys.exit(1)
print()

# output_detail_tab 테스트
print(f"[STEP 5] output_detail_tab 임포트")
try:
    from output_detail_tab import OutputDetailTab
    print(f"  ✅ output_detail_tab 성공")
except Exception as e:
    print(f"  ❌ output_detail_tab 실패: {e}")
    traceback.print_exc()
    sys.exit(1)
print()

# lighting_power_manager 테스트
print(f"[STEP 6] lighting_power_manager 임포트")
try:
    from lighting_power_manager import LightingPowerManager
    print(f"  ✅ lighting_power_manager 성공")
except Exception as e:
    print(f"  ❌ lighting_power_manager 실패: {e}")
    traceback.print_exc()
    sys.exit(1)
print()

# GUI 생성 테스트
print(f"[STEP 7] QApplication 생성")
try:
    app = QApplication(sys.argv)
    print(f"  ✅ QApplication 생성 성공")
except Exception as e:
    print(f"  ❌ QApplication 생성 실패: {e}")
    traceback.print_exc()
    sys.exit(1)
print()

# 윈도우 생성 테스트
print(f"[STEP 8] QMainWindow 생성")
try:
    window = QMainWindow()
    window.setWindowTitle("산출내역 - 독립 실행")
    window.resize(1200, 800)
    print(f"  ✅ QMainWindow 생성 성공")
except Exception as e:
    print(f"  ❌ QMainWindow 생성 실패: {e}")
    traceback.print_exc()
    sys.exit(1)
print()

# 탭 생성 테스트
print(f"[STEP 9] OutputDetailTab 생성")
try:
    tab_manager = OutputDetailTab(window)
    print(f"  ✅ OutputDetailTab 생성 성공")
except Exception as e:
    print(f"  ❌ OutputDetailTab 생성 실패: {e}")
    traceback.print_exc()
    sys.exit(1)
print()

# create_tab 테스트
print(f"[STEP 10] create_tab() 호출")
try:
    central_widget = tab_manager.create_tab()
    if central_widget is None:
        print(f"  ❌ create_tab() 실패: None 반환")
        sys.exit(1)
    print(f"  ✅ create_tab() 성공")
except Exception as e:
    print(f"  ❌ create_tab() 실패: {e}")
    traceback.print_exc()
    sys.exit(1)
print()

# 스타일 적용 테스트
print(f"[STEP 11] 스타일 적용")
try:
    font_name = register_fonts(current_dir)
    app.setStyleSheet(get_main_stylesheet(font_name))
    print(f"  ✅ 스타일 적용 성공 (폰트: {font_name})")
except Exception as e:
    print(f"  ⚠️  스타일 적용 실패 (계속 진행): {e}")
print()

# 윈도우 설정 및 표시
print(f"[STEP 12] 윈도우 설정 및 표시")
try:
    window.setCentralWidget(central_widget)
    window.show()
    window.raise_()
    window.activateWindow()
    print(f"  ✅ 윈도우 표시 성공")
except Exception as e:
    print(f"  ❌ 윈도우 표시 실패: {e}")
    traceback.print_exc()
    sys.exit(1)
print()

print("="*70)
print("✅ 모든 진단 성공!")
print("="*70)
print("\n[INFO] GUI 애플리케이션을 시작합니다...")
print("[INFO] 윈도우를 종료하려면 윈도우 닫기 버튼을 클릭하세요.\n")

sys.exit(app.exec())
