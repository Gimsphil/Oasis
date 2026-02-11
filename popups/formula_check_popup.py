# -*- coding: utf-8 -*-
"""
산식 검사 팝업 (Formula Check Popup)
=================================
산출수식 오류 검사 결과 표시
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QHeaderView,
    QMessageBox,
)


class FormulaCheckPopup(QDialog):
    """산식 검사 결과 팝업"""

    def __init__(self, errors: list, parent=None):
        super().__init__(parent)
        self.errors = errors
        self.setWindowTitle("산식 검사 결과")
        self.resize(700, 500)

        self._setup_ui()
        self._load_errors()

    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)

        # 상단 정보
        if self.errors:
            info_text = f"❌ 총 {len(self.errors)}개의 오류가 발견되었습니다."
            info_text += "\n\n더블클릭하면 해당 위치로 이동합니다."
        else:
            info_text = "✅ 모든 수식이 정상입니다."
        info_label = QLabel(info_text)
        info_label.setStyleSheet("font-size: 11pt;")
        layout.addWidget(info_label)

        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["공종", "행", "수식", "오류유형"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setRowCount(0)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

        # 버튼
        btn_layout = QHBoxLayout()
        btn_refresh = QPushButton("새로고침")
        btn_refresh.clicked.connect(self._reload)
        btn_layout.addWidget(btn_refresh)
        btn_layout.addStretch()
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _load_errors(self):
        """오류 데이터 로드"""
        self.table.setRowCount(0)

        for error in self.errors:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # 공종
            self.table.setItem(row, 0, QTableWidgetItem(error.get("공종", "")))

            # 행
            self.table.setItem(row, 1, QTableWidgetItem(str(error.get("행", ""))))

            # 수식
            self.table.setItem(row, 2, QTableWidgetItem(error.get("수식", "")))

            # 오류유형
            error_types = [e.get("type", "") for e in error.get("오류", [])]
            self.table.setItem(row, 3, QTableWidgetItem(", ".join(error_types)))

    def _on_double_click(self, row, col):
        """더블클릭 시 해당 위치 정보 제공"""
        if row < len(self.errors):
            error = self.errors[row]
            info = f"[{error['공종']} 행 {error['행']}]\n"
            info += f"수식: {error['수식']}\n\n"
            info += "오류 상세:\n"
            for err in error.get("오류", []):
                info += f"- {err.get('type', '')}: {err.get('message', '')}\n"
            QMessageBox.information(self, "오류 상세", info)

    def _reload(self):
        """새로고침 (부모에서 재호출)"""
        self.accept()  # 팝업 닫기
        # 실제 사용 시 부모에서 다시 팝업 열기


# ============== 테스트 ==============
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 테스트 오류 데이터
    test_errors = [
        {
            "공종": "1. 전등공사",
            "행": 5,
            "수식": "(3.5+2.1",
            "오류": [
                {"type": "괄호_불일치", "message": "1 vs 0", "severity": "error"},
            ],
        },
        {
            "공종": "1. 전등공사",
            "행": 10,
            "수식": "++5",
            "오류": [{"type": "연속_연산자", "message": "++", "severity": "warning"}],
        },
        {
            "공종": "2. 전열공사",
            "행": 3,
            "수식": "3.5+",
            "오류": [
                {
                    "type": "끝_연산자",
                    "message": "수식이 연산자로 끝남",
                    "severity": "warning",
                }
            ],
        },
    ]

    popup = FormulaCheckPopup(test_errors)
    popup.show()
    sys.exit(app.exec())
