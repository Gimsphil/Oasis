"""
산출판 시스템 (Output Board System)
산출내역의 항목을 시각적으로 정리하고 관리하는 판서 시스템

기능:
- 항목별 그룹화 및 정렬
- 시각적 산출판 형식 출력
- 인쇄용 레이아웃 지원

참고: egManual.pdf p165-171
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QComboBox,
    QLabel,
    QLineEdit,
    QGroupBox,
    QSplitter,
    QHeaderView,
    QAbstractItemView,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

# 그리드 스타일 설정을 위한 공통 모듈 임포트
from utils.column_settings import (
    setup_common_table,
    DEFAULT_ROWS,
    DEFAULT_ROW_HEIGHT,
    HEADER_FONT_SIZE,
)


class OutputBoardPopup(QDialog):
    """
    산출판 팝업
    산출내역서를 시각적 판서 형식으로 변환하여 표시
    """

    closed = pyqtSignal(dict)  # 선택된 데이터 반환

    def __init__(self, parent=None, output_data: list = None):
        super().__init__(parent)
        self.setWindowTitle("산출판 시스템")
        self.setMinimumSize(1000, 700)
        self.output_data = output_data or []

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 상단 툴바
        toolbar = self.create_toolbar()
        layout.addLayout(toolbar)

        # 메인 스플리터 (좌측: 산출판, 우측: 상세내역)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 좌측: 산출판 테이블
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 산출판 테이블 - 그리드 스타일 적용
        self.board_table = QTableWidget()
        board_columns = ["순번", "산출항목", "규격", "수량", "비고"]
        board_widths = {
            "순번": 40,
            "산출항목": 200,
            "규격": 120,
            "수량": 60,
            "비고": 100,
        }
        setup_common_table(self.board_table, board_columns, board_widths)

        left_layout.addWidget(QLabel("<b>산출판</b>"))
        left_layout.addWidget(self.board_table)
        splitter.addWidget(left_frame)

        # 우측: 상세내역 테이블 - 그리드 스타일 적용
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.detail_table = QTableWidget()
        detail_columns = ["항목", "규격", "수량", "단위"]
        detail_widths = {"항목": 150, "규격": 100, "수량": 60, "단위": 50}
        setup_common_table(self.detail_table, detail_columns, detail_widths)
        self.detail_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        right_layout.addWidget(QLabel("<b>상세내역</b>"))
        right_layout.addWidget(self.detail_table)
        splitter.addWidget(right_frame)

        layout.addWidget(splitter)

        # 하단 버튼
        buttons = self.create_buttons()
        layout.addLayout(buttons)

    def create_toolbar(self) -> QHBoxLayout:
        """툴바 생성"""
        layout = QHBoxLayout()

        # 정렬 방식
        layout.addWidget(QLabel("정렬:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["공종별", "규격별", "수량순", "추가순"])
        self.sort_combo.currentIndexChanged.connect(self.sort_data)
        layout.addWidget(self.sort_combo)

        # 검색
        layout.addWidget(QLabel("검색:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("산출항목 검색...")
        self.search_edit.textChanged.connect(self.filter_data)
        layout.addWidget(self.search_edit)

        layout.addStretch()

        return layout

    def create_buttons(self) -> QHBoxLayout:
        """버튼 생성"""
        layout = QHBoxLayout()

        self.print_btn = QPushButton("인쇄")
        self.print_btn.clicked.connect(self.print_board)
        layout.addWidget(self.print_btn)

        self.export_btn = QPushButton("내보내기")
        self.export_btn.clicked.connect(self.export_board)
        layout.addWidget(self.export_btn)

        layout.addStretch()

        self.close_btn = QPushButton("닫기")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)

        return layout

    def load_data(self):
        """데이터 로드"""
        self.board_table.setRowCount(0)

        for i, item in enumerate(self.output_data):
            row = self.board_table.rowCount()
            self.board_table.insertRow(row)

            # 순번
            self.board_table.setItem(row, 0, QTableWidgetItem(str(i + 1)))

            # 산출항목
            name_item = QTableWidgetItem(item.get("name", ""))
            self.board_table.setItem(row, 1, name_item)

            # 규격
            spec_item = QTableWidgetItem(item.get("spec", ""))
            self.board_table.setItem(row, 2, spec_item)

            # 수량
            qty_item = QTableWidgetItem(str(item.get("quantity", "")))
            self.board_table.setItem(row, 3, qty_item)

            # 비고
            note_item = QTableWidgetItem(item.get("note", ""))
            self.board_table.setItem(row, 4, note_item)

    def sort_data(self):
        """데이터 정렬"""
        # 정렬 로직 구현
        pass

    def filter_data(self, text: str):
        """데이터 필터링"""
        for row in range(self.board_table.rowCount()):
            item = self.board_table.item(row, 1)
            if item:
                match = text.lower() in item.text().lower()
                self.board_table.setRowHidden(row, not match)

    def print_board(self):
        """산출판 인쇄"""
        # 인쇄 로직 구현
        pass

    def export_board(self):
        """산출판 내보내기"""
        # 내보내기 로직 구현
        pass

    def get_selected_item(self) -> Optional[dict]:
        """선택된 항목 반환"""
        row = self.board_table.currentRow()
        if row >= 0 and row < len(self.output_data):
            return self.output_data[row]
        return None


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 테스트 데이터
    test_data = [
        {"name": "전등기", "spec": "LED 40W", "quantity": 50, "note": ""},
        {"name": "콘센트", "spec": "일반용", "quantity": 120, "note": ""},
        {"name": "스위치", "spec": "1회로", "quantity": 30, "note": ""},
    ]

    dialog = OutputBoardPopup(output_data=test_data)
    dialog.exec()
