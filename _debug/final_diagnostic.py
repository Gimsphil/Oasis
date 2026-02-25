#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
이지맥스 최종 진단 - 모든 에러 로그에 저장
"""

import sys
import os
import traceback

# 로그 파일 경로
log_file = r"d:\이지맥스\OutputDetail_Standalone\error_report.txt"

# 로그 함수
def save_log(msg):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

# 기존 로그 삭제
with open(log_file, "w", encoding="utf-8") as f:
    f.write("="*70 + "\n")
    f.write("이지맥스 최종 진단 리포트\n")
    f.write("="*70 + "\n\n")

save_log(f"시작 시간: {__import__('datetime').datetime.now()}")
save_log(f"Python: {sys.version}")
save_log(f"실행 경로: {os.getcwd()}\n")

# Step 1: 디렉토리 확인
save_log("[STEP 1] 디렉토리 확인")
current_dir = os.path.dirname(os.path.abspath(__file__))
save_log(f"  현재 디렉토리: {current_dir}")
save_log(f"  main.py 존재: {os.path.exists(os.path.join(current_dir, 'main.py'))}")
save_log(f"  output_detail_tab.py 존재: {os.path.exists(os.path.join(current_dir, 'output_detail_tab.py'))}")
save_log(f"  lighting_power_manager.py 존재: {os.path.exists(os.path.join(current_dir, 'lighting_power_manager.py'))}")
save_log(f"  app_style.py 존재: {os.path.exists(os.path.join(current_dir, 'app_style.py'))}\n")

# Step 2: sys.path 설정
save_log("[STEP 2] sys.path 설정")
module_paths = [
    current_dir,
    os.path.join(current_dir, "core"),
    os.path.join(current_dir, "utils")
]

for path in module_paths:
    if path not in sys.path:
        sys.path.insert(0, path)
    save_log(f"  {path}")
save_log()

# Step 3: PyQt6 테스트
save_log("[STEP 3] PyQt6 임포트 테스트")
try:
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from PyQt6.QtCore import Qt
    save_log("  ✅ PyQt6 임포트 성공\n")
except Exception as e:
    save_log(f"  ❌ PyQt6 임포트 실패: {e}")
    save_log(f"\n{traceback.format_exc()}\n")
    sys.exit(1)

# Step 4: app_style 테스트
save_log("[STEP 4] app_style 임포트 테스트")
try:
    from app_style import register_fonts, get_main_stylesheet
    save_log("  ✅ app_style 임포트 성공\n")
except Exception as e:
    save_log(f"  ❌ app_style 임포트 실패: {e}")
    save_log(f"\n{traceback.format_exc()}\n")
    sys.exit(1)

# Step 5: lighting_power_manager 테스트 (중요!)
save_log("[STEP 5] lighting_power_manager 임포트 테스트")
try:
    from lighting_power_manager import LightingPowerManager
    save_log("  ✅ lighting_power_manager 임포트 성공\n")
except Exception as e:
    save_log(f"  ❌ lighting_power_manager 임포트 실패: {e}")
    save_log(f"\n{traceback.format_exc()}\n")
    sys.exit(1)

# Step 6: output_detail_tab 테스트
save_log("[STEP 6] output_detail_tab 임포트 테스트")
try:
    from output_detail_tab import OutputDetailTab
    save_log("  ✅ output_detail_tab 임포트 성공\n")
except Exception as e:
    save_log(f"  ❌ output_detail_tab 임포트 실패: {e}")
    save_log(f"\n{traceback.format_exc()}\n")
    sys.exit(1)

# Step 7: QApplication 테스트
save_log("[STEP 7] QApplication 생성 테스트")
try:
    app = QApplication(sys.argv)
    save_log("  ✅ QApplication 생성 성공\n")
except Exception as e:
    save_log(f"  ❌ QApplication 생성 실패: {e}")
    save_log(f"\n{traceback.format_exc()}\n")
    sys.exit(1)

# Step 8: QMainWindow 테스트
save_log("[STEP 8] QMainWindow 생성 테스트")
try:
    window = QMainWindow()
    window.setWindowTitle("테스트")
    window.resize(1200, 800)
    save_log("  ✅ QMainWindow 생성 성공\n")
except Exception as e:
    save_log(f"  ❌ QMainWindow 생성 실패: {e}")
    save_log(f"\n{traceback.format_exc()}\n")
    sys.exit(1)

# Step 9: OutputDetailTab 생성 테스트
save_log("[STEP 9] OutputDetailTab 생성 테스트")
try:
    tab_manager = OutputDetailTab(window)
    save_log("  ✅ OutputDetailTab 생성 성공\n")
except Exception as e:
    save_log(f"  ❌ OutputDetailTab 생성 실패: {e}")
    save_log(f"\n{traceback.format_exc()}\n")
    sys.exit(1)

# Step 10: create_tab 호출 테스트
save_log("[STEP 10] create_tab() 호출 테스트")
try:
    central_widget = tab_manager.create_tab()
    if central_widget is None:
        save_log("  ❌ create_tab()이 None을 반환함\n")
        sys.exit(1)
    save_log("  ✅ create_tab() 호출 성공\n")
except Exception as e:
    save_log(f"  ❌ create_tab() 호출 실패: {e}")
    save_log(f"\n{traceback.format_exc()}\n")
    sys.exit(1)

# Step 11: 스타일 적용 테스트
save_log("[STEP 11] 스타일 적용 테스트")
try:
    font_name = register_fonts(current_dir)
    app.setStyleSheet(get_main_stylesheet(font_name))
    save_log(f"  ✅ 스타일 적용 성공 (폰트: {font_name})\n")
except Exception as e:
    save_log(f"  ⚠️  스타일 적용 실패 (계속 진행): {e}\n")

# Step 12: 윈도우 표시 테스트
save_log("[STEP 12] 윈도우 표시 테스트")
try:
    window.setCentralWidget(central_widget)
    window.show()
    window.raise_()
    window.activateWindow()
    save_log("  ✅ 윈도우 표시 성공\n")
except Exception as e:
    save_log(f"  ❌ 윈도우 표시 실패: {e}")
    save_log(f"\n{traceback.format_exc()}\n")
    sys.exit(1)

# 최종 성공 메시지
save_log("="*70)
save_log("✅ 모든 진단 성공!")
save_log("="*70)
save_log(f"\n로그 파일: {log_file}\n")
save_log(f"종료 시간: {__import__('datetime').datetime.now()}")

print("\n\n✅ 진단 완료!")
print(f"자세한 내용은 다음 파일을 참고하세요: {log_file}")
print("\n이제 GUI를 시작합니다...\n")

sys.exit(app.exec())
