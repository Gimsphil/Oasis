# -*- coding: utf-8 -*-
"""
분전반 산출 매니저
==================
분전반 산출을 담당하는 매니저 클래스.
산출목록에서 '분전반 산출'을 선택하면 팝업을 열어 항목을 입력하고
을지 테이블로 자동 연동합니다.
"""

import os
import json
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QHeaderView,
    QAbstractItemView,
    QMessageBox,
    QComboBox,
    QLineEdit,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


# 분전반 구분 목록
BOARD_TYPES = ["동력반", "전등반", "분전반", "제어반", "MCC", "VCB반", "기타"]

# 기본 분전반 항목 목록 (을지 자동 입력 템플릿)
DEFAULT_BOARD_ITEMS = [
    {"item": "분전반 본체", "unit": "대"},
    {"item": "동력배선", "unit": "m"},
    {"item": "전등배선", "unit": "m"},
    {"item": "접지공사", "unit": "식"},
    {"item": "설치공사", "unit": "식"},
]


class DistributionBoardPanel(QDialog):
    """분전반 산출 편집 팝업."""

    items_applied = pyqtSignal(list)  # [(item, formula, unit), ...] 를 을지로 송출

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("분전반 산출")
        self.setMinimumSize(640, 480)
        self.setStyleSheet("""
            QDialog { background-color: #f8f9fa; }
            QLabel { font-family: '새굴림'; font-size: 10pt; }
            QPushButton {
                font-family: '새굴림'; font-size: 10pt;
                background-color: #f0f0f0;
                border: 1px solid #aaa; padding: 3px 10px;
            }
            QPushButton:hover { background-color: #dde8f0; }
            QTableWidget {
                font-family: '새굴림'; font-size: 10pt;
                gridline-color: #ccc;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # 헤더
        hdr = QLabel("분전반 산출 항목 입력")
        hdr.setStyleSheet("font-weight: bold; font-size: 11pt; color: #333;")
        layout.addWidget(hdr)

        # 분전반 구분 선택
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("구분:"))
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(BOARD_TYPES)
        self.cmb_type.setFixedWidth(120)
        top_row.addWidget(self.cmb_type)

        top_row.addWidget(QLabel("명칭:"))
        self.edt_name = QLineEdit()
        self.edt_name.setPlaceholderText("예) 1F 전등 분전반")
        self.edt_name.setFixedWidth(220)
        top_row.addWidget(self.edt_name)
        top_row.addStretch()
        layout.addLayout(top_row)

        # 항목 테이블
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["산출목록", "산출수식", "단위"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(1, 180)
        self.table.setColumnWidth(2, 60)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        # 버튼 행
        btn_row = QHBoxLayout()
        btn_add = QPushButton("항목 추가 (Ctrl+N)")
        btn_del = QPushButton("항목 삭제 (Ctrl+Y)")
        btn_load = QPushButton("기본 항목 불러오기")
        btn_add.clicked.connect(self._add_row)
        btn_del.clicked.connect(self._del_row)
        btn_load.clicked.connect(self._load_defaults)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        btn_row.addWidget(btn_load)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 구분선
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #ccc;")
        layout.addWidget(sep)

        # 확인/취소
        action_row = QHBoxLayout()
        action_row.addStretch()
        btn_ok = QPushButton("을지에 적용")
        btn_cancel = QPushButton("닫기")
        btn_ok.setStyleSheet("background-color: #d0e8f8; font-weight: bold;")
        btn_ok.clicked.connect(self._apply)
        btn_cancel.clicked.connect(self.reject)
        action_row.addWidget(btn_ok)
        action_row.addWidget(btn_cancel)
        layout.addLayout(action_row)

    def _add_row(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setRowHeight(r, 22)

    def _del_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _load_defaults(self):
        """기본 분전반 항목을 테이블에 채우기."""
        self.table.setRowCount(0)
        for item in DEFAULT_BOARD_ITEMS:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setRowHeight(r, 22)
            self.table.setItem(r, 0, QTableWidgetItem(item["item"]))
            self.table.setItem(r, 1, QTableWidgetItem(""))
            self.table.setItem(r, 2, QTableWidgetItem(item["unit"]))

    def _apply(self):
        """을지 테이블로 항목 전송."""
        rows = []
        for r in range(self.table.rowCount()):
            item = (self.table.item(r, 0) or QTableWidgetItem()).text().strip()
            formula = (self.table.item(r, 1) or QTableWidgetItem()).text().strip()
            unit = (self.table.item(r, 2) or QTableWidgetItem()).text().strip()
            if item:
                rows.append((item, formula, unit))
        if not rows:
            QMessageBox.information(self, "알림", "적용할 항목이 없습니다.")
            return
        self.items_applied.emit(rows)
        QMessageBox.information(self, "적용 완료", f"{len(rows)}개 항목이 을지에 추가되었습니다.")
        self.accept()

    def get_data(self):
        """현재 테이블 데이터 반환 (저장용)."""
        rows = []
        for r in range(self.table.rowCount()):
            rows.append({
                "item": (self.table.item(r, 0) or QTableWidgetItem()).text(),
                "formula": (self.table.item(r, 1) or QTableWidgetItem()).text(),
                "unit": (self.table.item(r, 2) or QTableWidgetItem()).text(),
            })
        return {
            "board_type": self.cmb_type.currentText(),
            "board_name": self.edt_name.text(),
            "items": rows,
        }

    def set_data(self, data: dict):
        """저장된 데이터 복원."""
        if not data:
            return
        self.cmb_type.setCurrentText(data.get("board_type", BOARD_TYPES[0]))
        self.edt_name.setText(data.get("board_name", ""))
        self.table.setRowCount(0)
        for row in data.get("items", []):
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setRowHeight(r, 22)
            self.table.setItem(r, 0, QTableWidgetItem(row.get("item", "")))
            self.table.setItem(r, 1, QTableWidgetItem(row.get("formula", "")))
            self.table.setItem(r, 2, QTableWidgetItem(row.get("unit", "")))


# ─────────────────────────────────────────────────────────────────────────────


class DistributionBoardManager:
    """OutputDetailTab과 연결되는 분전반 매니저."""

    # 분전반 산출로 인식할 산출목록 키워드 목록
    BOARD_KEYWORDS = ["분전반 산출", "동력반 산출", "전등반 산출", "분전반"]

    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        self._current_row: int = -1
        self._panel: DistributionBoardPanel | None = None
        self._board_data: dict = {}  # {eulji_row: data_dict} 저장

    # ─────────────────────────────────────────
    # 공개 API
    # ─────────────────────────────────────────

    def edit_row(self, row: int) -> None:
        """선택한 을지 행을 분전반 편집 대상으로 지정하고 팝업 열기."""
        self._current_row = row
        table = getattr(self.parent_tab, "eulji_table", None)
        item_col = self.parent_tab.EULJI_COLS.get("ITEM", 5)
        if table is not None and row >= 0:
            table.setCurrentCell(row, item_col)
        self.show_panel(row)

    def show_panel(self, row: int = -1) -> None:
        """분전반 산출 팝업 표시."""
        if self._panel is None:
            self._panel = DistributionBoardPanel(self.parent_tab.main_window)
            self._panel.items_applied.connect(self._on_items_applied)

        # 기존 저장 데이터 있으면 복원
        if row >= 0 and row in self._board_data:
            self._panel.set_data(self._board_data[row])

        self._current_row = row
        self._panel.exec()

    def is_board_item(self, item_text: str) -> bool:
        """산출목록 텍스트가 분전반 산출 키워드인지 확인."""
        stripped = item_text.strip()
        return any(kw in stripped for kw in self.BOARD_KEYWORDS)

    def save_data(self) -> dict:
        """현재 분전반 데이터를 직렬화 가능한 dict로 반환."""
        return {str(k): v for k, v in self._board_data.items()}

    def load_data(self, data: dict) -> None:
        """저장된 dict에서 분전반 데이터 복원."""
        self._board_data = {int(k): v for k, v in data.items() if k.isdigit()}

    # ─────────────────────────────────────────
    # 내부 로직
    # ─────────────────────────────────────────

    def _on_items_applied(self, rows: list) -> None:
        """팝업에서 '을지에 적용' 클릭 시 을지 테이블에 항목 입력."""
        table = getattr(self.parent_tab, "eulji_table", None)
        if table is None:
            return

        eulji_cols = self.parent_tab.EULJI_COLS
        insert_row = self._current_row if self._current_row >= 0 else table.rowCount()

        table.blockSignals(True)
        for i, (item_text, formula_text, unit_text) in enumerate(rows):
            r = insert_row + i
            # 행이 부족하면 추가
            if r >= table.rowCount():
                table.insertRow(r)
                table.setRowHeight(r, 22)

            def _set(col_key, text):
                col = eulji_cols.get(col_key, -1)
                if col < 0:
                    return
                cell = table.item(r, col) or QTableWidgetItem()
                cell.setText(text)
                table.setItem(r, col, cell)

            _set("ITEM", item_text)
            _set("FORMULA", formula_text)
            _set("UNIT", unit_text)

        table.blockSignals(False)

        # 데이터 저장
        if self._panel:
            self._board_data[self._current_row] = self._panel.get_data()

        print(f"[INFO] DistributionBoardManager: {len(rows)} items applied at row {insert_row}")
