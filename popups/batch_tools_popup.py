# -*- coding: utf-8 -*-
"""
일괄 변경 도구 (Batch Tools)
=========================
공종 간 일괄 변경 기능

기능:
- 전체 목록 집계
- 산출 보조 내용 일괄 바꾸기
- 수량 증감 (%)
- 재질 변경 (HI → ST 등)
"""

import os
import json
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QTabBar,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QLineEdit,
    QHeaderView,
    QMessageBox,
    QApplication,
    QSpinBox,
)


class BatchToolsPopup(QDialog):
    """일괄 변경 도구 팝업"""

    def __init__(self, parent_tab, parent=None):
        super().__init__(parent)
        self.parent_tab = parent_tab
        self.setWindowTitle("일괄 변경 도구")
        self.resize(800, 600)

        self._setup_ui()

    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)

        # 탭 위젯
        self.tabs = QTabWidget()

        # 탭 1: 전체 목록 집계
        tab1 = self._create_aggregate_tab()
        self.tabs.addTab(tab1, "전체 목록 집계")

        # 탭 2: 수량 증감
        tab2 = self._create_adjust_tab()
        self.tabs.addTab(tab2, "수량 증감 (%)")

        # 탭 3: 재질 변경
        tab3 = self._create_material_tab()
        self.tabs.addTab(tab3, "재질 변경")

        layout.addWidget(self.tabs)

        # 하단 버튼
        btn_layout = QHBoxLayout()
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _create_aggregate_tab(self):
        """전체 목록 집계 탭"""
        widget = QVBoxLayout()

        info = QLabel("모든 공종의 산출목록을 하나로 취합합니다.")
        widget.addWidget(info)

        # 테이블
        self.agg_table = QTableWidget()
        self.agg_table.setColumnCount(5)
        self.agg_table.setHorizontalHeaderLabels(
            ["품명", "규격", "단위", "사용공종수", "총수량"]
        )
        self.agg_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        widget.addWidget(self.agg_table)

        # 버튼
        btn = QPushButton("집계 실행")
        btn.clicked.connect(self._run_aggregate)
        widget.addWidget(btn)

        container = QWidget()
        container.setLayout(widget)
        return container

    def _create_adjust_tab(self):
        """수량 증감 탭"""
        widget = QVBoxLayout()

        info = QLabel("특정 자재의 수량을 비율(%)로 증감합니다.")
        widget.addWidget(info)

        # 입력 영역
        input_layout = QHBoxLayout()

        input_layout.addWidget(QLabel("품명 포함文字:"))
        self.search_term = QLineEdit()
        self.search_term.setPlaceholderText("예: 전선, 케이블")
        input_layout.addWidget(self.search_term)

        input_layout.addWidget(QLabel("증감율 (%):"))
        self.percent_spin = QSpinBox()
        self.percent_spin.setRange(-100, 1000)
        self.percent_spin.setValue(10)
        input_layout.addWidget(self.percent_spin)

        widget.addLayout(input_layout)

        # 버튼
        btn = QPushButton("적용")
        btn.clicked.connect(self._run_adjust)
        widget.addWidget(btn)

        # 결과 표시
        self.adjust_result = QLabel("")
        widget.addWidget(self.adjust_result)

        container = QWidget()
        container.setLayout(widget)
        return container

    def _create_material_tab(self):
        """재질 변경 탭"""
        widget = QVBoxLayout()

        info = QLabel("자재의 재질을 일괄 변경합니다. (예: HI → ST)")
        widget.addWidget(info)

        # 입력 영역
        input_layout = QHBoxLayout()

        input_layout.addWidget(QLabel("변경 전:"))
        self.before_material = QLineEdit()
        self.before_material.setPlaceholderText("예: HI")
        input_layout.addWidget(self.before_material)

        input_layout.addWidget(QLabel("→ 변경 후:"))
        self.after_material = QLineEdit()
        self.after_material.setPlaceholderText("예: ST")
        input_layout.addWidget(self.after_material)

        widget.addLayout(input_layout)

        # 버튼
        btn = QPushButton("변경 실행")
        btn.clicked.connect(self._run_material_change)
        widget.addWidget(btn)

        # 결과 표시
        self.material_result = QLabel("")
        widget.addWidget(self.material_result)

        container = QWidget()
        container.setLayout(widget)
        return container

    def _run_aggregate(self):
        """전체 목록 집계 실행"""
        self.agg_table.setRowCount(0)

        # 집계: {(품명, 규격, 단위): {'count': int, 'qty': float, 'gongjongs': set}}
        aggregated = {}

        for gongjong, eulji_list in self.parent_tab.eulji_data.items():
            for row_data in eulji_list:
                item = row_data.get("item", "").strip()
                if not item:
                    continue

                unit = row_data.get("unit", "").strip()
                total = row_data.get("total", "").strip()

                try:
                    qty = float(total) if total else 0.0
                except:
                    qty = 0.0

                if qty <= 0:
                    continue

                key = (item, "", unit)

                if key not in aggregated:
                    aggregated[key] = {"count": 0, "qty": 0.0, "gongjongs": set()}

                aggregated[key]["count"] += 1
                aggregated[key]["qty"] += qty
                aggregated[key]["gongjongs"].add(gongjong)

        # 테이블에 표시
        for key, data in aggregated.items():
            row = self.agg_table.rowCount()
            self.agg_table.insertRow(row)

            self.agg_table.setItem(row, 0, QTableWidgetItem(key[0]))
            self.agg_table.setItem(row, 1, QTableWidgetItem(key[1]))
            self.agg_table.setItem(row, 2, QTableWidgetItem(key[2]))
            self.agg_table.setItem(row, 3, QTableWidgetItem(str(data["count"])))

            qty_str = (
                str(int(data["qty"]))
                if data["qty"] == int(data["qty"])
                else str(data["qty"])
            )
            self.agg_table.setItem(row, 4, QTableWidgetItem(qty_str))

        self.agg_table.sortItems(0)

    def _run_adjust(self):
        """수량 증감 실행"""
        term = self.search_term.text().strip()
        percent = self.percent_spin.value()

        if not term:
            QMessageBox.warning(self, "입력 필요", "품명 포함文字를 입력하세요.")
            return

        if percent == 0:
            QMessageBox.warning(self, "변경 없음", "증감율을 변경하세요.")
            return

        # 실행 확인
        confirm = QMessageBox.question(
            self,
            "확인",
            f"'{term}' 포함 자재의 수량을 {percent}% {'증가' if percent > 0 else '감소'}하시겠습니까?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        changed_count = 0

        for gongjong, eulji_list in self.parent_tab.eulji_data.items():
            for row_data in eulji_list:
                item = row_data.get("item", "").strip()
                if term in item:
                    total = row_data.get("total", "").strip()
                    if total:
                        try:
                            qty = float(total)
                            new_qty = qty * (1 + percent / 100.0)
                            row_data["total"] = str(new_qty)
                            changed_count += 1
                        except:
                            pass

        self.adjust_result.setText(f"{changed_count}개 항목이 변경되었습니다.")
        QMessageBox.information(
            self, "완료", f"{changed_count}개 항목이 변경되었습니다."
        )

    def _run_material_change(self):
        """재질 변경 실행"""
        before = self.before_material.text().strip()
        after = self.after_material.text().strip()

        if not before or not after:
            QMessageBox.warning(self, "입력 필요", "변경 전/후 재질을 모두 입력하세요.")
            return

        # 실행 확인
        confirm = QMessageBox.question(
            self, "확인", f"재질 '{before}' → '{after}'로 일괄 변경하시겠습니까?"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        changed_count = 0

        for gongjong, eulji_list in self.parent_tab.eulji_data.items():
            for row_data in eulji_list:
                item = row_data.get("item", "").strip()
                # 품명에서 before를 after로 변경
                if before in item:
                    new_item = item.replace(before, after)
                    row_data["item"] = new_item
                    changed_count += 1

        self.material_result.setText(f"{changed_count}개 항목이 변경되었습니다.")
        QMessageBox.information(
            self, "완료", f"{changed_count}개 항목이 변경되었습니다."
        )


# ============== 테스트 ==============
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Mock parent_tab
    class MockParentTab:
        def __init__(self):
            self.eulji_data = {
                "1. 전등공사": [
                    {"item": "전선 HI 2.5sq", "total": "100", "unit": "m"},
                    {"item": "전선 HI 3.5sq", "total": "50", "unit": "m"},
                ],
                "2. 전열공사": [
                    {"item": "전선 HI 2.5sq", "total": "200", "unit": "m"},
                    {"item": "케이블 HI", "total": "30", "unit": "m"},
                ],
            }

    popup = BatchToolsPopup(MockParentTab())
    popup.show()
    sys.exit(app.exec())
