"""
간선 산출판 (Cable Routing Board)
전선/케이블 간선의 경로를 시각적으로 관리하는 시스템

기능:
- 간선별 산출항목 정리
- 경로별 그룹핑
- 케이블별 규격/수량 관리

참고: egManual.pdf p172-179
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
    QTreeWidget,
    QTreeWidgetItem,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class CableRoutingPopup(QDialog):
    """
    간선 산출판 팝업
    케이블/전선 간선의 산출 내역을 경로별로 정리
    """

    closed = pyqtSignal(dict)

    def __init__(self, parent=None, cable_data: list = None):
        super().__init__(parent)
        self.setWindowTitle("간선 산출판")
        self.setMinimumSize(1000, 700)
        self.cable_data = cable_data or []

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 상단 툴바
        toolbar = self.create_toolbar()
        layout.addLayout(toolbar)

        # 메인 스플리터
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 좌측: 간선 트리
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.route_tree = QTreeWidget()
        self.route_tree.setHeaderLabels(["간선 경로", "규격", "수량"])
        self.route_tree.setColumnWidth(0, 300)
        self.route_tree.itemClicked.connect(self.on_route_selected)

        left_layout.addWidget(QLabel("<b>간선 경로</b>"))
        left_layout.addWidget(self.route_tree)
        splitter.addWidget(left_frame)

        # 우측: 간선 상세내역
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.cable_table = QTableWidget()
        self.cable_table.setColumnCount(5)
        self.cable_table.setHorizontalHeaderLabels(
            ["회로", "시작점", "종료점", "규격", "수량(m)"]
        )
        self.cable_table.horizontalHeader().setStretchLastSection(True)
        self.cable_table.setAlternatingRowColors(True)

        right_layout.addWidget(QLabel("<b>간선 상세내역</b>"))
        right_layout.addWidget(self.cable_table)
        splitter.addWidget(right_frame)

        layout.addWidget(splitter)

        # 하단 버튼
        buttons = self.create_buttons()
        layout.addLayout(buttons)

    def create_toolbar(self) -> QHBoxLayout:
        """툴바 생성"""
        layout = QHBoxLayout()

        # 케이블 유형 필터
        layout.addWidget(QLabel("케이블:"))
        self.cable_type_combo = QComboBox()
        self.cable_type_combo.addItems(["전체", "전력", "통신", "접지"])
        self.cable_type_combo.currentIndexChanged.connect(self.filter_data)
        layout.addWidget(self.cable_type_combo)

        # 검색
        layout.addWidget(QLabel("검색:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("회로명 검색...")
        self.search_edit.textChanged.connect(self.filter_data)
        layout.addWidget(self.search_edit)

        layout.addStretch()
        return layout

    def create_buttons(self) -> QHBoxLayout:
        """버튼 생성"""
        layout = QHBoxLayout()

        self.add_route_btn = QPushButton("Route Add")
        self.add_route_btn.clicked.connect(self.add_route)
        layout.addWidget(self.add_route_btn)

        self.print_btn = QPushButton("인쇄")
        self.print_btn.clicked.connect(self.print_routing)
        layout.addWidget(self.print_btn)

        self.export_btn = QPushButton("내보내기")
        self.export_btn.clicked.connect(self.export_routing)
        layout.addWidget(self.export_btn)

        layout.addStretch()

        self.close_btn = QPushButton("닫기")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)

        return layout

    def load_data(self):
        """데이터 로드"""
        self.route_tree.clear()

        for item in self.cable_data:
            parent = QTreeWidgetItem(self.route_tree)
            parent.setText(0, item.get("route", ""))
            parent.setText(1, item.get("spec", ""))
            parent.setText(2, str(item.get("quantity", 0)))

            # 하위 항목 추가
            for sub_item in item.get("circuits", []):
                child = QTreeWidgetItem(parent)
                child.setText(0, sub_item.get("circuit", ""))
                child.setText(1, sub_item.get("from", ""))
                child.setText(2, sub_item.get("to", ""))
                child.setText(3, sub_item.get("spec", ""))
                child.setText(4, str(sub_item.get("quantity", 0)))

    def on_route_selected(self, item, column):
        """경로 선택 시 상세내역 표시"""
        # 상세내역 업데이트 로직
        pass

    def filter_data(self):
        """데이터 필터링"""
        cable_type = self.cable_type_combo.currentText()
        search_text = self.search_edit.text().lower()

        for i in range(self.route_tree.topLevelItemCount()):
            item = self.route_tree.topLevelItem(i)
            match = True

            if cable_type != "전체":
                # 케이블 유형 체크
                pass

            if search_text:
                # 검색어 체크
                pass

            item.setHidden(not match)

    def add_route(self):
        """경로 추가"""
        # 경로 추가 로직
        pass

    def print_routing(self):
        """간선 산출판 인쇄"""
        pass

    def export_routing(self):
        """간선 산출판 내보내기"""
        pass

    def get_selected_data(self) -> Optional[dict]:
        """선택된 데이터 반환"""
        item = self.route_tree.currentItem()
        if item:
            return {"route": item.text(0)}
        return None


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    test_data = [
        {
            "route": "1층 전등 회로",
            "spec": "CVV 2.0mm",
            "quantity": 500,
            "circuits": [
                {
                    "circuit": "L1-1",
                    "from": "분전반",
                    "to": "P1-1",
                    "spec": "CVV 2.0mm",
                    "quantity": 50,
                },
                {
                    "circuit": "L1-2",
                    "from": "P1-1",
                    "to": "P1-2",
                    "spec": "CVV 2.0mm",
                    "quantity": 30,
                },
            ],
        }
    ]

    dialog = CableRoutingPopup(cable_data=test_data)
    dialog.exec()
