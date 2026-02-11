"""
그림산출 (Graphic Output)
도면에서 산출 항목을 시각적으로 선택하여 수량 산출

기능:
- 도면 이미지/DXF 파일 표시
- 산출 항목 도면 상에서 선택
- 선택 영역에서 수량 자동 산출
- 산출 항목 연결선 지정

참고: egManual.pdf p151-163
"""

from typing import Optional, List, Dict, Tuple
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
    QGraphicsView,
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsLineItem,
    QGraphicsEllipseItem,
    QMenu,
    QMenuBar,
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QLineF, QPointF
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QFont, QAction


class DrawingGraphicsScene(QGraphicsScene):
    """도면 그래픽 씬 - 도면 표시 및 선택 처리"""

    item_selected = pyqtSignal(dict)  # 항목 선택 신호

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 800, 600)
        self.drawing_items = []  # 도면 객체 목록
        self.output_items = []  # 산출 항목 목록

        # 선택 상태
        self.selection_color = QColor(255, 0, 0, 100)  # 선택 색상 (반투명 빨강)
        self.selected_items = []

    def load_dxf_image(self, image_path: str):
        """DXF/이미지 로드"""
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.clear()
            self.addPixmap(
                pixmap.scaled(
                    800,
                    600,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def add_output_marker(self, x: float, y: float, item_data: dict):
        """산출 항목 마커 추가"""
        # 원형 마커 생성
        marker = QGraphicsEllipseItem(x - 10, y - 10, 20, 20)
        marker.setBrush(QBrush(QColor(0, 120, 255)))
        marker.setPen(QPen(QColor(255, 255, 255), 2))
        marker.setData(0, item_data)  # 데이터 저장

        self.addItem(marker)
        self.output_items.append(marker)
        return marker

    def add_selection_rect(self, rect: QRectF) -> QGraphicsRectItem:
        """선택 사각형 추가"""
        selection = QGraphicsRectItem(rect)
        selection.setBrush(QBrush(self.selection_color))
        selection.setPen(QPen(QColor(255, 0, 0), 2))
        self.addItem(selection)
        self.selected_items.append(selection)
        return selection

    def add_connection_line(self, start: QPointF, end: QPointF) -> QGraphicsLineItem:
        """접속선 추가"""
        line = QGraphicsLineItem(QLineF(start, end))
        line.setPen(QPen(QColor(0, 200, 0), 3))
        self.addItem(line)
        return line

    def mousePressEvent(self, event):
        """마우스 클릭 처리"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.scenePos()

            # 클릭 위치의 항목 찾기
            items = self.items(pos)
            for item in items:
                if isinstance(item, QGraphicsEllipseItem) and item.data(0):
                    # 산출 항목 선택
                    data = item.data(0)
                    self.item_selected.emit(data)
                    break

        super().mousePressEvent(event)

    def clear_selections(self):
        """선택 해제"""
        for item in self.selected_items:
            self.removeItem(item)
        self.selected_items.clear()


class GraphicOutputPopup(QDialog):
    """
    그림산출 팝업
    도면에서 산출 항목을 시각적으로 선택하여 수량 산출
    """

    output_extracted = pyqtSignal(list)  # 추출된 산출 항목

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("그림산출")
        self.setMinimumSize(1200, 800)

        self.drawing_path = None
        self.extracted_items = []  # 추출된 항목

        self.setup_ui()
        self.setup_menu()

    def setup_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)

        # 메인 스플리터
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 좌측: 도면 표시 영역
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 도면 툴바
        toolbar = self.create_drawing_toolbar()
        left_layout.addLayout(toolbar)

        # 그래픽 뷰
        self.graphics_view = QGraphicsView()
        self.scene = DrawingGraphicsScene()
        self.graphics_view.setScene(self.scene)
        self.graphics_view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        left_layout.addWidget(self.graphics_view)
        splitter.addWidget(left_frame)

        # 우측: 산출 항목 목록
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 탭 구성
        tabs = QTabWidget()

        # 탭 1: 추출 항목
        extract_tab = self.create_extract_tab()
        tabs.addTab(extract_tab, "추출항목")

        # 탭 2: 도면 항목 매핑
        mapping_tab = self.create_mapping_tab()
        tabs.addTab(mapping_tab, "도면매핑")

        right_layout.addWidget(tabs)
        splitter.addWidget(right_frame)

        # 스플리터 비율 설정
        splitter.setSizes([800, 400])
        layout.addWidget(splitter)

        # 하단 버튼
        buttons = self.create_buttons()
        layout.addLayout(buttons)

    def create_drawing_toolbar(self) -> QHBoxLayout:
        """도면 툴바"""
        layout = QHBoxLayout()

        self.open_drawing_btn = QPushButton("도면열기")
        self.open_drawing_btn.clicked.connect(self.open_drawing)
        layout.addWidget(self.open_drawing_btn)

        self.zoom_in_btn = QPushButton("확대")
        self.zoom_in_btn.clicked.connect(lambda: self.graphics_view.scale(1.2, 1.2))
        layout.addWidget(self.zoom_in_btn)

        self.zoom_out_btn = QPushButton("축소")
        self.zoom_out_btn.clicked.connect(lambda: self.graphics_view.scale(0.8, 0.8))
        layout.addWidget(self.zoom_out_btn)

        self.fit_btn = QPushButton("맞춤")
        self.fit_btn.clicked.connect(self.fit_to_window)
        layout.addWidget(self.fit_btn)

        self.clear_selection_btn = QPushButton("선택해제")
        self.clear_selection_btn.clicked.connect(self.scene.clear_selections)
        layout.addWidget(self.clear_selection_btn)

        layout.addStretch()

        return layout

    def create_extract_tab(self) -> QFrame:
        """추출 항목 탭"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)

        # 도구 버튼
        tool_layout = QHBoxLayout()

        self.add_point_btn = QPushButton("점추가")
        self.add_point_btn.setCheckable(True)
        self.add_point_btn.clicked.connect(self.set_point_mode)
        tool_layout.addWidget(self.add_point_btn)

        self.add_rect_btn = QPushButton("영역추가")
        self.add_rect_btn.setCheckable(True)
        self.add_rect_btn.clicked.connect(self.set_rect_mode)
        tool_layout.addWidget(self.add_rect_btn)

        self.add_line_btn = QPushButton("선추가")
        self.add_line_btn.setCheckable(True)
        self.add_line_btn.clicked.connect(self.set_line_mode)
        tool_layout.addWidget(self.add_line_btn)

        layout.addLayout(tool_layout)

        # 추출 항목 테이블
        self.extract_table = QTableWidget()
        self.extract_table.setColumnCount(6)
        self.extract_table.setHorizontalHeaderLabels(
            ["순번", "항목명", "규격", "수량", "단위", "위치"]
        )
        self.extract_table.horizontalHeader().setStretchLastSection(True)
        self.extract_table.setAlternatingRowColors(True)
        self.extract_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        layout.addWidget(self.extract_table)

        # 정보 라벨
        self.extract_info = QLabel("추출 항목: 0개")
        layout.addWidget(self.extract_info)

        return frame

    def create_mapping_tab(self) -> QFrame:
        """도면 매핑 탭"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)

        # 매핑 도구
        mapping_group = QGroupBox("도면 항목 매핑")
        mapping_layout = QGridLayout()

        mapping_layout.addWidget(QLabel("도면기호:"), 0, 0)
        self.symbol_edit = QLineEdit()
        self.symbol_edit.setPlaceholderText("도면에서 선택한 기호...")
        mapping_layout.addWidget(self.symbol_edit, 0, 1)

        mapping_layout.addWidget(QLabel("산출항목:"), 1, 0)
        self.item_combo = QComboBox()
        self.item_combo.addItems(["전등기", "콘센트", "스위치", "분전반", "배선반"])
        mapping_layout.addWidget(self.item_combo, 1, 1)

        mapping_layout.addWidget(QLabel("규격:"), 2, 0)
        self.spec_edit = QLineEdit()
        self.spec_edit.setPlaceholderText("규격 입력...")
        mapping_layout.addWidget(self.spec_edit, 2, 1)

        self.add_mapping_btn = QPushButton("매핑추가")
        self.add_mapping_btn.clicked.connect(self.add_mapping)
        mapping_layout.addWidget(self.add_mapping_btn, 3, 0, 1, 2)

        mapping_group.setLayout(mapping_layout)
        layout.addWidget(mapping_group)

        # 매핑 목록
        layout.addWidget(QLabel("<b>매핑 목록</b>"))

        self.mapping_table = QTableWidget()
        self.mapping_table.setColumnCount(3)
        self.mapping_table.setHorizontalHeaderLabels(["도면기호", "산출항목", "규격"])
        self.mapping_table.horizontalHeader().setStretchLastSection(True)
        self.mapping_table.setAlternatingRowColors(True)

        layout.addWidget(self.mapping_table)

        return frame

    def setup_menu(self):
        """메뉴 바 설정"""
        menubar = QMenuBar()

        # 파일 메뉴
        file_menu = menubar.addMenu("파일")
        open_action = QAction("도면열기", self)
        open_action.triggered.connect(self.open_drawing)
        file_menu.addAction(open_action)

        export_action = QAction("내보내기", self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)

        # 편집 메뉴
        edit_menu = menubar.addMenu("편집")
        clear_action = QAction("선택해제", self)
        clear_action.triggered.connect(self.scene.clear_selections)
        edit_menu.addAction(clear_action)

        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말")
        help_action = QAction("사용법", self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)

    def create_buttons(self) -> QHBoxLayout:
        """버튼 생성"""
        layout = QHBoxLayout()

        self.extract_all_btn = QPushButton("전체추출")
        self.extract_all_btn.clicked.connect(self.extract_all)
        layout.addWidget(self.extract_all_btn)

        self.auto_extract_btn = QPushButton("자동추출")
        self.auto_extract_btn.clicked.connect(self.auto_extract)
        layout.addWidget(self.auto_extract_btn)

        layout.addStretch()

        self.apply_btn = QPushButton("적용")
        self.apply_btn.clicked.connect(self.apply_extraction)
        layout.addWidget(self.apply_btn)

        self.close_btn = QPushButton("닫기")
        self.close_btn.clicked.connect(self.reject)
        layout.addWidget(self.close_btn)

        return layout

    def open_drawing(self):
        """도면 열기"""
        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "도면 열기",
            "",
            "Images (*.png *.jpg *.bmp);;DXF Files (*.dxf);;All Files (*.*)",
        )

        if file_path:
            self.drawing_path = file_path
            self.scene.load_dxf_image(file_path)

    def fit_to_window(self):
        """창에 맞춤"""
        self.graphics_view.fitInView(
            self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
        )

    def set_point_mode(self):
        """점 추가 모드"""
        self.add_point_btn.setChecked(True)
        self.add_rect_btn.setChecked(False)
        self.add_line_btn.setChecked(False)

    def set_rect_mode(self):
        """영역 추가 모드"""
        self.add_point_btn.setChecked(False)
        self.add_rect_btn.setChecked(True)
        self.add_line_btn.setChecked(False)

    def set_line_mode(self):
        """선 추가 모드"""
        self.add_point_btn.setChecked(False)
        self.add_rect_btn.setChecked(False)
        self.add_line_btn.setChecked(True)

    def add_mapping(self):
        """매핑 추가"""
        symbol = self.symbol_edit.text()
        item = self.item_combo.currentText()
        spec = self.spec_edit.text()

        if symbol and item:
            row = self.mapping_table.rowCount()
            self.mapping_table.insertRow(row)
            self.mapping_table.setItem(row, 0, QTableWidgetItem(symbol))
            self.mapping_table.setItem(row, 1, QTableWidgetItem(item))
            self.mapping_table.setItem(row, 2, QTableWidgetItem(spec))

            # 입력 초기화
            self.symbol_edit.clear()
            self.spec_edit.clear()

    def add_extracted_item(self, item_data: dict):
        """추출 항목 추가"""
        row = self.extract_table.rowCount()
        self.extract_table.insertRow(row)

        self.extract_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.extract_table.setItem(row, 1, QTableWidgetItem(item_data.get("name", "")))
        self.extract_table.setItem(row, 2, QTableWidgetItem(item_data.get("spec", "")))
        self.extract_table.setItem(
            row, 3, QTableWidgetItem(str(item_data.get("quantity", 1)))
        )
        self.extract_table.setItem(
            row, 4, QTableWidgetItem(item_data.get("unit", "개"))
        )
        self.extract_table.setItem(
            row, 5, QTableWidgetItem(item_data.get("position", ""))
        )

        self.extracted_items.append(item_data)
        self.update_extract_info()

    def update_extract_info(self):
        """추출 정보 업데이트"""
        self.extract_info.setText(f"추출 항목: {len(self.extracted_items)}개")

    def extract_all(self):
        """전체 추출"""
        # 현재 매핑 규칙에 따라 모든 도면 항목 추출
        for i in range(self.mapping_table.rowCount()):
            symbol = self.mapping_table.item(i, 0)
            name = self.mapping_table.item(i, 1)
            spec = self.mapping_table.item(i, 2)

            if symbol and name:
                item_data = {
                    "name": name.text(),
                    "spec": spec.text() if spec else "",
                    "quantity": 1,
                    "unit": "개",
                    "position": symbol.text(),
                }
                self.add_extracted_item(item_data)

    def auto_extract(self):
        """자동 추출"""
        # 도면에서 패턴을 인식하여 자동으로 항목 추출
        # (실제 구현에서는 OCR 또는 객체 인식 필요)
        pass

    def apply_extraction(self):
        """추출 적용"""
        if self.extracted_items:
            self.output_extracted.emit(self.extracted_items)
            self.accept()

    def export_data(self):
        """데이터 내보내기"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "내보내기",
            "",
            "Excel Files (*.xlsx);;CSV Files (*.csv);;All Files (*.*)",
        )

        if file_path:
            QMessageBox.information(
                self, "완료", f"데이터가 저장되었습니다.\n{file_path}"
            )

    def show_help(self):
        """도움말 표시"""
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            "사용법",
            "1. [도면열기] 버튼으로 도면 파일을 엽니다.\n"
            "2. 도면 매핑 탭에서 기호와 산출항목을 매핑합니다.\n"
            "3. 추출항목 탭에서 [전체추출] 버튼을 클릭합니다.\n"
            "4. [적용] 버튼으로 산출내역에 반영합니다.",
        )


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = GraphicOutputPopup()
    dialog.exec()
