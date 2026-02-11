"""
설계변경 (Design Change)
설계 변경에 따른 산출내역 일괄 수정 시스템

기능:
- 항목별 수량/규격 변경
- 변경 이력 관리
- 원본 대비 변경내역 비교

참고: egManual.pdf p354-358
"""

from typing import Optional, List, Dict
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
    QTabWidget,
    QTextEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor


class DesignChangePopup(QDialog):
    """
    설계변경 팝업
    설계 변경 시 산출내역의 수량/규격/품명을 일괄 수정하고 이력을 관리
    """

    change_applied = pyqtSignal(dict)  # 변경 적용 결과

    def __init__(self, parent=None, current_data: list = None):
        super().__init__(parent)
        self.setWindowTitle("설계변경")
        self.setMinimumSize(1100, 750)
        self.current_data = current_data or []
        self.original_data = []  # 변경 전 원본 데이터
        self.change_history = []  # 변경 이력

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 탭 구성
        tabs = QTabWidget()

        # 탭 1: 변경 대상 선택
        tabs.addTab(self.create_select_tab(), "변경대상")

        # 탭 2: 변경 내용 입력
        tabs.addTab(self.create_change_tab(), "변경입력")

        # 탭 3: 변경 이력
        tabs.addTab(self.create_history_tab(), "변경이력")

        layout.addWidget(tabs)

        # 하단 버튼
        buttons = self.create_buttons()
        layout.addLayout(buttons)

    def create_select_tab(self) -> QFrame:
        """변경 대상 선택 탭"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)

        # 필터 그룹
        filter_group = QGroupBox("필터 조건")
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("공종:"))
        self.gongjong_combo = QComboBox()
        self.gongjong_combo.addItems(["전체"] + [f"공종 {i}" for i in range(1, 10)])
        filter_layout.addWidget(self.gongjong_combo)

        filter_layout.addWidget(QLabel("변경유형:"))
        self.change_type_combo = QComboBox()
        self.change_type_combo.addItems(["전체", "수량변경", "규격변경", "품명변경"])
        filter_layout.addWidget(self.change_type_combo)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("검색어 입력...")
        filter_layout.addWidget(self.search_edit)

        self.filter_btn = QPushButton("적용")
        self.filter_btn.clicked.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_btn)

        filter_layout.addStretch()
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # 변경 대상 테이블
        self.select_table = QTableWidget()
        self.select_table.setColumnCount(7)
        self.select_table.setHorizontalHeaderLabels(
            ["선택", "순번", "산출항목", "규격", "수량", "단위", "공종"]
        )
        self.select_table.horizontalHeader().setStretchLastSection(True)
        self.select_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.select_table.setAlternatingRowColors(True)
        self.select_table.itemChanged.connect(self.on_selection_changed)

        layout.addWidget(QLabel("<b>변경 대상 목록</b>"))
        layout.addWidget(self.select_table)

        # 선택 정보
        self.selection_info = QLabel("선택 항목: 0개")
        layout.addWidget(self.selection_info)

        return frame

    def create_change_tab(self) -> QFrame:
        """변경 내용 입력 탭"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)

        # 변경 유형 선택
        type_group = QGroupBox("변경 유형")
        type_layout = QHBoxLayout()

        self.change_type_radio1 = QPushButton("수량 일괄 변경")
        self.change_type_radio1.setCheckable(True)
        self.change_type_radio1.setChecked(True)
        self.change_type_radio1.clicked.connect(
            lambda: self.set_change_mode("quantity")
        )
        type_layout.addWidget(self.change_type_radio1)

        self.change_type_radio2 = QPushButton("규격 일괄 변경")
        self.change_type_radio2.setCheckable(True)
        self.change_type_radio2.clicked.connect(lambda: self.set_change_mode("spec"))
        type_layout.addWidget(self.change_type_radio2)

        self.change_type_radio3 = QPushButton("수량 증감률 적용")
        self.change_type_radio3.setCheckable(True)
        self.change_type_radio3.clicked.connect(lambda: self.set_change_mode("rate"))
        type_layout.addWidget(self.change_type_radio3)

        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # 변경 내용 입력
        input_group = QGroupBox("변경 내용")
        input_layout = QGridLayout()

        # 수량 변경 모드
        self.qty_label = QLabel("변경 수량:")
        input_layout.addWidget(self.qty_label, 0, 0)
        self.qty_input = QLineEdit()
        self.qty_input.setPlaceholderText("새 수량 입력...")
        input_layout.addWidget(self.qty_input, 0, 1)

        # 규격 변경 모드
        self.spec_label = QLabel("변경 규격:")
        self.spec_input = QComboBox()
        self.spec_input.addItems(["CVV 2.0mm", "CVV 3.5mm", "CVV 5.5mm", "VV 8.0mm"])
        input_layout.addWidget(self.spec_label, 1, 0)
        input_layout.addWidget(self.spec_input, 1, 1)

        # 증감률 모드
        self.rate_label = QLabel("증감률(%):")
        self.rate_input = QLineEdit()
        self.rate_input.setPlaceholderText("예: +10, -5, +20")
        input_layout.addWidget(self.rate_label, 2, 0)
        input_layout.addWidget(self.rate_input, 2, 1)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # 변경 사유
        reason_group = QGroupBox("변경 사유")
        reason_layout = QVBoxLayout()
        self.reason_edit = QTextEdit()
        self.reason_edit.setMaximumHeight(80)
        self.reason_edit.setPlaceholderText("변경 사유를 입력하세요...")
        reason_layout.addWidget(self.reason_edit)
        reason_group.setLayout(reason_layout)
        layout.addWidget(reason_group)

        # 미리보기
        preview_group = QGroupBox("변경 미리보기")
        preview_layout = QVBoxLayout()

        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(5)
        self.preview_table.setHorizontalHeaderLabels(
            ["산출항목", "현재수량", "변경후수량", "변경량", "변경율(%)"]
        )
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        preview_layout.addWidget(self.preview_table)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        return frame

    def create_history_tab(self) -> QFrame:
        """변경 이력 탭"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)

        # 이력 목록
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(
            ["순번", "변경일시", "변경유형", "대상항목수", "변경사유", "작성자"]
        )
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        layout.addWidget(QLabel("<b>변경 이력</b>"))
        layout.addWidget(self.history_table)

        # 상세 보기
        self.history_detail = QTextEdit()
        self.history_detail.setMaximumHeight(150)
        self.history_detail.setPlaceholderText("선택한 이력의 상세 내용...")
        layout.addWidget(QLabel("상세 내용:"))
        layout.addWidget(self.history_detail)

        return frame

    def create_buttons(self) -> QHBoxLayout:
        """버튼 생성"""
        layout = QHBoxLayout()

        self.apply_btn = QPushButton("변경 적용")
        self.apply_btn.clicked.connect(self.apply_change)
        layout.addWidget(self.apply_btn)

        self.preview_btn = QPushButton("미리보기")
        self.preview_btn.clicked.connect(self.preview_change)
        layout.addWidget(self.preview_btn)

        self.undo_btn = QPushButton("변경 취소")
        self.undo_btn.clicked.connect(self.undo_last_change)
        layout.addWidget(self.undo_btn)

        layout.addStretch()

        self.close_btn = QPushButton("닫기")
        self.close_btn.clicked.connect(self.reject)
        layout.addWidget(self.close_btn)

        return layout

    def set_change_mode(self, mode: str):
        """변경 모드 설정"""
        self.current_mode = mode

        # 라디오 버튼 상태 업데이트
        self.change_type_radio1.setChecked(mode == "quantity")
        self.change_type_radio2.setChecked(mode == "spec")
        self.change_type_radio3.setChecked(mode == "rate")

        # 입력 필드 표시/숨김
        self.qty_label.setVisible(mode == "quantity")
        self.qty_input.setVisible(mode == "quantity")
        self.spec_label.setVisible(mode == "spec")
        self.spec_input.setVisible(mode == "spec")
        self.rate_label.setVisible(mode == "rate")
        self.rate_input.setVisible(mode == "rate")

    def load_data(self):
        """데이터 로드"""
        self.original_data = [item.copy() for item in self.current_data]
        self.select_table.setRowCount(0)

        for i, item in enumerate(self.current_data):
            row = self.select_table.rowCount()
            self.select_table.insertRow(row)

            # 선택 체크박스
            checkbox = QTableWidgetItem()
            checkbox.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            checkbox.setCheckState(Qt.CheckState.Unchecked)
            self.select_table.setItem(row, 0, checkbox)

            # 순번
            self.select_table.setItem(row, 1, QTableWidgetItem(str(i + 1)))

            # 산출항목
            self.select_table.setItem(row, 2, QTableWidgetItem(item.get("name", "")))

            # 규격
            self.select_table.setItem(row, 3, QTableWidgetItem(item.get("spec", "")))

            # 수량
            self.select_table.setItem(
                row, 4, QTableWidgetItem(str(item.get("quantity", "")))
            )

            # 단위
            self.select_table.setItem(row, 5, QTableWidgetItem(item.get("unit", "")))

            # 공종
            self.select_table.setItem(
                row, 6, QTableWidgetItem(item.get("gongjong", ""))
            )

    def on_selection_changed(self, item):
        """선택 변경 시"""
        if item.column() == 0:  # 체크박스 열
            selected = self.get_selected_items()
            self.selection_info.setText(f"선택 항목: {len(selected)}개")

    def get_selected_items(self) -> List[dict]:
        """선택된 항목 반환"""
        selected = []
        for row in range(self.select_table.rowCount()):
            checkbox = self.select_table.item(row, 0)
            if checkbox and checkbox.checkState() == Qt.CheckState.Checked:
                if row < len(self.current_data):
                    selected.append(self.current_data[row])
        return selected

    def apply_filter(self):
        """필터 적용"""
        pass

    def preview_change(self):
        """변경 미리보기"""
        selected = self.get_selected_items()
        if not selected:
            return

        self.preview_table.setRowCount(0)

        new_value = self.qty_input.text() if self.current_mode == "quantity" else ""
        new_spec = self.spec_input.currentText() if self.current_mode == "spec" else ""
        rate = (
            float(self.rate_input.text().replace("%", "").replace("+", ""))
            if self.current_mode == "rate"
            else 0
        )

        for item in selected:
            row = self.preview_table.rowCount()
            self.preview_table.insertRow(row)

            current_qty = float(item.get("quantity", 0))

            if self.current_mode == "quantity":
                new_qty = float(new_value) if new_value else current_qty
            elif self.current_mode == "rate":
                new_qty = current_qty * (1 + rate / 100)
            else:
                new_qty = current_qty

            change_qty = new_qty - current_qty
            change_rate = (change_qty / current_qty * 100) if current_qty > 0 else 0

            self.preview_table.setItem(row, 0, QTableWidgetItem(item.get("name", "")))
            self.preview_table.setItem(row, 1, QTableWidgetItem(str(current_qty)))
            self.preview_table.setItem(row, 2, QTableWidgetItem(str(round(new_qty, 2))))
            self.preview_table.setItem(
                row, 3, QTableWidgetItem(str(round(change_qty, 2)))
            )
            self.preview_table.setItem(row, 4, QTableWidgetItem(f"{change_rate:+.1f}%"))

    def apply_change(self):
        """변경 적용"""
        selected = self.get_selected_items()
        if not selected:
            return

        reason = self.reason_edit.toPlainText()
        if not reason:
            # 확인 대화상자
            pass

        # 변경 이력 기록
        history_entry = {
            "datetime": "2026-02-11 11:00:00",  # 현재 일시
            "type": self.current_mode,
            "count": len(selected),
            "reason": reason,
            "author": "User",
        }
        self.change_history.append(history_entry)

        # 변경 적용 신호 발송
        self.change_applied.emit(
            {"items": selected, "mode": self.current_mode, "reason": reason}
        )

    def undo_last_change(self):
        """마지막 변경 취소"""
        if self.change_history:
            self.change_history.pop()
            # 원본 데이터 복원
            self.current_data = [item.copy() for item in self.original_data]
            self.load_data()

    def get_history(self) -> List[dict]:
        """변경 이력 반환"""
        return self.change_history


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    test_data = [
        {
            "name": "전등기",
            "spec": "LED 40W",
            "quantity": 50,
            "unit": "개",
            "gongjong": "조명",
        },
        {
            "name": "콘센트",
            "spec": "일반용",
            "quantity": 120,
            "unit": "개",
            "gongjong": "전력",
        },
        {
            "name": "스위치",
            "spec": "1회로",
            "quantity": 30,
            "unit": "개",
            "gongjong": "조명",
        },
    ]

    dialog = DesignChangePopup(current_data=test_data)
    dialog.exec()
