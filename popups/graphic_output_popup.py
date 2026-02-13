# -*- coding: utf-8 -*-
"""
PDF 산출 팝업 - 리디렉트 모듈
==========================
실제 구현은 pdf_output/ 폴더로 이동되었습니다.
이 파일은 기존 import 경로를 유지하기 위한 호환성 레이어입니다.

실제 코드: pdf_output/pdf_popup.py
독립 디버그: pdf_output/debug_run.py (또는 debug_run.bat)
"""

# pdf_output 모듈에서 PDFOutputPopup을 import하여 재export
# output_detail_tab.py의 _on_toolbar_clicked에서
# "popups.graphic_output_popup" → "PDFOutputPopup" 을 찾으므로
# 이 re-export만으로 기존 호출이 그대로 동작합니다.
from pdf_output.pdf_popup import PDFOutputPopup

__all__ = ["PDFOutputPopup"]
