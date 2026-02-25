# -*- coding: utf-8 -*-
"""
PDF 도면 뷰어 (CAD 스타일)
- 마우스 휠 줌 인/아웃
- 드래그로 패닝
- 선/사각형 그리기
- 크로스헤어 커서
"""
from typing import List
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene,
    QGraphicsLineItem, QGraphicsRectItem,
)
from PyQt6.QtCore import Qt, QLineF, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QPen, QBrush, QColor, QCursor, QPainter,
)
from .pdf_models import DrawingElement


class PDFGraphicsView(QGraphicsView):
    """PDF 도면 표시 및 그리기용 그래픽스 뷰"""

    # 줌 레벨 변경 시그널
    zoom_changed = pyqtSignal(int)  # 퍼센트
    # 페이지 변경 요청 시그널 (-1=이전, +1=다음)
    page_change_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # 렌더링 품질
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # CAD 스타일 설정
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        # 배경색 (CAD 스타일 어두운 배경)
        self.setBackgroundBrush(QBrush(QColor("#2D2D30")))

        # 그리기 상태
        self.drawing_mode = None  # None | "line" | "rect"
        self.drawing_items: list = []
        self.current_item = None
        self.temp_points: list = []
        self.current_pen = QPen(QColor("#FF0000"), 3)
        self.current_pen.setCosmetic(True)  # 줌에 영향 안 받는 선 굵기

        # 줌 범위
        self._zoom_factor = 1.0
        self._min_zoom = 0.05
        self._max_zoom = 20.0

    def wheelEvent(self, event):
        """마우스 휠 처리
        - Ctrl + 휠: 줌 인/아웃
        - 일반 휠: 페이지 넘김 (위=이전, 아래=다음)
        """
        modifiers = event.modifiers()
        delta = event.angleDelta().y()

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # ── Ctrl + 휠: 줌 ──
            factor = 1.15
            if delta > 0:
                if self._zoom_factor * factor <= self._max_zoom:
                    self.scale(factor, factor)
                    self._zoom_factor *= factor
            else:
                if self._zoom_factor / factor >= self._min_zoom:
                    self.scale(1.0 / factor, 1.0 / factor)
                    self._zoom_factor /= factor
            self.zoom_changed.emit(int(self._zoom_factor * 100))
        else:
            # ── 일반 휠: 페이지 넘김 ──
            if delta > 0:
                self.page_change_requested.emit(-1)  # 이전 페이지
            elif delta < 0:
                self.page_change_requested.emit(+1)  # 다음 페이지

    def set_drawing_mode(self, mode, color="#FF0000"):
        """그리기 모드 설정"""
        self.drawing_mode = mode
        if mode:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
            if isinstance(color, str):
                self.current_pen = QPen(QColor(f"#{color}" if not color.startswith("#") else color), 3)
            self.current_pen.setCosmetic(True)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def mousePressEvent(self, event):
        """마우스 클릭 - 그리기 시작"""
        if self.drawing_mode and event.button() == Qt.MouseButton.LeftButton:
            pos = self.mapToScene(event.pos())

            if self.drawing_mode == "line":
                line = QLineF(pos, pos)
                self.current_item = QGraphicsLineItem(line)
                self.current_item.setPen(self.current_pen)
                self.scene.addItem(self.current_item)
                self.drawing_items.append(self.current_item)

            elif self.drawing_mode == "rect":
                self.current_item = QGraphicsRectItem(QRectF(pos, pos))
                self.current_item.setPen(self.current_pen)
                self.current_item.setBrush(QBrush(QColor(255, 0, 0, 30)))
                self.scene.addItem(self.current_item)
                self.drawing_items.append(self.current_item)

            # 부모의 mousePressEvent 호출하지 않아 드래그 방지
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
                new_rect = QRectF(top_left, pos).normalized()
                self.current_item.setRect(new_rect)

            return

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
                new_rect = QRectF(top_left, pos).normalized()
                self.current_item.setRect(new_rect)

            self.current_item = None
            return

        super().mouseReleaseEvent(event)

    def clear_drawings(self):
        """그리기 요소 모두 삭제"""
        for item in self.drawing_items:
            self.scene.removeItem(item)
        self.drawing_items.clear()
        self.temp_points.clear()

    def fit_to_view(self):
        """화면에 맞추기"""
        if self.scene.items():
            self.fitInView(
                self.scene.sceneRect(),
                Qt.AspectRatioMode.KeepAspectRatio
            )
            self._zoom_factor = self.transform().m11()
            self.zoom_changed.emit(int(self._zoom_factor * 100))

    def reset_zoom(self):
        """줌 초기화 (100%)"""
        self.resetTransform()
        self._zoom_factor = 1.0
        self.zoom_changed.emit(100)

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
                    color=str(item.pen().color().name()),
                    line_width=item.pen().widthF(),
                    label=f"선 {i + 1}",
                    quantity=length / 1000.0,
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
                    quantity=rect.width() * rect.height() / 1000000.0,
                    unit="m²",
                )
                elements.append(element)
        return elements
