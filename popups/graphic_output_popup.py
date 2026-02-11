# -*- coding: utf-8 -*-
"""
PDF 산출 시스템 (PDF Output System)
PDF 도면에서 직접 산출 항목을 선택하고 수량을 산정하는 시스템

기능:
- PDF 벡터 렌더링 및 표시
- 도면에 직접 선 그리기 (터파기, 배관, TRAY, DUCT, Raceway 등)
- 산출 유형별 수량 자동 계산
- 선택 영역의 거리/면적 측정
- 산출 항목 리스트 생성

산출 유형:
- 터파기(지중): 토목 터파기 공법
- 배관: 전선관/배관 공법
- TRAY: 케이블 트레이 시스템
- DUCT: 덕트 공업
- Raceway: 레이스웨이 시스템
- 매몰(Concrete): 콘크리트 매몰 공법
- 현관(Exposed): 노출 공법

참고: egManual.pdf p181-199
"""

from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
import math
import json
import os

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
    QGraphicsView,
    QGraphicsScene,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsPathItem,
    QGraphicsEllipseItem,
    QGraphicsTextItem,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QWidget,
    QStackedWidget,
    QToolBar,
    QToolButton,
    QSpinBox,
    QDoubleSpinBox,
    QRadioButton,
    QButtonGroup,
    QMessageBox,
    QFileDialog,
    QColorDialog,
)
from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QPointF,
    QLineF,
    QRectF,
    QSize,
    QTimer,
)
from PyQt6.QtGui import (
    QFont,
    QColor,
    QPen,
    QBrush,
    QPainter,
    QPainterPath,
    QTransform,
    QPixmap,
    QImage,
    QCursor,
)

# PDF 렌더링 시도
try:
    from PyQt6.QtPdf import QPdfDocument
    from PyQt6.QtPdfWidgets import QPdfView

    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("[WARN] PyQt6.Pdf 미설치: pip install PyQt6-PyQt6-Pdf")


@dataclass
class DrawingElement:
    """도면 요소 데이터 클래스"""

    element_type: str  # 'line', 'rect', 'circle', 'path', 'text'
    points: List[QPointF] = field(default_factory=list)
    start_point: Optional[QPointF] = None
    end_point: Optional[QPointF] = None
    width: float = 0.0  # 선의 경우 길이, 면의 경우 폭
    height: float = 0.0
    area: float = 0.0
    length: float = 0.0  # 총 연장
    color: str = "#000000"
    line_width: float = 2.0
    label: str = ""
    notes: str = ""
    quantity: float = 0.0
    unit: str = "m"


@dataclass
class OutputItem:
    """산출 항목"""

    id: int
    output_type: str  # '터파기', '배관', 'TRAY', 'DUCT', 'Raceway', '매몰', '현관'
    location: str  # 위치/구간
    specification: str  # 규격
    length: float  # 연장 (m)
    width: float = 0.0  # 폭 (m)
    depth: float = 0.0  # 깊이 (m)
    area: float = 0.0  # 면적 (㎡)
    quantity: float = 0.0  # 수량
    unit: str = "m³"  # 단위
    notes: str = ""


class PDFGraphicsView(QGraphicsView):
    """PDF 도면 표시 및 그리기용 그래픽스 뷰"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # 줌/패닝 설정
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 그리기 모드
        self.drawing_mode = None  # 'line', 'rect', 'polyline'
        self.drawing_items = []
        self.current_pen = QPen(QColor("#FF0000"), 2)
        self.current_item = None
        self.temp_points = []

        # 배경
        self.setBackgroundBrush(QColor("#F5F5F5"))

        # 확대/축소
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0

    def wheelEvent(self, event):
        """마우스 휠로 줌 인/아웃"""
        zoom_in = event.angleDelta().y() > 0
        factor = 1.1 if zoom_in else 0.9

        new_zoom = self.zoom_factor * factor
        if self.min_zoom <= new_zoom <= self.max_zoom:
            self.zoom_factor = new_zoom
            self.scale(factor, factor)

    def set_drawing_mode(self, mode: str, color: str = "#FF0000"):
        """그리기 모드 설정"""
        self.drawing_mode = mode
        self.temp_points = []
        self.current_pen = QPen(QColor(color), 2)
        if mode:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def mousePressEvent(self, event):
        """마우스 클릭 - 그리기 시작"""
        if self.drawing_mode and event.button() == Qt.MouseButton.LeftButton:
            pos = self.mapToScene(event.pos())
            self.temp_points.append(pos)

            if self.drawing_mode == "line":
                # 선 그리기 시작
                self.current_item = QGraphicsLineItem(QLineF(pos, pos))
                self.current_item.setPen(self.current_pen)
                self.scene.addItem(self.current_item)
                self.drawing_items.append(self.current_item)

            elif self.drawing_mode == "rect":
                # 사각형 그리기 시작
                self.current_item = QGraphicsRectItem(QRectF(pos, pos))
                self.current_item.setPen(self.current_pen)
                self.current_item.setBrush(QBrush(QColor(255, 0, 0, 30)))
                self.scene.addItem(self.current_item)
                self.drawing_items.append(self.current_item)

            super().mousePressEvent(event)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """마우스 이동 - 그리기 실시간 표시"""
        if self.drawing_mode and self.current_item:
            pos = self.mapToScene(event.pos())

            if self.drawing_mode == "line":
                line = self.current_item.line()
                line.setP2(pos)
                self.current_item.setLine(line)

            elif self.drawing_mode == "rect":
                rect = self.current_item.rect()
                top_left = rect.topLeft()
                bottom_right = pos
                rect = QRectF(top_left, bottom_right).normalized()
                self.current_item.setRect(rect)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """마우스 릴리즈 - 그리기 완료"""
        if self.drawing_mode and self.current_item:
            pos = self.mapToScene(event.pos())

            if self.drawing_mode == "line":
                line = self.current_item.line()
                line.setP2(pos)
                self.current_item.setLine(line)

            elif self.drawing_mode == "rect":
                rect = self.current_item.rect()
                top_left = rect.topLeft()
                bottom_right = pos
                rect = QRectF(top_left, bottom_right).normalized()
                self.current_item.setRect(rect)

            self.current_item = None

        super().mouseReleaseEvent(event)

    def clear_drawings(self):
        """그리기 요소 모두 삭제"""
        for item in self.drawing_items:
            self.scene.removeItem(item)
        self.drawing_items.clear()
        self.temp_points.clear()

    def get_drawing_elements(self) -> List[DrawingElement]:
        """그리기 요소 목록 반환"""
        elements = []

        for i, item in enumerate(self.drawing_items):
            if isinstance(item, QGraphicsLineItem):
                line = item.line()
                length = line.length()

                element = DrawingElement(
                    element_type="line",
                    start_point=line.p1(),
                    end_point=line.p2(),
                    length=length,
                    width=0.0,
                    area=0.0,
                    color=str(item.pen().color().name()),
                    line_width=item.pen().widthF(),
                    label=f"선 {i + 1}",
                    quantity=length / 1000.0,  # mm를 m로 변환
                    unit="m",
                )
                elements.append(element)

            elif isinstance(item, QGraphicsRectItem):
                rect = item.rect()

                element = DrawingElement(
                    element_type="rect",
                    start_point=rect.topLeft(),
                    end_point=rect.bottomRight(),
                    width=rect.width(),
                    height=rect.height(),
                    area=rect.width() * rect.height(),
                    length=2 * (rect.width() + rect.height()),
                    color=str(item.pen().color().name()),
                    line_width=item.pen().widthF(),
                    label=f"사각형 {i + 1}",
                    quantity=rect.width()
                    * rect.height()
                    / 1000000.0,  # mm²를 m²로 변환
                    unit="m²",
                )
                elements.append(element)

        return elements


class PDFOutputPopup(QDialog):
    """
    PDF 산출 팝업
    PDF 도면에서 산출 항목을 직접 선택하고 수량 산정
    """

    closed = pyqtSignal(dict)  # 산출 데이터 반환

    # 산출 유형 정의
    OUTPUT_TYPES = {
        "터파기(지중)": {
            "icon": "🕳️",
            "unit": "m³",
            "color": "#8B4513",
            "default_depth": 0.8,  # 기본 깊이 800mm
            "description": "토목 터파기 공법",
        },
        "배관": {
            "icon": "🔧",
            "unit": "m",
            "color": "#4682B4",
            "default_depth": 0.0,
            "description": "전선관/배관 시스템",
        },
        "TRAY": {
            "icon": "📐",
            "unit": "m",
            "color": "#708090",
            "default_depth": 0.0,
            "description": "케이블 트레이 시스템",
        },
        "DUCT": {
            "icon": "🌪️",
            "unit": "m",
            "color": "#DEB887",
            "default_depth": 0.0,
            "description": "덕트 공업 시스템",
        },
        "Raceway": {
            "icon": "🔲",
            "unit": "m",
            "color": "#6B8E23",
            "default_depth": 0.0,
            "description": "레이스웨이 시스템",
        },
        "매몰(Concrete)": {
            "icon": "🧱",
            "unit": "m³",
            "color": "#A9A9A9",
            "default_depth": 0.1,
            "description": "콘크리트 매몰 공법",
        },
        "현관(Exposed)": {
            "icon": "🏗️",
            "unit": "m",
            "color": "#B8860B",
            "default_depth": 0.0,
            "description": "노출 공법",
        },
    }

    def __init__(self, parent=None, eulji_data: dict = None):
        super().__init__(parent)
        self.setWindowTitle("PDF 산출 시스템")
        self.setMinimumSize(1400, 900)

        self.eulji_data = eulji_data or {}
        self.current_pdf_path = None
        self.pdf_document = None
        self.output_items = []
        self.item_counter = 0

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """UI 초기화"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # 1. 상단 툴바
        toolbar = self.create_toolbar()
        main_layout.addWidget(toolbar)

        # 2. 메인 스플리터
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 좌측: PDF 뷰어 (대형)
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)

        # PDF 뷰어
        self.pdf_view = PDFGraphicsView()
        left_layout.addWidget(self.pdf_view)

        # 확대/축소 컨트롤
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(5)

        self.zoom_out_btn = QPushButton("🔍-")
        self.zoom_out_btn.setFixedSize(30, 25)
        zoom_layout.addWidget(self.zoom_out_btn)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zoom_layout.addWidget(self.zoom_label)

        self.zoom_in_btn = QPushButton("🔍+")
        self.zoom_in_btn.setFixedSize(30, 25)
        zoom_layout.addWidget(self.zoom_in_btn)

        self.fit_btn = QPushButton("맞춤")
        self.fit_btn.setFixedSize(50, 25)
        zoom_layout.addWidget(self.fit_btn)

        zoom_layout.addStretch()
        left_layout.addLayout(zoom_layout)

        splitter.addWidget(left_frame)

        # 중앙: 산출 유형 및 설정
        center_frame = QFrame()
        center_frame.setFixedWidth(280)
        center_layout = QVBoxLayout(center_frame)
        center_layout.setSpacing(5)

        # 산출 유형 선택
        type_group = QGroupBox("산출 유형 선택")
        type_layout = QVBoxLayout()
        type_layout.setSpacing(3)

        self.type_button_group = QButtonGroup()

        for output_type, info in self.OUTPUT_TYPES.items():
            radio = QRadioButton(f"{info['icon']} {output_type}")
            radio.setData(output_type)
            radio.setToolTip(info["description"])
            self.type_button_group.addButton(radio)
            type_layout.addWidget(radio)

        # 기본 선택: 배관
        type_layout.addStretch()
        type_group.setLayout(type_layout)
        center_layout.addWidget(type_group)

        # 깊이/규격 설정
        depth_group = QGroupBox("설정")
        depth_layout = QVBoxLayout()
        depth_layout.setSpacing(5)

        # 깊이 (터파기/매몰용)
        depth_layout.addWidget(QLabel("깊이 (m):"))
        self.depth_spin = QDoubleSpinBox()
        self.depth_spin.setRange(0, 10)
        self.depth_spin.setDecimals(2)
        self.depth_spin.setValue(0.8)
        self.depth_spin.setSuffix(" m")
        depth_layout.addWidget(self.depth_spin)

        # 폭 (터파기용)
        depth_layout.addWidget(QLabel("폭 (m):"))
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0, 10)
        self.width_spin.setDecimals(2)
        self.width_spin.setValue(0.6)
        self.width_spin.setSuffix(" m")
        depth_layout.addWidget(self.width_spin)

        # 규격
        depth_layout.addWidget(QLabel("규격:"))
        self.spec_combo = QComboBox()
        self.spec_combo.setEditable(True)
        self.spec_combo.addItems(
            [
                "50A",
                "65A",
                "80A",
                "100A",
                "125A",
                "150A",  # 배관
                "100mm",
                "150mm",
                "200mm",
                "300mm",  # TRAY/DUCT
                "50x50",
                "100x50",
                "100x100",  # Raceway
            ]
        )
        depth_layout.addWidget(self.spec_combo)

        # 위치/구간
        depth_layout.addWidget(QLabel("위치/구간:"))
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("예: 1층 전등동")
        depth_layout.addWidget(self.location_edit)

        center_layout.addWidget(depth_group)

        # 그리기 도구
        draw_group = QGroupBox("그리기 도구")
        draw_layout = QVBoxLayout()
        draw_layout.setSpacing(3)

        # 색상 선택
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("색상:"))
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(30, 25)
        self.color_btn.setStyleSheet(
            f"background-color: {self.OUTPUT_TYPES['배관']['color']};"
        )
        self.color_btn.clicked.connect(self.select_color)
        color_layout.addWidget(self.color_btn)

        # 선 굵기
        color_layout.addWidget(QLabel("굵기:"))
        self.line_width_spin = QSpinBox()
        self.line_width_spin.setRange(1, 10)
        self.line_width_spin.setValue(3)
        self.line_width_spin.setSuffix("px")
        color_layout.addWidget(self.line_width_spin)
        color_layout.addStretch()
        draw_layout.addLayout(color_layout)

        # 선 그리기
        self.draw_line_btn = QPushButton("━ 선 그리기")
        self.draw_line_btn.setCheckable(True)
        draw_layout.addWidget(self.draw_line_btn)

        # 사각형 그리기
        self.draw_rect_btn = QPushButton("▢ 면 그리기")
        self.draw_rect_btn.setCheckable(True)
        draw_layout.addWidget(self.draw_rect_btn)

        # 지우기
        self.clear_btn = QPushButton("🗑️ 모두 지우기")
        draw_layout.addWidget(self.clear_btn)

        draw_layout.addStretch()
        draw_group.setLayout(draw_layout)
        center_layout.addWidget(draw_group)

        # 현재 선택 항목 수
        self.selection_count_label = QLabel("선택: 0개")
        self.selection_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.selection_count_label)

        splitter.addWidget(center_frame)

        # 우측: 산출 목록
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 산출 목록 테이블
        right_layout.addWidget(QLabel("<b>산출 목록</b>"))

        self.output_table = QTableWidget()
        self.output_table.setColumnCount(7)
        self.output_table.setHorizontalHeaderLabels(
            ["구분", "유형", "위치", "규격", "연장(m)", "수량", "단위"]
        )
        self.output_table.horizontalHeader().setStretchLastSection(True)
        self.output_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.output_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # 그리드 스타일 적용
        self.setup_table_style()

        right_layout.addWidget(self.output_table)

        # 하단 버튼
        btn_layout = QHBoxLayout()

        self.delete_btn = QPushButton("🗑️ 삭제")
        btn_layout.addWidget(self.delete_btn)

        self.clear_all_btn = QPushButton("🗑️ 전체 삭제")
        btn_layout.addWidget(self.clear_all_btn)

        btn_layout.addStretch()

        self.export_btn = QPushButton("📤 산출 적용")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
            }
        """)
        btn_layout.addWidget(self.export_btn)

        right_layout.addLayout(btn_layout)

        splitter.addWidget(right_frame)

        # 초기 분할 비율
        splitter.setSizes([900, 280, 400])

        main_layout.addWidget(splitter)

    def setup_table_style(self):
        """테이블 그리드 스타일 적용"""
        # 행 높이
        self.output_table.verticalHeader().setDefaultSectionSize(22)
        self.output_table.verticalHeader().setVisible(True)

        # 행 번호 스타일
        self.output_table.verticalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #e1e1e1;
                color: black;
                padding: 2px;
                border: 1px solid #707070;
                font-family: '굴림';
                font-size: 10pt;
            }
        """)

        # 헤더 스타일
        self.output_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #4a90d9;
                color: white;
                padding: 4px;
                border: 1px solid #2c5aa0;
                font-family: '굴림';
                font-weight: bold;
                font-size: 10pt;
            }
        """)

        # 교대 행 색상
        self.output_table.setAlternatingRowColors(True)
        self.output_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #cccccc;
                font-family: '굴림체';
                font-size: 10pt;
            }
            QTableWidget::item:selected {
                background-color: #b3d9ff;
            }
        """)

    def create_toolbar(self):
        """상단 툴바 생성"""
        toolbar = QFrame()
        toolbar.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border-bottom: 1px solid #cccccc;
                padding: 3px;
            }
        """)
        layout = QHBoxLayout(toolbar)
        layout.setSpacing(5)

        # PDF 열기
        self.open_pdf_btn = QPushButton("📂 PDF 열기")
        layout.addWidget(self.open_pdf_btn)

        layout.addSpacing(10)

        # 페이지 네비게이션
        layout.addWidget(QLabel("페이지:"))
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 100)
        self.page_spin.setValue(1)
        self.page_spin.setFixedWidth(50)
        layout.addWidget(self.page_spin)
        self.page_spin.valueChanged.connect(self.go_to_page)

        self.page_label = QLabel("/ 1")
        layout.addWidget(self.page_label)

        layout.addStretch()

        # 통계
        self.total_length_label = QLabel("총 연장: 0m")
        self.total_length_label.setStyleSheet("font-weight: bold; color: #333;")
        layout.addWidget(self.total_length_label)

        self.total_qty_label = QLabel("총 수량: 0")
        self.total_qty_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        layout.addWidget(self.total_qty_label)

        return toolbar

    def setup_connections(self):
        """시그널 연결"""
        self.open_pdf_btn.clicked.connect(self.open_pdf)

        # 그리기 버튼 그룹
        self.draw_line_btn.toggled.connect(self.on_draw_line_toggled)
        self.draw_rect_btn.toggled.connect(self.on_draw_rect_toggled)

        self.clear_btn.clicked.connect(self.pdf_view.clear_drawings)

        self.delete_btn.clicked.connect(self.delete_selected)
        self.clear_all_btn.clicked.connect(self.clear_all)

        self.export_btn.clicked.connect(self.export_output)

        # 깊이/폭 변경 시 업데이트
        self.depth_spin.valueChanged.connect(self.update_selected_items)
        self.width_spin.valueChanged.connect(self.update_selected_items)
        self.spec_combo.currentTextChanged.connect(self.update_selected_items)
        self.location_edit.textChanged.connect(self.update_selected_items)

    def open_pdf(self):
        """PDF 파일 열기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "PDF 도면 열기", "", "PDF Files (*.pdf);;All Files (*.*)"
        )

        if file_path:
            self.load_pdf(file_path)

    def load_pdf(self, file_path: str):
        """PDF 로드 및 표시"""
        if not PDF_SUPPORT:
            QMessageBox.warning(
                self,
                "PDF 미지원",
                "PyQt6.Pdf 라이브러리가 설치되지 않았습니다.\n"
                "pip install PyQt6-PyQt6-Pdf 을 실행하세요.",
            )
            return

        try:
            self.current_pdf_path = file_path
            self.pdf_document = QPdfDocument()
            self.pdf_document.load(file_path)

            # 페이지 수
            page_count = self.pdf_document.pageCount()
            self.page_spin.setRange(1, page_count)
            self.page_label.setText(f"/ {page_count}")

            # 첫 페이지 표시
            self.go_to_page(1)

            QMessageBox.information(
                self,
                "PDF 열기 완료",
                f"PDF 파일이 로드되었습니다.\n{file_path.split('/')[-1]}",
            )

        except Exception as e:
            QMessageBox.critical(
                self, "PDF 로드 오류", f"PDF 파일을 열 수 없습니다.\n\n오류: {str(e)}"
            )

    def go_to_page(self, page_num: int):
        """지정 페이지로 이동"""
        if not self.pdf_document:
            return

        # PDF 페이지 렌더링 (QImage 사용)
        try:
            page = self.pdf_document.page(page_num - 1)
            if page:
                # 페이지 크기
                page_size = page.pageSize()
                scale = 1.0

                # 픽셀 단위로 변환 (96 DPI)
                width = int(page_size.width() * scale)
                height = int(page_size.height() * scale)

                # QImage 생성
                image = QImage(width, height, QImage.Format.Format_ARGB32)
                image.fill(Qt.GlobalColor.white)

                # PDF 렌더링
                painter = QPainter(image)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

                transform = QTransform()
                transform.scale(scale, scale)
                painter.setWorldTransform(transform)

                page.render(painter)
                painter.end()

                # GraphicsScene에 표시
                self.pdf_view.scene.clear()
                pixmap = QPixmap.fromImage(image)
                self.pdf_view.scene.addPixmap(pixmap)
                self.pdf_view.scene.setSceneRect(pixmap.rect())

                # PDF 정보 업데이트
                info = f"{width}x{height}px (Page {page_num})"

        except Exception as e:
            print(f"[ERROR] PDF 페이지 렌더링 오류: {e}")
            # 폴백: 흰 배경
            self.pdf_view.scene.clear()
            self.pdf_view.scene.addRect(
                QRectF(0, 0, 800, 1100),
                QPen(Qt.GlobalColor.black),
                QBrush(Qt.GlobalColor.white),
            )

    def select_color(self):
        """색상 선택 대화상자"""
        color = QColorDialog.getColor(QColor("#FF0000"), self, "선 색상 선택")
        if color.isValid():
            hex_color = color.name()
            self.color_btn.setStyleSheet(f"background-color: {hex_color};")
            self.pdf_view.current_pen = QPen(color, self.line_width_spin.value())

    def on_draw_line_toggled(self, checked: bool):
        """선 그리기 버튼 토글"""
        if checked:
            self.draw_rect_btn.setChecked(False)
            self.pdf_view.set_drawing_mode(
                "line", self.color_btn.styleSheet().split("#")[1][:6]
            )
        elif not self.draw_rect_btn.isChecked():
            self.pdf_view.set_drawing_mode(None)

    def on_draw_rect_toggled(self, checked: bool):
        """면 그리기 버튼 토글"""
        if checked:
            self.draw_line_btn.setChecked(False)
            self.pdf_view.set_drawing_mode(
                "rect", self.color_btn.styleSheet().split("#")[1][:6]
            )
        elif not self.draw_line_btn.isChecked():
            self.pdf_view.set_drawing_mode(None)

    def update_output_table(self):
        """산출 목록 테이블 업데이트"""
        self.output_table.setRowCount(len(self.output_items))

        total_length = 0.0
        total_qty = 0.0

        for row, item in enumerate(self.output_items):
            # 구분
            self.output_table.setItem(row, 0, QTableWidgetItem(f"{row + 1}"))

            # 유형
            type_info = self.OUTPUT_TYPES.get(item.output_type, {})
            icon = type_info.get("icon", "")
            self.output_table.setItem(
                row, 1, QTableWidgetItem(f"{icon} {item.output_type}")
            )

            # 위치
            self.output_table.setItem(row, 2, QTableWidgetItem(item.location))

            # 규격
            self.output_table.setItem(row, 3, QTableWidgetItem(item.specification))

            # 연장
            self.output_table.setItem(row, 4, QTableWidgetItem(f"{item.length:.2f}"))

            # 수량
            self.output_table.setItem(row, 5, QTableWidgetItem(f"{item.quantity:.3f}"))

            # 단위
            self.output_table.setItem(row, 6, QTableWidgetItem(item.unit))

            total_length += item.length
            total_qty += item.quantity

        # 통계 업데이트
        self.selection_count_label.setText(f"선택: {len(self.output_items)}개")
        self.total_length_label.setText(f"총 연장: {total_length:.2f}m")
        self.total_qty_label.setText(f"총 수량: {total_qty:.3f}")

    def delete_selected(self):
        """선택 항목 삭제"""
        selected_rows = set(item.row() for item in self.output_table.selectedIndexes())

        if not selected_rows:
            QMessageBox.warning(self, "경고", "삭제할 항목을 선택하세요.")
            return

        # 선택된 행 삭제 (내림차순으로)
        for row in sorted(selected_rows, reverse=True):
            if row < len(self.output_items):
                self.output_items.pop(row)

        self.update_output_table()

    def clear_all(self):
        """모두 삭제"""
        if (
            QMessageBox.question(
                self,
                "확인",
                "모든 산출 항목을 삭제하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.output_items.clear()
            self.item_counter = 0
            self.pdf_view.clear_drawings()
            self.update_output_table()

    def update_selected_items(self):
        """선택 항목의 깊이/규격 업데이트"""
        selected_rows = set(item.row() for item in self.output_table.selectedIndexes())

        for row in selected_rows:
            if row < len(self.output_items):
                item = self.output_items[row]
                item.depth = self.depth_spin.value()
                item.width = self.width_spin.value()
                item.specification = self.spec_combo.currentText()
                item.location = self.location_edit.text()

                # 수량 재계산
                if item.output_type in ["터파기(지중)", "매몰(Concrete)"]:
                    # 체적 = 폭 × 깊이 × 연장
                    item.quantity = item.width * item.depth * item.length
                    item.unit = "m³"
                else:
                    # 단순 연장
                    item.quantity = item.length
                    item.unit = "m"

        self.update_output_table()

    def export_output(self):
        """산출 적용"""
        if not self.output_items:
            QMessageBox.warning(self, "경고", "산출할 항목이 없습니다.")
            return

        # 산출 데이터 구성
        result = {
            "items": [
                {
                    "id": item.id,
                    "output_type": item.output_type,
                    "location": item.location,
                    "specification": item.specification,
                    "length": item.length,
                    "width": item.width,
                    "depth": item.depth,
                    "area": item.area,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "notes": item.notes,
                }
                for item in self.output_items
            ],
            "total_length": sum(item.length for item in self.output_items),
            "total_quantity": sum(item.quantity for item in self.output_items),
        }

        # 시그널 발생
        self.closed.emit(result)

        QMessageBox.information(
            self,
            "완료",
            f"산출이 적용되었습니다.\n"
            f"총 {len(self.output_items)}개 항목\n"
            f"총 연장: {result['total_length']:.2f}m\n"
            f"총 수량: {result['total_quantity']:.3f}",
        )

        self.accept()


# 단독 실행 테스트
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    dialog = PDFOutputPopup()
    dialog.show()

    sys.exit(app.exec())
