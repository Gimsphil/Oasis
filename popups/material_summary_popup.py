# -*- coding: utf-8 -*-
"""
소요자재 집계 팝업 (Material Summary Popup)
======================================
전체 프로젝트의 사용 자재를 집계하여 표시

기능:
- 품명/규격/단위별 수량 합산
- 근거추적 (사용 공종/행 표시)
- 엑셀 호환 Txt 복사
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
    QMessageBox,
    QApplication,
)


class MaterialSummaryPopup(QDialog):
    """소요자재 집계 팝업"""

    def __init__(self, parent_tab, parent=None):
        super().__init__(parent)
        self.parent_tab = parent_tab
        self.setWindowTitle("소요자재 집계")
        self.resize(900, 600)

        # 컬럼 정의
        self.columns = ["번호", "품명", "규격", "단위", "산출수량", "사용공종"]

        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)

        # 상단 정보
        info_label = QLabel("전체 공종에서 사용된 자재 목록입니다.")
        info_label.setStyleSheet("color: #666; font-size: 11pt;")
        layout.addWidget(info_label)

        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setRowCount(0)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # 버튼 레이아웃
        btn_layout = QHBoxLayout()

        # 새로고침 버튼
        btn_refresh = QPushButton("새로고침")
        btn_refresh.clicked.connect(self._load_data)
        btn_layout.addWidget(btn_refresh)

        # 근거추적 버튼
        btn_trace = QPushButton("근거추적")
        btn_trace.clicked.connect(self._trace_origin)
        btn_layout.addWidget(btn_trace)

        # Txt 복사 버튼
        btn_copy = QPushButton("Txt 복사")
        btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_layout.addWidget(btn_copy)

        btn_layout.addStretch()

        # 닫기 버튼
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def _load_data(self):
        """데이터 로드 및 집계"""
        self.table.setRowCount(0)

        # 집계 데이터: {(품명, 규격, 단위): {'qty': float, 'gongjong': str, 'rows': []}}
        aggregated = {}

        try:
            # 전체 공종 순회
            for gongjong, eulji_list in self.parent_tab.eulji_data.items():
                if not eulji_list:
                    continue

                for row_idx, row_data in enumerate(eulji_list):
                    item_name = row_data.get("item", "").strip()
                    if not item_name:
                        continue

                    # 수량 계산
                    formula = row_data.get("formula", "")
                    total = row_data.get("total", "")

                    try:
                        from utils.formula_parser import parse_formula

                        if total:
                            qty = float(total)
                        elif formula:
                            qty = parse_formula(formula)
                        else:
                            qty = 0.0
                    except:
                        qty = 0.0

                    if qty <= 0:
                        continue

                    # 키 생성 (품명, 규격, 단위)
                    unit = row_data.get("unit", "").strip()
                    key = (item_name, "", unit)  # 규격은 현재 미사용

                    if key not in aggregated:
                        aggregated[key] = {
                            "qty": 0.0,
                            "gongjong": gongjong,
                            "rows": [],
                        }

                    aggregated[key]["qty"] += qty
                    aggregated[key]["rows"].append(
                        {"gongjong": gongjong, "row": row_idx + 1, "qty": qty}
                    )

            # 테이블에 표시
            for idx, (key, data) in enumerate(aggregated.items()):
                row = self.table.rowCount()
                self.table.insertRow(row)

                # 번호
                self.table.setItem(row, 0, QTableWidgetItem(str(idx + 1)))

                # 품명
                self.table.setItem(row, 1, QTableWidgetItem(key[0]))

                # 규격
                self.table.setItem(row, 2, QTableWidgetItem(key[1]))

                # 단위
                self.table.setItem(row, 3, QTableWidgetItem(key[2]))

                # 산출수량
                qty_str = (
                    str(int(data["qty"]))
                    if data["qty"] == int(data["qty"])
                    else str(data["qty"])
                )
                self.table.setItem(row, 4, QTableWidgetItem(qty_str))

                # 사용공종 (첫 번째 공종만 표시)
                self.table.setItem(row, 5, QTableWidgetItem(data["gongjong"]))

            # 정렬: 품명 순
            self.table.sortItems(1)

        except Exception as e:
            print(f"[ERROR] 소요자재 집계 실패: {e}")

    def _trace_origin(self):
        """근거추적: 선택된 자재의 사용 위치 표시"""
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "선택 필요", "추적할 자재를 선택하세요.")
            return

        # 선택된 행 데이터 수집
        item_name = self.table.item(selected, 1).text()
        gongjong = self.table.item(selected, 5).text()

        # 상세 정보
        details = f"[{item_name}]\n"
        details += f"공종: {gongjong}\n\n"
        details += "사용 위치:\n"

        for key, data in self.parent_tab.eulji_data.items():
            for row_idx, row_data in enumerate(data):
                if row_data.get("item", "").strip() == item_name:
                    total = row_data.get("total", "")
                    details += f"  - {key} 행 {row_idx + 1}: {total}\n"

        QMessageBox.information(self, "근거추적", details)

    def _copy_to_clipboard(self):
        """엑셀 호환 Txt로 클립보드 복사"""
        lines = []

        # 헤더
        lines.append("\t".join(["품명", "규격", "단위", "산출수량"]))

        # 데이터
        for row in range(self.table.rowCount()):
            cols = []
            for col in range(1, 5):  # 품명~수량
                item = self.table.item(row, col)
                cols.append(item.text() if item else "")
            lines.append("\t".join(cols))

        # 클립보드 복사
        text = "\n".join(lines)
        QApplication.clipboard().setText(text)

        QMessageBox.information(
            self, "복사 완료", "클립보드에 복사되었습니다.\n엑셀에 붙여넣기 하세요."
        )


# ============== 테스트 ==============
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Mock parent_tab for testing
    class MockParentTab:
        def __init__(self):
            self.eulji_data = {
                "1. 전등공사": [
                    {"item": "조명기구", "formula": "5", "total": "5", "unit": "개"},
                    {
                        "item": "전선 2.5sq",
                        "formula": "100+50",
                        "total": "150",
                        "unit": "m",
                    },
                ],
                "2. 전열공사": [
                    {"item": "콘센트", "formula": "10", "total": "10", "unit": "개"},
                    {
                        "item": "전선 2.5sq",
                        "formula": "200",
                        "total": "200",
                        "unit": "m",
                    },
                ],
            }

    popup = MaterialSummaryPopup(MockParentTab())
    popup.show()
    sys.exit(app.exec())
