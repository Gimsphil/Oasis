# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class GongjongListPanel(QFrame):
    """우측 공종 리스트 패널 위젯"""
    def __init__(self, parent_tab=None):
        super().__init__()
        self.parent_tab = parent_tab
        self._init_ui()

    def _init_ui(self):
        self.setMinimumWidth(200)
        self.setStyleSheet("background-color: #f8f9fa;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 헤더
        header = QLabel("공종 리스트")
        header.setFixedHeight(30)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            background-color: #e1e1e1;
            border: 1px solid #707070;
            border-top: 1px solid #ffffff;
            border-left: 1px solid #ffffff;
            border-bottom: 2px solid #606060;
            border-right: 2px solid #606060;
            font-weight: normal;
            color: #333;
            font-family: '새굴림';
            font-size: 11pt;
        """)
        layout.addWidget(header)

        # 리스트 위젯
        self.list_widget = QListWidget()
        
        # 폰트 설정
        font = QFont("새굴림", 11)
        font.setStretch(100)
        self.list_widget.setFont(font)
        
        self.list_widget.setStyleSheet("""
            QListWidget { border: none; background-color: white; font-family: '새굴림'; font-size: 11pt; }
            QListWidget::item { height: 22px; padding-left: 0px; border-bottom: 1px solid #f1f3f5; }
            QListWidget::item:hover { background-color: #f1f3f5; }
            QListWidget::item:selected { background-color: #e1e1e1; color: black; border: 1px solid #707070; }
        """)
        
        if self.parent_tab:
            self.list_widget.itemClicked.connect(self.parent_tab._on_gongjong_item_clicked)
        
        layout.addWidget(self.list_widget)

    def add_item(self, text, user_role_data=None):
        """항목 추가"""
        item = QListWidgetItem(text)
        if user_role_data:
            item.setData(Qt.ItemDataRole.UserRole, user_role_data)
        self.list_widget.addItem(item)

    def clear(self):
        """모든 항목 제거"""
        self.list_widget.clear()
