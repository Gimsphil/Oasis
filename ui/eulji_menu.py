# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt

class EuljiCategoryMenu(QWidget):
    """을지 화면 상단의 카테고리 단축키 메뉴 위젯"""
    def __init__(self, parent_tab=None):
        super().__init__()
        self.parent_tab = parent_tab
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("eulji_category_menu")
        self.setFixedHeight(26)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        eulji_categories = [
            "전등/전열", "통신/약전", "자탐/소방", "전력간선", 
            "수변전설비", "TRAY", "Raceway", "자동화설비"
        ]

        style = """
            QPushButton {
                background-color: #f1f1f1;
                border: 1px solid #707070;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-bottom: 2px solid #606060;
                border-right: 2px solid #606060;
                border-radius: 2px;
                padding: 1px 10px;
                min-height: 20px;
                max-height: 22px;
                font-family: '새굴림';
                font-size: 10pt;
                color: #333;
            }
            QPushButton:hover {
                background-color: #e1e1e1;
            }
            QPushButton:pressed {
                background-color: #d1d1d1;
                border-top: 2px solid #606060;
                border-left: 2px solid #606060;
                border-bottom: 1px solid #ffffff;
                border-right: 1px solid #ffffff;
            }
        """

        for cat in eulji_categories:
            btn = QPushButton(cat)
            btn.setStyleSheet(style)
            # [FIX] 버튼 클릭 이벤트 연결
            btn.clicked.connect(lambda checked, c=cat: self._on_button_clicked(c))
            layout.addWidget(btn)
        
        layout.addStretch()

    def _on_button_clicked(self, category):
        """버튼 클릭 시 부모 탭에 알림"""
        if self.parent_tab and hasattr(self.parent_tab, "_on_eulji_category_clicked"):
            self.parent_tab._on_eulji_category_clicked(category)
