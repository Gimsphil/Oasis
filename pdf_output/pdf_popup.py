# -*- coding: utf-8 -*-
"""
PDF 산출 시스템 - CAD 스타일 메인 팝업
====================================
레이아웃 (사이드 패널 없음, 전체 너비 뷰어):
┌──────────────────────────────────────────────────────────────┐
│ 파일(F) │ 편집(E) │ 보기(V) │ 도구(T) │ 도움말(H)             │
├──────────────────────────────────────────────────────────────┤
│ 📂열기│◀ 1/1 ▶│🔍− 100% 🔍+ 맞춤│━선 ▢면│🎨│굵기│🗑│연장 수량│
├──────────────────────────────────────────────────────────────┤
│ 유형:[배관▼] 깊이:[0.80] 폭:[0.60] 규격:[50A▼] 위치:[    ]  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│              PDF 도면 뷰어 (전체 너비, 최대 높이)              │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ 📋산출목록 #│유형│위치│규격│연장│수량│단위│ [삭제][전체삭제][적용]│
├──────────────────────────────────────────────────────────────┤
│ 파일:(없음) │ 줌: 100% │ 페이지: 1/1                         │
└──────────────────────────────────────────────────────────────┘
"""
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QMenuBar, QFrame,
    QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QLabel, QLineEdit,
    QSpinBox, QDoubleSpinBox,
    QMessageBox, QFileDialog, QColorDialog,
    QAbstractItemView, QWidget,
    QGraphicsTextItem, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QSize
from PyQt6.QtGui import QFont, QColor, QPen, QBrush, QPixmap, QKeySequence, QAction

from .pdf_viewer import PDFGraphicsView
from .pdf_models import OutputItem

# PDF 렌더링 지원 확인
try:
    from PyQt6.QtPdf import QPdfDocument
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("[WARN] PyQt6.QtPdf 미설치: pip install PyQt6-Pdf")


# 공통 버튼 스타일
BTN_STYLE = """
    QPushButton {
        background-color: #f5f5f5; border: 1px solid #999;
        border-radius: 2px; padding: 2px 7px;
        font-family: '새굴림'; font-size: 10pt; min-height: 22px;
    }
    QPushButton:hover { background-color: #ddeeff; border-color: #6699cc; }
    QPushButton:pressed { background-color: #bbddff; }
    QPushButton:checked { background-color: #cce5ff; border-color: #3399ff; font-weight: bold; }
"""

LABEL_STYLE = "font-family: '새굴림'; font-size: 9pt; color: #555;"


class PDFOutputPopup(QDialog):
    """
    CAD 스타일 PDF 산출 팝업
    PDF 도면에서 산출 항목을 직접 선택하고 수량 산정
    """

    closed = pyqtSignal(dict)

    # 산출 유형 정의
    OUTPUT_TYPES = {
        "터파기(지중)": {"icon": "🕳️", "unit": "m³", "color": "#8B4513", "default_depth": 0.8},
        "배관":        {"icon": "🔧", "unit": "m",  "color": "#4682B4", "default_depth": 0.0},
        "TRAY":        {"icon": "📐", "unit": "m",  "color": "#708090", "default_depth": 0.0},
        "DUCT":        {"icon": "🌪️", "unit": "m",  "color": "#DEB887", "default_depth": 0.0},
        "Raceway":     {"icon": "🔲", "unit": "m",  "color": "#6B8E23", "default_depth": 0.0},
        "매몰(Concrete)": {"icon": "🧱", "unit": "m³", "color": "#A9A9A9", "default_depth": 0.1},
        "현관(Exposed)":  {"icon": "🏗️", "unit": "m",  "color": "#B8860B", "default_depth": 0.0},
    }

    def __init__(self, parent=None, eulji_data: dict = None):
        super().__init__(parent)
        self.setWindowTitle("PDF 산출 시스템")
        self.setMinimumSize(900, 600)
        self.resize(1400, 900)

        # 전체화면/최대화 지원
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )

        # 상태
        self.eulji_data = eulji_data or {}
        self.current_pdf_path = None
        self.pdf_document = None
        self.output_items = []
        self.item_counter = 0
        self.current_color = "#FF0000"

        self._setup_ui()

    # ═══════════════════════════════ UI 구성 ═══════════════════════════════

    def _setup_ui(self):
        """전체 UI 구성 (수직 레이아웃, 사이드 패널 없음)"""
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # 1. 메뉴 바 (고정 높이)
        self._create_menu_bar(main)

        # 2. 툴바 (고정 높이)
        self._create_toolbar(main)

        # 3. 설정 바 - 산출 유형/깊이/폭/규격/위치 (한 줄)
        self._create_settings_bar(main)

        # 4. PDF 뷰어 + 하단 산출목록 (수직 스플리터)
        self._create_viewer_and_table(main)

        # 5. 상태 바 (고정 높이)
        self._create_status_bar(main)

    # ─────────────────── 1. 메뉴 바 ───────────────────

    def _create_menu_bar(self, layout):
        """메뉴 바"""
        mb = QMenuBar(self)
        mb.setFixedHeight(26)
        mb.setStyleSheet("""
            QMenuBar {
                background: #f0f0f0; border-bottom: 1px solid #ccc;
                font-family: '새굴림'; font-size: 11pt; padding: 1px;
            }
            QMenuBar::item { padding: 3px 10px; background: transparent; }
            QMenuBar::item:selected { background: #e0e0e0; }
            QMenu { font-family: '새굴림'; font-size: 11pt; }
            QMenu::item { padding: 5px 30px 5px 15px; }
            QMenu::item:selected { background: #0078d7; color: white; }
            QMenu::separator { height: 1px; background: #ccc; margin: 3px 5px; }
        """)

        # ─ 파일 ─
        fm = mb.addMenu("파일(&F)")
        self._add_action(fm, "📂 PDF 열기", "Ctrl+O", self._open_pdf)
        fm.addSeparator()
        self._add_action(fm, "📤 산출 적용", "Ctrl+S", self._export_output)
        fm.addSeparator()
        self._add_action(fm, "닫기", "Ctrl+W", self.close)

        # ─ 편집 ─
        em = mb.addMenu("편집(&E)")
        self._add_action(em, "🗑️ 선택 삭제", "Delete", self._delete_selected)
        self._add_action(em, "🗑️ 전체 삭제", None, self._clear_all)

        # ─ 보기 ─
        vm = mb.addMenu("보기(&V)")
        self._add_action(vm, "🔍 확대", "Ctrl++", lambda: self._zoom(1.25))
        self._add_action(vm, "🔍 축소", "Ctrl+-", lambda: self._zoom(0.8))
        self._add_action(vm, "📐 화면 맞춤", "Ctrl+0", self._fit_view)
        vm.addSeparator()
        self._add_action(vm, "◀ 이전 페이지", "PgUp", self._prev_page)
        self._add_action(vm, "▶ 다음 페이지", "PgDown", self._next_page)
        vm.addSeparator()
        self._add_action(vm, "🖥️ 전체화면", "F11", self._toggle_fullscreen)

        # ─ 도구 ─
        tm = mb.addMenu("도구(&T)")
        self.act_draw_line = QAction("━ 선 그리기", self)
        self.act_draw_line.setCheckable(True)
        self.act_draw_line.triggered.connect(self._toggle_line_draw)
        tm.addAction(self.act_draw_line)
        self.act_draw_rect = QAction("▢ 면 그리기", self)
        self.act_draw_rect.setCheckable(True)
        self.act_draw_rect.triggered.connect(self._toggle_rect_draw)
        tm.addAction(self.act_draw_rect)
        tm.addSeparator()
        self._add_action(tm, "🎨 색상 선택", None, self._select_color)
        # 그리기 지우기는 pdf_view 생성 후 연결하므로 나중에

        # ─ 도움말 ─
        hm = mb.addMenu("도움말(&H)")
        self._add_action(hm, "ℹ️ 사용법", None, self._show_help)

        layout.addWidget(mb, 0)

    # ─────────────────── 2. 툴바 ───────────────────

    def _create_toolbar(self, layout):
        """툴바 (한 줄, 32px 높이)"""
        tb = QFrame()
        tb.setFixedHeight(30)
        tb.setStyleSheet("QFrame { background: #e8e8e8; border-bottom: 1px solid #bbb; }")
        h = QHBoxLayout(tb)
        h.setContentsMargins(4, 1, 4, 1)
        h.setSpacing(2)

        # PDF 열기
        b = self._tb_btn("📂 열기", "PDF 파일 열기 (Ctrl+O)")
        b.clicked.connect(self._open_pdf)
        h.addWidget(b)

        self._sep(h)

        # 페이지 네비게이션
        b = self._tb_btn("◀", "이전 페이지")
        b.setFixedWidth(24)
        b.clicked.connect(self._prev_page)
        h.addWidget(b)

        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 1)
        self.page_spin.setFixedWidth(45)
        self.page_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_spin.setStyleSheet("font-size: 9pt;")
        self.page_spin.valueChanged.connect(self._go_to_page)
        h.addWidget(self.page_spin)

        self.page_label = QLabel("/1")
        self.page_label.setStyleSheet(LABEL_STYLE)
        h.addWidget(self.page_label)

        b = self._tb_btn("▶", "다음 페이지")
        b.setFixedWidth(24)
        b.clicked.connect(self._next_page)
        h.addWidget(b)

        self._sep(h)

        # 줌
        b = self._tb_btn("🔍−", "축소")
        b.setFixedWidth(32)
        b.clicked.connect(lambda: self._zoom(0.8))
        h.addWidget(b)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(40)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setStyleSheet(LABEL_STYLE)
        h.addWidget(self.zoom_label)

        b = self._tb_btn("🔍+", "확대")
        b.setFixedWidth(32)
        b.clicked.connect(lambda: self._zoom(1.25))
        h.addWidget(b)

        b = self._tb_btn("맞춤", "화면 맞춤 (Ctrl+0)")
        b.clicked.connect(self._fit_view)
        h.addWidget(b)

        self._sep(h)

        # 그리기
        self.btn_draw_line = self._tb_btn("━ 선", "선 그리기")
        self.btn_draw_line.setCheckable(True)
        self.btn_draw_line.toggled.connect(self._on_line_toggled)
        h.addWidget(self.btn_draw_line)

        self.btn_draw_rect = self._tb_btn("▢ 면", "면 그리기")
        self.btn_draw_rect.setCheckable(True)
        self.btn_draw_rect.toggled.connect(self._on_rect_toggled)
        h.addWidget(self.btn_draw_rect)

        self._sep(h)

        # 색상
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(20, 20)
        self.color_btn.setStyleSheet(f"background: {self.current_color}; border: 1px solid #666; border-radius: 2px;")
        self.color_btn.setToolTip("색상 선택")
        self.color_btn.clicked.connect(self._select_color)
        h.addWidget(self.color_btn)

        h.addWidget(QLabel("굵기:"))
        self.line_width_spin = QSpinBox()
        self.line_width_spin.setRange(1, 10)
        self.line_width_spin.setValue(3)
        self.line_width_spin.setSuffix("px")
        self.line_width_spin.setFixedWidth(50)
        self.line_width_spin.setStyleSheet("font-size: 9pt;")
        h.addWidget(self.line_width_spin)

        self._sep(h)

        b = self._tb_btn("🗑️ 지우기", "그리기 모두 지우기")
        b.clicked.connect(self._clear_drawings)
        h.addWidget(b)

        h.addStretch()

        # 통계 (우측)
        self.stat_length = QLabel("연장: 0m")
        self.stat_length.setStyleSheet("font-weight: bold; font-size: 10pt; color: #333; font-family: '새굴림';")
        h.addWidget(self.stat_length)
        h.addSpacing(8)
        self.stat_qty = QLabel("수량: 0")
        self.stat_qty.setStyleSheet("font-weight: bold; font-size: 10pt; color: #0066cc; font-family: '새굴림';")
        h.addWidget(self.stat_qty)

        layout.addWidget(tb, 0)

    # ─────────────────── 3. 설정 바 ───────────────────

    def _create_settings_bar(self, layout):
        """산출 유형/설정을 한 줄로 압축"""
        bar = QFrame()
        bar.setFixedHeight(30)
        bar.setStyleSheet("""
            QFrame { background: #f5f5f0; border-bottom: 1px solid #ccc; }
            QLabel { font-family: '새굴림'; font-size: 9pt; color: #444; }
            QComboBox, QDoubleSpinBox, QLineEdit {
                font-family: '새굴림'; font-size: 9pt; padding: 1px 3px; min-height: 20px;
            }
        """)
        h = QHBoxLayout(bar)
        h.setContentsMargins(6, 2, 6, 2)
        h.setSpacing(4)

        # 산출 유형 (콤보박스로 변경)
        h.addWidget(QLabel("유형:"))
        self.type_combo = QComboBox()
        self.type_combo.setFixedWidth(130)
        for t, info in self.OUTPUT_TYPES.items():
            self.type_combo.addItem(f"{info['icon']} {t}", t)
        self.type_combo.setCurrentIndex(1)  # 기본: 배관
        h.addWidget(self.type_combo)

        self._sep(h)

        # 깊이
        h.addWidget(QLabel("깊이:"))
        self.depth_spin = QDoubleSpinBox()
        self.depth_spin.setRange(0, 10)
        self.depth_spin.setDecimals(2)
        self.depth_spin.setValue(0.8)
        self.depth_spin.setSuffix("m")
        self.depth_spin.setFixedWidth(65)
        h.addWidget(self.depth_spin)

        # 폭
        h.addWidget(QLabel("폭:"))
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0, 10)
        self.width_spin.setDecimals(2)
        self.width_spin.setValue(0.6)
        self.width_spin.setSuffix("m")
        self.width_spin.setFixedWidth(65)
        h.addWidget(self.width_spin)

        self._sep(h)

        # 규격
        h.addWidget(QLabel("규격:"))
        self.spec_combo = QComboBox()
        self.spec_combo.setEditable(True)
        self.spec_combo.setFixedWidth(80)
        self.spec_combo.addItems([
            "50A", "65A", "80A", "100A", "125A", "150A",
            "100mm", "150mm", "200mm", "300mm",
            "50x50", "100x50", "100x100",
        ])
        h.addWidget(self.spec_combo)

        self._sep(h)

        # 위치
        h.addWidget(QLabel("위치:"))
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("예: 1층 전등동")
        self.location_edit.setFixedWidth(130)
        h.addWidget(self.location_edit)

        h.addStretch()

        layout.addWidget(bar, 0)

    # ─────────────────── 4. PDF 뷰어 + 산출목록 ───────────────────

    def _create_viewer_and_table(self, layout):
        """PDF 뷰어(대) + 하단 산출목록(컴팩트 고정)"""
        # ── PDF 뷰어 (전체 너비, stretch=1 → 최대 공간 차지) ──
        self.pdf_view = PDFGraphicsView()
        self.pdf_view.zoom_changed.connect(
            lambda pct: self.zoom_label.setText(f"{pct}%")
        )
        # 마우스 휠 페이지 넘김 연결
        self.pdf_view.page_change_requested.connect(self._on_wheel_page_change)
        self.pdf_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.pdf_view, 1)  # stretch=1 → 나머지 공간 전부

        # output_table은 내부 데이터 용도로만 유지 (화면에 표시하지 않음)
        self.output_table = None

    # ─────────────────── 5. 상태 바 ───────────────────

    def _create_status_bar(self, layout):
        """하단 상태 바"""
        bar = QFrame()
        bar.setFixedHeight(22)
        bar.setStyleSheet("""
            QFrame { background: #e8e8e8; border-top: 1px solid #bbb; }
            QLabel { font-family: '새굴림'; font-size: 9pt; color: #444; padding: 0 6px; }
        """)
        h = QHBoxLayout(bar)
        h.setContentsMargins(5, 0, 5, 0)
        h.setSpacing(0)

        self.st_file = QLabel("파일: (없음)")
        h.addWidget(self.st_file)
        h.addWidget(QLabel("|"))

        self.st_count = QLabel("항목: 0개")
        h.addWidget(self.st_count)
        h.addWidget(QLabel("|"))

        self.st_zoom = QLabel("줌: 100%")
        h.addWidget(self.st_zoom)
        self.pdf_view.zoom_changed.connect(lambda p: self.st_zoom.setText(f"줌: {p}%"))
        h.addWidget(QLabel("|"))

        self.st_page = QLabel("페이지: 1/1")
        h.addWidget(self.st_page)

        h.addStretch()
        layout.addWidget(bar, 0)

    # ═══════════════════════════ PDF 로드/렌더링 ═══════════════════════════

    def _open_pdf(self):
        """PDF 파일 열기"""
        fp, _ = QFileDialog.getOpenFileName(
            self, "PDF 도면 열기", "", "PDF Files (*.pdf);;All Files (*.*)"
        )
        if fp:
            self._load_pdf(fp)

    def _load_pdf(self, fp):
        """PDF 로드"""
        if not PDF_SUPPORT:
            QMessageBox.warning(self, "PDF 미지원",
                "PyQt6.QtPdf가 설치되지 않았습니다.\npip install PyQt6-Pdf")
            return

        try:
            self.current_pdf_path = fp
            self.pdf_document = QPdfDocument(self)
            self.pdf_document.load(fp)

            pc = self.pdf_document.pageCount()
            if pc <= 0:
                raise RuntimeError(f"PDF 페이지 수: {pc}")

            self.page_spin.setRange(1, pc)
            self.page_spin.setValue(1)
            self.page_label.setText(f"/{pc}")

            fn = os.path.basename(fp)
            self.st_file.setText(f"파일: {fn}")
            self.st_page.setText(f"페이지: 1/{pc}")

            self._render_page(0)
            print(f"[OK] PDF 로드: {fp} ({pc}p)")

        except Exception as e:
            import traceback; traceback.print_exc()
            QMessageBox.critical(self, "PDF 오류", f"PDF를 열 수 없습니다.\n\n{e}")

    def _render_page(self, idx):
        """페이지 렌더링"""
        if not self.pdf_document:
            return
        if idx < 0 or idx >= self.pdf_document.pageCount():
            return

        try:
            ps = self.pdf_document.pagePointSize(idx)
            dpi = 150.0
            s = dpi / 72.0
            w, h = int(ps.width() * s), int(ps.height() * s)
            if w <= 0 or h <= 0:
                raise RuntimeError(f"잘못된 크기: {w}x{h}")

            image = self.pdf_document.render(idx, QSize(w, h))
            if image.isNull():
                raise RuntimeError("렌더링 결과 없음")

            self.pdf_view.scene.clear()
            self.pdf_view.drawing_items.clear()
            pixmap = QPixmap.fromImage(image)
            self.pdf_view.scene.addPixmap(pixmap)
            self.pdf_view.scene.setSceneRect(QRectF(0, 0, pixmap.width(), pixmap.height()))
            self.pdf_view.fit_to_view()

            pc = self.pdf_document.pageCount()
            self.st_page.setText(f"페이지: {idx+1}/{pc}")

        except Exception as e:
            import traceback; traceback.print_exc()
            self.pdf_view.scene.clear()
            self.pdf_view.scene.addRect(
                QRectF(0, 0, 800, 1100), QPen(Qt.GlobalColor.black), QBrush(Qt.GlobalColor.white))
            t = QGraphicsTextItem(f"PDF 렌더링 실패:\n{e}")
            t.setPos(50, 50); t.setDefaultTextColor(QColor("#cc0000"))
            self.pdf_view.scene.addItem(t)

    def _go_to_page(self, n):
        if self.pdf_document:
            self._render_page(n - 1)

    def _prev_page(self):
        v = self.page_spin.value()
        if v > 1:
            self.page_spin.setValue(v - 1)

    def _next_page(self):
        v = self.page_spin.value()
        if v < self.page_spin.maximum():
            self.page_spin.setValue(v + 1)

    def _on_wheel_page_change(self, delta):
        """마우스 휠 페이지 넘김 (-1=이전, +1=다음)"""
        if delta < 0:
            self._next_page()
        elif delta > 0:
            self._prev_page()

    # ═══════════════════════════ 줌 / 전체화면 ═══════════════════════════

    def _zoom(self, factor):
        self.pdf_view.scale(factor, factor)
        self.pdf_view._zoom_factor *= factor
        p = int(self.pdf_view._zoom_factor * 100)
        self.zoom_label.setText(f"{p}%")
        self.st_zoom.setText(f"줌: {p}%")

    def _fit_view(self):
        self.pdf_view.fit_to_view()

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F11:
            self._toggle_fullscreen(); return
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal(); return
        super().keyPressEvent(event)

    # ═══════════════════════════ 그리기 도구 ═══════════════════════════

    def _toggle_line_draw(self, checked):
        if checked:
            self.act_draw_rect.setChecked(False)
            self.btn_draw_rect.setChecked(False)
            self.pdf_view.set_drawing_mode("line", self.current_color)
        elif not self.act_draw_rect.isChecked():
            self.pdf_view.set_drawing_mode(None)

    def _toggle_rect_draw(self, checked):
        if checked:
            self.act_draw_line.setChecked(False)
            self.btn_draw_line.setChecked(False)
            self.pdf_view.set_drawing_mode("rect", self.current_color)
        elif not self.act_draw_line.isChecked():
            self.pdf_view.set_drawing_mode(None)

    def _on_line_toggled(self, checked):
        self.act_draw_line.setChecked(checked)
        self._toggle_line_draw(checked)

    def _on_rect_toggled(self, checked):
        self.act_draw_rect.setChecked(checked)
        self._toggle_rect_draw(checked)

    def _select_color(self):
        color = QColorDialog.getColor(QColor(self.current_color), self, "색상 선택")
        if color.isValid():
            self.current_color = color.name()
            self.color_btn.setStyleSheet(
                f"background: {self.current_color}; border: 1px solid #666; border-radius: 2px;")
            self.pdf_view.current_pen = QPen(color, self.line_width_spin.value())
            self.pdf_view.current_pen.setCosmetic(True)

    def _clear_drawings(self):
        self.pdf_view.clear_drawings()

    # ═══════════════════════════ 산출 항목 관리 ═══════════════════════════

    def _update_table(self):
        """산출 통계 갱신 (테이블 제거됨, 상태바/툴바만 업데이트)"""
        tl = sum(it.length for it in self.output_items)
        tq = sum(it.quantity for it in self.output_items)
        self.st_count.setText(f"항목: {len(self.output_items)}개")
        self.stat_length.setText(f"연장: {tl:.2f}m")
        self.stat_qty.setText(f"수량: {tq:.3f}")

    def _delete_selected(self):
        if self.output_items:
            self.output_items.pop()
            self._update_table()

    def _clear_all(self):
        if QMessageBox.question(
            self, "확인", "모든 산출 항목을 삭제?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            self.output_items.clear()
            self.item_counter = 0
            self.pdf_view.clear_drawings()
            self._update_table()

    def _export_output(self):
        if not self.output_items:
            QMessageBox.warning(self, "경고", "산출할 항목이 없습니다.")
            return

        result = {
            "items": [
                {k: getattr(it, k) for k in
                 ("id","output_type","location","specification",
                  "length","width","depth","area","quantity","unit","notes")}
                for it in self.output_items
            ],
            "total_length": sum(it.length for it in self.output_items),
            "total_quantity": sum(it.quantity for it in self.output_items),
        }
        self.closed.emit(result)
        QMessageBox.information(
            self, "완료",
            f"산출 적용 완료\n항목: {len(self.output_items)}개\n"
            f"연장: {result['total_length']:.2f}m\n수량: {result['total_quantity']:.3f}")
        self.accept()

    # ═══════════════════════════ 도움말 ═══════════════════════════

    def _show_help(self):
        QMessageBox.information(
            self, "PDF 산출 사용법",
            "■ PDF 열기: 파일>열기 또는 Ctrl+O\n"
            "■ 페이지: ◀▶ 또는 PgUp/PgDown\n"
            "■ 줌: 마우스 휠 또는 Ctrl+±, 맞춤=Ctrl+0\n"
            "■ 전체화면: F11, 해제=ESC\n"
            "■ 그리기: 선(━)/면(▢) 도구 선택 후 도면에 드래그\n"
            "■ 산출: 유형 선택→도면 그리기→산출 적용")

    # ═══════════════════════════ 유틸 ═══════════════════════════

    def _tb_btn(self, text, tip=None):
        b = QPushButton(text)
        b.setStyleSheet(BTN_STYLE)
        if tip:
            b.setToolTip(tip)
        return b

    @staticmethod
    def _sep(layout):
        s = QFrame()
        s.setFrameShape(QFrame.Shape.VLine)
        s.setFixedHeight(20)
        s.setStyleSheet("color: #bbb;")
        layout.addWidget(s)

    def _add_action(self, menu, text, shortcut, callback):
        act = QAction(text, self)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.triggered.connect(callback)
        menu.addAction(act)
        return act
