# -*- coding: utf-8 -*-
"""
PDF 산출 모듈 독립 실행 (디버그용)
다른 모듈에 영향을 주지 않고 단독으로 테스트할 수 있습니다.

실행 방법:
  1) python pdf_output/debug_run.py
  2) pdf_output/debug_run.bat 더블클릭
"""
import sys
import os

# 프로젝트 루트를 sys.path에 추가 (모듈 임포트 경로 해결)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtGui import QIcon

def main():
    print("=" * 50)
    print(" PDF 산출 모듈 독립 실행 (Debug Mode)")
    print("=" * 50)

    app = QApplication(sys.argv)

    # 폰트/스타일 적용 시도 (실패해도 무관)
    try:
        from core.app_style import register_fonts, get_main_stylesheet
        font_name = register_fonts(project_root)
        app.setStyleSheet(get_main_stylesheet(font_name))
        print(f"[OK] 스타일 적용 완료: {font_name}")
    except Exception as e:
        print(f"[WARN] 스타일 로드 실패 (무시됨): {e}")

    # PDF 산출 팝업 실행
    from pdf_output.pdf_popup import PDFOutputPopup

    dialog = PDFOutputPopup()
    dialog.setWindowTitle("PDF 산출 시스템 [DEBUG MODE]")
    dialog.resize(1400, 900)

    # 아이콘 설정 시도
    icon_path = os.path.join(project_root, "assets", "icons", "오아시스_로고01.png")
    if os.path.exists(icon_path):
        dialog.setWindowIcon(QIcon(icon_path))

    dialog.show()

    print("[OK] PDF 산출 팝업이 실행되었습니다.")
    print("     Ctrl+O: PDF 열기")
    print("     Ctrl+W: 닫기")
    print()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
