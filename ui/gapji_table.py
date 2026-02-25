# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt
from utils.column_settings import setup_common_table, COMMON_COLUMNS, COLUMN_WIDTHS

class GapjiTableWidget(QTableWidget):
    """산출총괄표(갑지) 전용 테이블 위젯"""
    def __init__(self, parent_tab=None):
        super().__init__()
        self.parent_tab = parent_tab
        self._init_ui()

    def _init_ui(self):
        setup_common_table(self, COMMON_COLUMNS, COLUMN_WIDTHS)
        if self.parent_tab:
            self.cellChanged.connect(self.parent_tab.on_gapji_cell_changed)
            self.itemChanged.connect(self.parent_tab._on_gapji_item_changed)
            self.cellClicked.connect(self.parent_tab.on_gapji_cell_clicked)
        
        # 기본 안내 행 설정
        self.blockSignals(True)
        # 1행: 공 사 명
        item_seq0 = QTableWidgetItem("Project")
        item_seq0.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(0, self.parent_tab.GONGJONG_NUM_COL if self.parent_tab else 2, item_seq0)

        item_gubun0 = QTableWidgetItem("공 사 명")
        item_gubun0.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(0, self.parent_tab.GUBUN_COL if self.parent_tab else 1, item_gubun0)
        
        self.setItem(0, self.parent_tab.GONGJONG_COL if self.parent_tab else 3, QTableWidgetItem("새로운 공사명을 등록하세요."))
        
        # 2행: 공 통
        item_gubun1 = QTableWidgetItem("공  통")
        item_gubun1.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(1, self.parent_tab.GUBUN_COL if self.parent_tab else 1, item_gubun1)
        
        self.blockSignals(False)

    def set_reorder_button(self, row, col, button_widget):
        """특정 셀에 번호정리 버튼 배치"""
        self.setCellWidget(row, col, button_widget)
