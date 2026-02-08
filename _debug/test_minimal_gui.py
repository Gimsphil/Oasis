#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
최소 GUI 테스트
"""

import sys
import os

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, "core"))
sys.path.insert(0, os.path.join(current_dir, "utils"))

try:
    from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QPushButton
    from PyQt6.QtCore import Qt
    
    app = QApplication(sys.argv)
    
    # 간단한 테스트 윈도우
    window = QMainWindow()
    window.setWindowTitle("✅ 이지맥스 GUI 테스트")
    window.resize(400, 300)
    window.move(500, 300)  # 화면 중앙에 배치
    
    widget = QWidget()
    layout = QVBoxLayout(widget)
    
    label1 = QLabel("✅ PyQt6이 정상 작동합니다!")
    label1.setStyleSheet("font-size: 14pt; font-weight: bold; color: green;")
    layout.addWidget(label1)
    
    label2 = QLabel("이 윈도우가 보인다면 GUI 환경이 정상입니다.")
    layout.addWidget(label2)
    
    btn = QPushButton("닫기")
    btn.clicked.connect(window.close)
    layout.addWidget(btn)
    
    window.setCentralWidget(widget)
    window.show()
    
    print("[OK] GUI Window is displayed!")
    sys.exit(app.exec())
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
