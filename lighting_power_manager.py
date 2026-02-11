# -*- coding: utf-8 -*-
"""
전등/전열 전용 산출공종 관리 모듈
Lighting/Power Management Module
"""

import os
import re
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QSplitter,
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHeaderView,
    QAbstractItemView,
    QRadioButton,
    QButtonGroup,
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

# QMimeData와 QDrag는 버전에 따라 위치가 다를 수 있음
try:
    from PyQt6.QtCore import QMimeData
except ImportError:
    from PyQt6.QtGui import QMimeData

try:
    from PyQt6.QtGui import QDrag
except ImportError:
    from PyQt6.QtCore import QDrag

from database_reference_popup import DatabaseReferencePopup
from utils.column_settings import CleanStyleDelegate

import sqlite3
import re


def evaluate_math(expression):
    """사칙연산 수식을 계산하여 결과를 반환 (안전한 eval)"""
    if not expression:
        return 0.0
    try:
        # 전처리: 공백 제거, 특수 대괄호를 소괄호로, x 또는 X를 *로 변경
        expr = str(expression).strip()
        expr = expr.replace(" ", "")
        expr = expr.replace("{", "(").replace("}", ")")
        expr = expr.replace("[", "(").replace("]", ")")
        expr = expr.replace("x", "*").replace("X", "*")

        # 사칙연산 및 숫자, 소괄호 외의 문자 차단 (보안)
        clean_expr = re.sub(r"[^0-9+\-*/().]", "", expr)

        if not clean_expr:
            return 0.0

        # 계산 실행
        return float(eval(clean_expr))
    except Exception:
        return 0.0


class LightingPowerDelegate(CleanStyleDelegate):
    """전등/전열 팝업 전용 델리게이트 - 편집 중 Tab 키 가로채기 지원"""

    def __init__(self, parent=None, popup=None):
        super().__init__(parent)
        self.popup = popup

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit) and self.popup:
            # [IMPORTANT] 편집기(QLineEdit)에 팝업의 이벤트 필터 설치하여 Tab 키 감지
            editor.installEventFilter(self.popup)
        return editor


class LightingPowerPopup(QDialog):
    """
    전등/전열 DB 연동 팝업창 (2분할 패널)
    세부산출조서
    """

    def __init__(self, parent=None, item_name="", parent_tab=None):
        super().__init__(parent)
        self.setWindowTitle(f"세부산출조서 - {item_name}")
        self.setMinimumSize(
            1192, 750
        )  # 창 너비 확장 (단위수식 +30px 추가 확장, 총 +62px)
        self.db_path = r"D:\오아시스\산출목록\조명기구타입.db"
        self.ref_db_path = r"D:\오아시스\data\자료사전.db"
        self.reference_codes = set()  # 자료사전 코드 매칭용

        # [NEW] 부모 탭 참조 (1식 저장용)
        self.parent_tab = parent_tab
        self.item_name = item_name  # 공종명
        self.current_row = -1  # 산출내역서 행 번호

        # [NEW] 내부 클립보드 (F6, F7, F4용)
        self._internal_clipboard = []

        # [NEW] 마스터 항목별 상세 내역 캐시 (재진입 및 타 항목 이동 시 소실 방지)
        # 구조: { master_row_index: [ { col_index: text, ... }, ... ] }
        self.master_details_cache = {}
        self.current_master_row = -1

        # [NEW] 초기 데이터 (재진입 시 복원용) - list of dict
        self.initial_data = []

        # [PHASE 3-3] Undo 스택 (이전 상태 저장)
        self.undo_stack = []
        self.undo_max = 20  # 최대 20개까지 저장

        # [FIX] 속성 누락 방지 초기화
        self._preview_timer = None
        self.preview_label = None

        self._init_ui()
        self._load_reference_codes()  # 자료사전 로드
        self._load_reference_products()  # [PHASE 3-4] 자동 완성용 데이터 로드
        self._load_master_data()

        # [NEW] 첫 번째 행 자동 선택 및 산출일위 패널에 데이터 표시
        if self.master_table.rowCount() > 0:
            self.master_table.selectRow(0)
            first_item = self.master_table.item(0, 0)
            if first_item:
                self._on_master_item_clicked(first_item)

        # [NEW] 자료사전 팝업 사전 로딩 (Pre-loading 적용으로 첫 호출부터 즉시 표시)
        from database_reference_popup import DatabaseReferencePopup

        print("[DEBUG] Pre-loading Reference DB Popup into memory...")
        self.reference_popup = DatabaseReferencePopup(self)

        # [NEW] 화면 위치 조정 (화면 밖으로 나가는 현상 방지)
        self._adjust_initial_geometry()

    def _adjust_initial_geometry(self):
        """팝업창이 화면 밖으로 나가지 않도록 초기 위치 조정"""
        from PyQt6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen().availableGeometry()

        # 현재 설정된 크기
        w, h = self.width(), self.height()
        # 화면 중앙에 배치하되, 상단 여백 50px 확보 (잘림 방지)
        x = screen.center().x() - w // 2
        y = screen.top() + 50

        # 만약 높이가 화면보다 크면 조정
        if h > screen.height() - 60:
            h = screen.height() - 60
            # setFixedHeight를 제거하여 세로 방향 수축/확장을 허용

        self.setGeometry(x, y, w, h)
        print(f"[DEBUG] Geometry adjusted: {x}, {y}, {w}, {h}")

    # [REMOVED] focusNextPrevChild 제거 (eventFilter로 Tab 로직 일일원화하여 충돌 방지)

    def set_data(self, data, current_row=-1):
        """
        외부에서 초기 데이터 설정

        Args:
            data: 초기 데이터 (list of dict)
            current_row: 산출내역서의 현재 행 번호 (1식 저장용)
        """
        # [NEW] 만약 저장된 데이터가 없는 신규 행(current_row < 0 이거나 data가 비어있음)이라면
        # 자료사전의 수량 입력값을 초기화하여 이전 작업의 잔상이 남지 않게 함
        if current_row < 0 or not data:
            if hasattr(self, "reference_popup") and self.reference_popup.model:
                print(
                    "[DEBUG] New calculation detected. Clearing reference quantities."
                )
                self.reference_popup.model.clear_all_qty()

        self.initial_data = data
        self.current_row = current_row

    def _load_reference_codes(self):
        """자료사전.db에서 모든 CODE를 로드하여 세트에 저장"""
        if not os.path.exists(self.ref_db_path):
            print(f"[DEBUG] Reference DB not found: {self.ref_db_path}")
            return
        try:
            conn = sqlite3.connect(self.ref_db_path)
            cursor = conn.cursor()
            # 사용자의 요청에 따라 'CODE' 컬럼을 매칭 포인트로 사용 (ID는 일련번호)
            cursor.execute("SELECT CAST(CODE AS TEXT) FROM [자료사전]")
            codes = cursor.fetchall()
            self.reference_codes = {
                str(c[0]).strip() for c in codes if c[0] is not None
            }
            conn.close()
            # print(f"[DEBUG] Loaded {len(self.reference_codes)} reference codes.")
        except Exception as e:
            print(f"[DEBUG] Error loading reference codes: {e}")

    def _load_reference_products(self):
        """[PHASE 3-4] 자료사전에서 품목/규격/CODE 데이터 로드 (자동 완성용)"""
        self.reference_products = {}  # {품목: (규격, CODE)}

        if not os.path.exists(self.ref_db_path):
            return

        try:
            conn = sqlite3.connect(self.ref_db_path)
            cursor = conn.cursor()
            # 품명, 규격, CODE 조회
            cursor.execute("SELECT 품명, 규격, CODE FROM [자료사전]")
            rows = cursor.fetchall()

            for row in rows:
                product, spec, code = row
                if product:
                    product_key = str(product).strip()
                    # 품목 → (규격, CODE) 매핑
                    self.reference_products[product_key] = (
                        str(spec) if spec else "",
                        str(code) if code else "",
                    )

            conn.close()
            print(
                f"[DEBUG] Loaded {len(self.reference_products)} reference products for autocomplete."
            )
        except Exception as e:
            print(f"[DEBUG] Error loading reference products: {e}")

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 중앙 2분할 스플리터
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # [패널 1] 왼쪽: 산출목록
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_title = QLabel("산출목록")
        left_title.setStyleSheet("""
            background-color: #f8f9fa;
            padding: 4px 8px;
            border: 1px solid #ced4da;
            font-family: '새굴림';
            font-size: 11pt;
            font-weight: bold;
            color: #495057;
        """)
        left_layout.addWidget(left_title)

        self.master_table = QTableWidget()
        self.master_table.setColumnCount(3)  # 번호 컬럼 삭제
        self.master_table.setHorizontalHeaderLabels(
            ["타입별 조명기구", "구분", "산출수식"]
        )

        self.master_table.verticalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignCenter
        )  # 세로 헤더 중앙 정렬
        self.master_table.verticalHeader().setFont(
            QFont("새굴림", 11)
        )  # 세로 헤더 폰트 설정 (헤더는 새굴림 적용)
        self.master_table.verticalHeader().setDefaultSectionSize(
            22
        )  # 행 높이 22px 설정
        self.master_table.verticalHeader().setFixedWidth(
            15
        )  # [수정] 헤더 너비를 15px로 더 축소 (10% 수준으로 극소화)
        header = self.master_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        # [NEW] 헤더 클릭 선택 기능을 위해 SelectionBehavior를 아이템 단위로 변경하고 다중 선택 허용
        self.master_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems
        )
        self.master_table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        # [NEW] 헤더 클릭 시 행/열 전체 선택 연결
        self.master_table.horizontalHeader().sectionClicked.connect(
            self.master_table.selectColumn
        )
        self.master_table.verticalHeader().sectionClicked.connect(
            self.master_table.selectRow
        )
        # 다양한 입력 방식 허용 (클릭은 itemClicked에서 수동 처리)
        self.master_table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.AnyKeyPressed
        )
        self.master_table.setFont(QFont("새굴림", 11))
        self.master_table.horizontalHeader().setFont(
            QFont("새굴림", 11)
        )  # 헤더 폰트 (헤더는 새굴림 적용)

        # [STYLE] 공통 스타일 적용 (무채색 통일)
        from utils.column_settings import setup_common_table

        setup_common_table(self.master_table, ["타입별 조명기구", "구분", "산출수식"])

        # [NEW] 파란색 잔상 원천 차단 (팔레트 투명화 + 데리게이트)
        m_palette = self.master_table.palette()
        m_palette.setColor(
            QPalette.ColorRole.Highlight, QColor(Qt.GlobalColor.transparent)
        )
        m_palette.setColor(
            QPalette.ColorRole.HighlightedText, m_palette.color(QPalette.ColorRole.Text)
        )
        self.master_table.setPalette(m_palette)
        self.master_table.setItemDelegate(CleanStyleDelegate(self.master_table))
        self.master_table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.master_table.itemClicked.connect(self._on_master_item_clicked)

        left_layout.addWidget(self.master_table)

        # [패널 2] 오른쪽: 산출일위
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 산출일위 헤더 영역 (레이블 + 매칭확인 버튼)
        right_header = QWidget()
        right_header_layout = QHBoxLayout(right_header)
        right_header_layout.setContentsMargins(0, 0, 0, 0)
        right_header_layout.setSpacing(5)

        right_title = QLabel("산출일위")
        right_title.setStyleSheet("""
            background-color: #f8f9fa;
            padding: 4px 8px;
            border: 1px solid #ced4da;
            font-family: '새굴림';
            font-size: 11pt;
            font-weight: bold;
            color: #495057;
        """)
        right_header_layout.addWidget(right_title)

        right_header_layout.addStretch()

        # 매칭확인 버튼
        self.verify_match_btn = QPushButton("매칭확인")
        self.verify_match_btn.setFixedSize(80, 26)
        self.verify_match_btn.setFont(QFont("새굴림", 10))
        self.verify_match_btn.setStyleSheet("""
            QPushButton {
                background-color: #e9ecef;
                border: 1px solid #adb5bd;
                border-radius: 3px;
                color: #495057;
            }
            QPushButton:hover {
                background-color: #dee2e6;
            }
            QPushButton:pressed {
                background-color: #ced4da;
            }
        """)
        self.verify_match_btn.clicked.connect(self._on_verify_match_clicked)
        right_header_layout.addWidget(self.verify_match_btn)

        # [NEW] 저장 옵션 라디오 버튼
        save_option_frame = QFrame()
        save_option_layout = QHBoxLayout(save_option_frame)
        save_option_layout.setContentsMargins(10, 0, 0, 0)
        save_option_layout.setSpacing(5)

        self.save_option_group = QButtonGroup(self)

        self.save_to_original_rb = QRadioButton("원본저장")
        self.save_to_original_rb.setFont(QFont("새굴림", 9))
        self.save_to_original_rb.setChecked(True)  # 기본값: 원본 저장
        self.save_option_group.addButton(self.save_to_original_rb, 0)
        save_option_layout.addWidget(self.save_to_original_rb)

        self.save_to_project_rb = QRadioButton("프로젝트만")
        self.save_to_project_rb.setFont(QFont("새굴림", 9))
        self.save_option_group.addButton(self.save_to_project_rb, 1)
        save_option_layout.addWidget(self.save_to_project_rb)

        right_header_layout.addWidget(save_option_frame)

        right_layout.addWidget(right_header)

        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(5)  # 번호 컬럼 삭제
        self.detail_table.setHorizontalHeaderLabels(
            ["W", "CODE", "산출목록", "단위수식", "계"]
        )

        # 세로 헤더 중앙 정렬 및 폰트
        self.detail_table.verticalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.detail_table.verticalHeader().setFont(QFont("새굴림", 11))
        self.detail_table.verticalHeader().setDefaultSectionSize(
            22
        )  # 행 높이 22px 설정
        self.detail_table.verticalHeader().setFixedWidth(
            15
        )  # [수정] 헤더 너비를 15px로 더 축소 (10% 수준으로 극소화)

        # 헤더 폰트 및 설정
        self.detail_table.setFont(QFont("새굴림", 11))
        self.detail_table.horizontalHeader().setFont(
            QFont("새굴림", 11)
        )  # 헤더 폰트 (헤더는 새굴림 적용)

        # 헤더 너비 수동 조정
        d_header = self.detail_table.horizontalHeader()
        d_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.detail_table.setColumnWidth(0, 50)  # W (마커 포함)
        self.detail_table.setColumnWidth(1, 110)  # CODE (11자)
        self.detail_table.setColumnWidth(2, 230)  # 산출목록
        d_header.setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )  # 단위수식 (여전히 자리가 남으면 확장)
        self.detail_table.setColumnWidth(4, 45)  # 계 (50% 축소: 90 -> 45)

        self.detail_table.setFont(QFont("새굴림", 11))

        # [STYLE] 공통 스타일 적용 (무채색 통일)
        from utils.column_settings import setup_common_table

        setup_common_table(
            self.detail_table, ["W", "CODE", "산출목록", "단위수식", "계"]
        )

        # [NEW] 파란색 잔상 원천 차단 (팔레트 투명화 + 데리게이트)
        d_palette = self.detail_table.palette()
        d_palette.setColor(
            QPalette.ColorRole.Highlight, QColor(Qt.GlobalColor.transparent)
        )
        d_palette.setColor(
            QPalette.ColorRole.HighlightedText, d_palette.color(QPalette.ColorRole.Text)
        )
        self.detail_table.setPalette(d_palette)
        # [NEW] 팝업 전용 델리게이트 적용 (Tab 키 가로채기용)
        self.detail_table.setItemDelegate(
            LightingPowerDelegate(self.detail_table, self)
        )
        self.detail_table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.detail_table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
        )  # 더블 클릭 시 편집 활성화
        self.detail_table.itemChanged.connect(self._on_detail_item_changed)  # 변경 감지

        # [PHASE 3-5] 드래그 앤 드롭 설정
        self.detail_table.setAcceptDrops(True)
        self.detail_table.setDefaultDropAction(Qt.DropAction.CopyAction)

        # [NEW] 헤더 클릭 선택 기능을 위해 SelectionBehavior를 아이템 단위로 변경하고 다중 선택 허용
        self.detail_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems
        )
        self.detail_table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        # [NEW] 헤더 클릭 시 행/열 전체 선택 연결
        self.detail_table.horizontalHeader().sectionClicked.connect(
            self.detail_table.selectColumn
        )
        self.detail_table.verticalHeader().sectionClicked.connect(
            self.detail_table.selectRow
        )

        # [NEW] TAB 키 → 자료사전 팝업 호출 (이벤트 필터 설치)
        self.detail_table.installEventFilter(self)

        right_layout.addWidget(self.detail_table)

        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(right_panel)

        # [수정] 산출일위 패널 30px 추가 확장 반영 (총 1192 기준)
        self.splitter.setSizes([490, 672])
        self.splitter.setStretchFactor(0, 5)
        self.splitter.setStretchFactor(1, 6)

        main_layout.addWidget(self.splitter)

        # [PHASE 3-1] 실시간 합계 표시 (프리뷰) - REMOVED per user request
        # preview_layout = QHBoxLayout()
        # preview_layout.setContentsMargins(10, 5, 10, 5)
        #
        # self.preview_label = QLabel("합계: 0")
        # self.preview_label.setStyleSheet(
        #     "font-family: '새굴림'; font-size: 11pt; font-weight: bold; "
        #     "color: #2c3e50; background-color: #ecf0f1; padding: 8px; "
        #     "border-radius: 3px; border-left: 4px solid #3498db;"
        # )
        # self.preview_label.setMinimumHeight(35)
        # preview_layout.addWidget(self.preview_label)
        #
        # main_layout.addLayout(preview_layout)

        # 하단 버튼
        btn_layout = QHBoxLayout()

        # 우측 버튼들
        btn_layout.addStretch()

        # [수정] "선택 적용" → 1식 저장 + 팝업 닫기
        select_btn = QPushButton("내보내기")  # 버튼명 변경
        select_btn.setFixedSize(120, 35)
        select_btn.setStyleSheet("font-family: '새굴림'; font-size: 11pt;")
        select_btn.clicked.connect(self.accept)  # accept() 메서드로 이동

        close_btn = QPushButton("닫기")
        close_btn.setFixedSize(100, 35)
        close_btn.setStyleSheet("font-family: '새굴림'; font-size: 11pt;")
        close_btn.clicked.connect(self.reject)

        btn_layout.addWidget(select_btn)
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)

        # [FIX] 이벤트 필터 설치 일괄 처리 (TAB 키 및 단축키 정상화)
        for w in [
            self.master_table,
            self.detail_table,
            self.master_table.viewport(),
            self.detail_table.viewport(),
            self,
        ]:
            if w:
                w.installEventFilter(self)

        # [FIX] TAB 키가 필터에 도달하도록 내비게이션 비활성화 (전체 패널)
        self.master_table.setTabKeyNavigation(False)
        self.detail_table.setTabKeyNavigation(False)

    def _load_master_data(self):
        """DB에서 조명기구 목록 로드"""
        if not os.path.exists(self.db_path):
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # [OPTIMIZE] 성능 향상 PRAGMA
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")

            table_name = "조명기구목록"
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND (name='조명기구목록' OR name='조명기구목골');"
            )
            result = cursor.fetchone()
            if result:
                table_name = result[0]

            cursor.execute(f"SELECT * FROM [{table_name}]")
            rows = cursor.fetchall()

            # [OPTIMIZE] UI 업데이트 일시 중지
            self.master_table.setUpdatesEnabled(False)
            self.master_table.setRowCount(len(rows))
            fm = self.master_table.fontMetrics()
            max_name_width = 100

            for r_idx, row in enumerate(rows):
                display_cols = row[1:4]
                for c_idx, val in enumerate(display_cols):
                    text = str(val) if val is not None else ""
                    item = QTableWidgetItem(text)

                    # 편집 기능 제어: 산출수식만 편집 가능
                    if c_idx == 2:
                        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                    else:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                    if c_idx == 0:
                        w = fm.horizontalAdvance(text + "   ")
                        if w > max_name_width:
                            max_name_width = w

                    if c_idx == 1:  # 구분 (중앙)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    else:
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                        )

                    self.master_table.setItem(r_idx, c_idx, item)

            # [NEW] 초기 데이터가 있다면 복원
            if self.initial_data:
                self.restore_data()

            # 너비 조정: 산출수식(2번) 13% 추가 확장 (105 -> 120)
            self.master_table.setColumnWidth(0, max_name_width)
            self.master_table.setColumnWidth(1, 45)
            self.master_table.setColumnWidth(2, 120)

            # [OPTIMIZE] UI 업데이트 재개
            self.master_table.setUpdatesEnabled(True)

            # [여백 최적화]
            # 좌측 패널 너비 = (기구명) + (구분) + (산출수식) + (마진: 수직헤더+스크롤바 등 약 45px -> 80px로 넉넉하게)
            # 가로 스크롤 제거 요청 반영
            left_width_target = max_name_width + 45 + 120 + 80
            total_width = self.width()

            # 스플리터 강제 조정 (왼쪽 고정, 오른쪽 나머지)
            if total_width > left_width_target:
                self.splitter.setSizes(
                    [left_width_target, total_width - left_width_target]
                )

            conn.close()
        except Exception as e:
            print(f"[DEBUG] Error loading master data: {e}")

    def _on_detail_item_changed(self, item):
        """상세 일위 테이블 아이템 변경 시 호출"""
        col = item.column()

        # [PHASE 3-1] 단위수식(3번 컬럼)이 변경된 경우에만 '계' 재계산
        if col == 3:
            row = item.row()
            formula = item.text()
            try:
                formula_clean = formula.replace(",", "")
                if not formula_clean.strip():
                    calc_val = 0
                else:
                    calc_val = self._evaluate_math(formula_clean)
            except:
                calc_val = 0

            # '계' 컬럼(4번) 업데이트 (SIGNAL 차단하여 무한루프 방지)
            self.detail_table.blockSignals(True)
            self.detail_table.setItem(row, 4, QTableWidgetItem(f"{calc_val:g}"))
            self.detail_table.item(row, 4).setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            self.detail_table.blockSignals(False)

            # [Step 10] '계' 변경되었으므로 전체 합계 업데이트
            self._update_preview_sum()

        # [NEW] CODE(1번) 또는 산출목록(2번) 변경 시 W 상태 재검증
        if col in [1, 2]:
            self._verify_all_codes()

        # [PHASE 3-4] 산출목록(컬럼 2) 입력 시 자동 완성
        if col == 2:
            self._auto_complete_product(item.row(), item.text())

    # [REMOVED] _on_tab_pressed 및 중복 메서드 제거

    # [REMOVED] 중복된 _show_reference_db_popup 제거

    def _evaluate_math(self, expression):
        """간단한 수식 계산 (Eval)"""
        try:
            # 허용된 문자만 남기기 (숫자, ., +, -, *, /, (, ))
            allowed = "0123456789.+-*/() "
            clean_expr = "".join([c for c in expression if c in allowed])
            return eval(clean_expr, {"__builtins__": None}, {})
        except:
            return 0

    def _update_preview_sum(self):
        """[PHASE 3-1] 실시간 합계 업데이트 (debounce로 성능 최적화)"""
        # [FIX] 타이머 초기화 (AttributeError 방지)
        if getattr(self, "_preview_timer", None) is None:
            self._preview_timer = QTimer()
            self._preview_timer.setSingleShot(True)
            self._preview_timer.timeout.connect(self._calculate_preview_sum)

        self._preview_timer.stop()
        self._preview_timer.start(100)

    def _calculate_preview_sum(self):
        """[PHASE 3-1] 실시간 합계 실제 계산"""
        total_sum = 0.0

        for row in range(self.detail_table.rowCount()):
            # [Step 10] 단위수식(3번) → 계(4번) 결과값 저장(출력) 동기화 보장
            formula_item = self.detail_table.item(row, 3)
            total_item = self.detail_table.item(row, 4)

            if formula_item:
                formula_text = formula_item.text().strip()
                if formula_text:
                    calc_val = self._evaluate_math(formula_text)

                    # 계 컬럼에 결과값 저장 (UI 출력)
                    self.detail_table.blockSignals(True)
                    if not total_item:
                        total_item = QTableWidgetItem()
                        self.detail_table.setItem(row, 4, total_item)

                    total_item.setText(f"{calc_val:g}")
                    total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.detail_table.blockSignals(False)

                    total_sum += float(calc_val)

        # 합계 텍스트 업데이트
        sum_text = (
            f"{int(total_sum):,}" if total_sum.is_integer() else f"{total_sum:,.2f}"
        )

        # [FIX] preview_label 존재 시에만 업데이트 (AttributeError 방지)
        if hasattr(self, "preview_label") and self.preview_label:
            self.preview_label.setText(f"합계: {sum_text}")

        print(f"[DEBUG] Preview sum updated (Console): {sum_text}")

    def _validate_all_inputs(self):
        """[Step 10] 모든 입력 데이터 유효성 검사 (미매칭 코드 및 필수값 체크)"""
        errors = []
        has_mismatch = False
        has_empty_code = False

        for row in range(
            1, self.detail_table.rowCount()
        ):  # [FIX] 첫 행(기구명 헤더) 제외
            # 1. W 마커 기반 상태 체크
            w_item = self.detail_table.item(row, 0)
            if w_item:
                w_status = w_item.text()
                if w_status in ["~*", "~i"]:
                    has_mismatch = True
                elif w_status == "**":
                    has_empty_code = True

            # 2. 필수 필드(산출목록, 단위수식) 공백 체크
            product_item = self.detail_table.item(row, 2)
            if not product_item or not product_item.text().strip():
                errors.append(f"행 {row + 1}: 산출목록이 입력되지 않았습니다.")

            formula_item = self.detail_table.item(row, 3)
            if not formula_item or not formula_item.text().strip():
                errors.append(f"행 {row + 1}: 단위수식이 입력되지 않았습니다.")

        # 종합 경고/안내 메시지 생성
        if has_mismatch:
            errors.append("자료사전에 없는 코드(~*, ~i)가 포함되어 있습니다.")
        if has_empty_code:
            errors.append("수량이 입력되지 않은 행(**)이 포함되어 있습니다.")

        if self.detail_table.rowCount() == 0:
            errors.append("산출 내역이 비어 있습니다.")

        return errors

    def _show_validation_errors(self, errors):
        """[PHASE 3-2] 유효성 검사 오류 표시 (사용자 요청으로 메시지 박스 제거)"""
        if not errors:
            return True

        # 메시지 박스 없이 바로 진행하도록 수정
        print(f"[DEBUG] Validation errors ignored: {errors}")
        return True

    def is_ilwi_item(self, code):
        """
        [PHASE 2-1] 일위대가 품목 여부를 판정하는 함수
        TODO: 실제 일위대가 판정 기준이 확정되면 구현 예정
        현재 임시 기준: 코드의 첫 자가 'i' 또는 'I'인 경우
        """
        if not code:
            return False
        return str(code).strip().lower().startswith("i")

    def _on_verify_match_clicked(self):
        """매칭확인 버튼 클릭 시 수동 매핑 파일 새로 로드 후 W컬럼 갱신"""
        try:
            import sys

            project_folder = os.path.dirname(os.path.abspath(sys.argv[0]))

            # [NEW] 매핑 로드 우선순위: 프로젝트 → 원본 (병합)
            manual_mappings = {}

            # 1. 원본 매핑 로드
            original_mapping_path = r"D:\오아시스\data\manual_mapping.json"
            if os.path.exists(original_mapping_path):
                with open(original_mapping_path, "r", encoding="utf-8") as f:
                    manual_mappings = json.load(f)

            # 2. 프로젝트 매핑 로드 (원본 덮어쓰기 - 프로젝트 우선)
            project_mapping_path = os.path.join(
                project_folder, "project_data", "manual_mapping.json"
            )
            if os.path.exists(project_mapping_path):
                with open(project_mapping_path, "r", encoding="utf-8") as f:
                    project_mappings = json.load(f)
                    manual_mappings.update(project_mappings)  # 프로젝트 값으로 덮어쓰기

            if manual_mappings:
                # 산출일위 테이블 순회하며 수동 매핑 적용
                for row in range(self.detail_table.rowCount()):
                    product_item = self.detail_table.item(row, 2)  # 산출목록
                    formula_item = self.detail_table.item(row, 3)  # 단위수식
                    code_item = self.detail_table.item(row, 1)  # CODE

                    if product_item and product_item.text().strip():
                        product_name = product_item.text().strip()
                        spec = formula_item.text().strip() if formula_item else ""
                        key_text = f"{product_name}|{spec}"

                        # 수동 매핑에 해당 키가 있으면 CODE 적용
                        if key_text in manual_mappings:
                            code_val = manual_mappings[key_text]
                            if code_item:
                                code_item.setText(code_val)
                            else:
                                from PyQt6.QtWidgets import QTableWidgetItem

                                self.detail_table.setItem(
                                    row, 1, QTableWidgetItem(code_val)
                                )
                            print(f"[매칭확인] {key_text} → {code_val}")

            # W컬럼 상태 갱신
            self._verify_all_codes()
            print("[매칭확인] 완료 - W컬럼 갱신됨")

        except Exception as e:
            print(f"[ERROR] 매칭확인 실패: {e}")

    def _verify_all_codes(self):
        """[5단계] 모든 행의 CODE를 자료사전과 매칭 검증하고 W 컬럼 및 스타일 업데이트"""
        try:
            self.detail_table.blockSignals(True)

            # 색상/폰트 정의
            color_ilwi = QColor(0, 0, 139)  # 일위대가 (i): 짙은 청색
            color_mismatch = QColor(255, 0, 0)  # 미매칭 (~): 빨강
            color_normal = QColor(0, 0, 0)  # 일반: 검정
            color_empty = QColor(128, 128, 0)  # 빈값 (**): 올리브/갈색

            # [Step 12] 수동 매핑 데이터 로드 (전등수량 산출인 경우에만)
            manual_mappings = {}
            if self.item_name == "전등수량(갯수)산출":
                mapping_path = r"D:\오아시스\data\manual_mapping.json"
                if os.path.exists(mapping_path):
                    try:
                        with open(mapping_path, "r", encoding="utf-8") as f:
                            manual_mappings = json.load(f)
                    except Exception as e:
                        print(f"[DEBUG] Error loading manual mappings: {e}")

            # [NEW] 첫 행(0번 행, 기구명) 스타일 초기화 및 마커 제거
            if self.detail_table.rowCount() > 0:
                first_w = self.detail_table.item(0, 0)
                if first_w:
                    first_w.setText("")  # 마커 제거

                # 첫 행 전체 스타일 초기화 (기본 검정, 볼드)
                first_font = QFont("새굴림", 11, QFont.Weight.Bold)
                for c in range(self.detail_table.columnCount()):
                    it = self.detail_table.item(0, c)
                    if it:
                        it.setForeground(color_normal)
                        it.setFont(first_font)

            for row in range(1, self.detail_table.rowCount()):  # [FIX] 첫 행 제외
                code_item = self.detail_table.item(row, 1)  # CODE 컬럼
                w_item = self.detail_table.item(row, 0)  # W 컬럼
                product_item = self.detail_table.item(row, 2)  # 산출목록

                if not code_item:
                    continue
                if not w_item:
                    w_item = QTableWidgetItem("")
                    self.detail_table.setItem(row, 0, w_item)

                code_val = code_item.text().strip()

                # [Step 12] 코드가 없는 경우 수동 매핑 사전 확인
                if not code_val and self.item_name == "전등수량(갯수)산출":
                    if product_item:
                        spec_item = self.detail_table.item(row, 3)
                        name_text = product_item.text().strip()
                        spec_text = spec_item.text().strip() if spec_item else ""
                        key_text = f"{name_text}|{spec_text}"

                        if key_text in manual_mappings:
                            code_val = manual_mappings[key_text]
                            code_item.setText(code_val)
                            print(
                                f"[DEBUG] Auto-applied manual CODE for {key_text}: {code_val}"
                            )

                # 1. 일위대가 판정 (인터페이스 호출)
                is_ilwi = self.is_ilwi_item(code_val)

                # 2. W 상태 판정 규칙
                if not code_val:
                    # CODE 빈값
                    w_status = "**"
                    text_color = color_empty
                else:
                    matched = code_val in self.reference_codes
                    if matched:
                        # 매칭 성공
                        w_status = "-i-" if is_ilwi else "--"
                        text_color = color_ilwi if is_ilwi else color_normal
                    else:
                        # 매칭 실패
                        w_status = "~i" if is_ilwi else "~*"
                        text_color = color_ilwi if is_ilwi else color_mismatch

                # 3. UI 적용
                w_item.setText(w_status)
                w_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # 폰트 및 색상 적용
                bold_font = QFont("새굴림", 11, QFont.Weight.Bold)
                normal_font = QFont("새굴림", 11)

                # 'i' 행은 항상 짙은 청색, 그 외는 상태 색상
                current_row_color = color_ilwi if is_ilwi else text_color

                w_item.setForeground(current_row_color)
                w_item.setFont(bold_font)

                if product_item:
                    product_item.setForeground(current_row_color)
                    # 일위대가는 목록도 볼드 처리 (선택사항이나 가독성 위해 유지)
                    if is_ilwi:
                        product_item.setFont(bold_font)
                    else:
                        product_item.setFont(normal_font)

                # CODE 컬럼도 색상 동기화
                code_item.setForeground(current_row_color)

            self.detail_table.blockSignals(False)

        except Exception as e:
            print(f"[ERROR] Error in _verify_all_codes: {e}")
            self.detail_table.blockSignals(False)

    def _on_master_item_clicked(self, item):
        """마스터 클릭 시 구분별 상세 테이블 로드 및 첫 행 기구명 입력"""
        row_idx = item.row()

        # [Step 12] 1. 기존에 작업하던 상세 내역을 캐시에 저장 (항목 이동 시 소실 방지)
        if self.current_master_row != -1:
            prev_data = []
            for r in range(self.detail_table.rowCount()):
                row_dict = {}
                for c in range(self.detail_table.columnCount()):
                    detail_item = self.detail_table.item(r, c)
                    row_dict[c] = detail_item.text() if detail_item else ""
                prev_data.append(row_dict)
            self.master_details_cache[self.current_master_row] = prev_data

        # 2. 현재 마스터 행 인덱스 업데이트
        self.current_master_row = row_idx

        lighting_item = self.master_table.item(row_idx, 0)
        gubun_item = self.master_table.item(row_idx, 1)  # 구분

        if not lighting_item or not gubun_item:
            print(f"[DEBUG] Selection contains empty items at row {row_idx}")
            return

        lighting_name = lighting_item.text().strip()  # 타입별 조명기구
        gubun_text = gubun_item.text().strip()
        if not gubun_text:
            return

        # [NEW] 클릭 시 산출수식(2번 컬럼)으로 포커스 이동 및 편집 모드 진입
        if item.column() != 2:
            self.master_table.setCurrentCell(row_idx, 2)
            # self.master_table.editItem(self.master_table.item(row_idx, 2))

        # [Step 12] 3. 캐시에 데이터가 있는 경우 캐시에서 우선 로드
        if row_idx in self.master_details_cache:
            cached_data = self.master_details_cache[row_idx]
            self.detail_table.blockSignals(True)
            self.detail_table.setRowCount(len(cached_data))
            for r_idx, row_dict in enumerate(cached_data):
                for c_idx, text in row_dict.items():
                    cell_item = QTableWidgetItem(text)
                    c_idx_int = int(c_idx)
                    if c_idx_int in [0, 1, 4]:
                        cell_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.detail_table.setItem(r_idx, c_idx_int, cell_item)
            self.detail_table.blockSignals(False)
            self._verify_all_codes()  # 검표 수행
            return

        # 4. 캐시에 없는 경우에만 DB에서 조명기구 템플릿 로드
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(f"SELECT * FROM [{gubun_text}]")
            rows = cursor.fetchall()

            # DB의 2번째 행부터 출력하도록 (DB 기준 첫 줄 제외)
            valid_rows = rows[1:] if len(rows) > 1 else []
            self.detail_table.setRowCount(len(valid_rows) + 1)

            # [1행] 타입별 조명기구명 입력
            header_item = QTableWidgetItem(lighting_name)
            self.detail_table.setItem(0, 2, header_item)  # 산출목록 컬럼

            for r_idx, row_data in enumerate(valid_rows):
                # 실제 데이터는 2행(Index 1)부터 입력
                target_r = r_idx + 1
                display_data = row_data[1:6]  # W, CODE, 목록, 수식, 계

                for c_idx, val in enumerate(display_data):
                    text = str(val) if val is not None else ""

                    if c_idx == 4:  # '계' 컬럼 자동 계산
                        formula = (
                            str(display_data[3]) if display_data[3] is not None else ""
                        )
                        calc_val = evaluate_math(formula)
                        text = f"{calc_val:g}"

                    cell_item = QTableWidgetItem(text)
                    if c_idx in [0, 1, 4]:
                        cell_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    self.detail_table.setItem(target_r, c_idx, cell_item)

            conn.close()

            # [NEW] 데이터 로딩 후 일괄 W 마커 검증
            self._verify_all_codes()

        except sqlite3.OperationalError:
            # 테이블이 없는 경우 첫 행 기구명만 입력
            print(f"[WARNING] Table '{gubun_text}' not found in DB.")
            self.detail_table.setRowCount(1)
            self.detail_table.setItem(0, 2, QTableWidgetItem(lighting_name))
        except Exception as e:
            print(f"[ERROR] Error loading detail data for table '{gubun_text}': {e}")
            self.detail_table.setItem(0, 2, QTableWidgetItem(lighting_name))

    def load_from_saved_state(self, saved_data):
        """[Step 11/12] 저장된 JSON 데이터를 기반으로 세부산출조서 상태 복구"""
        if not saved_data:
            return

        try:
            # 1. 헤더 복구
            self.item_name = saved_data.get("item_header", "")
            self.setWindowTitle(f"세부산출조서 - {self.item_name} (수정)")

            # [Step 12] 2. 마스터 테이블 산출수식 복구
            self.master_table.blockSignals(True)
            master_formulas = saved_data.get("master_formulas", {})
            for r_idx_str, formula in master_formulas.items():
                r_idx = int(r_idx_str)
                if r_idx < self.master_table.rowCount():
                    item = QTableWidgetItem(str(formula))
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                    )
                    self.master_table.setItem(r_idx, 2, item)
            self.master_table.blockSignals(False)

            # [Step 12] 3. 상세 내역 캐시(master_details_cache) 복구
            raw_cache = saved_data.get("master_details_cache", {})
            # JSON은 키를 문자열로 저장하므로 다시 정수로 변환
            self.master_details_cache = {int(k): v for k, v in raw_cache.items()}

            # [Step 12] 4. 마지막 작업 상태(마스터 행) 복구
            ui_state = saved_data.get("ui_state", {})
            last_master_row = ui_state.get("last_master_row", -1)
            scroll_pos = ui_state.get("scroll_pos", 0)

            if last_master_row >= 0 and last_master_row < self.master_table.rowCount():
                # 마스터 행을 클릭한 효과를 주어 상세 테이블 로드
                master_item = self.master_table.item(last_master_row, 0)
                if master_item:
                    # current_master_row가 -1인 상태에서 호출되므로 캐시 저장 없이 바로 로드됨
                    self.master_table.setCurrentCell(last_master_row, 0)
                    self._on_master_item_clicked(master_item)

            self.detail_table.verticalScrollBar().setValue(scroll_pos)

            # 5. 검증 및 합계 갱신 (로드 직후 필수)
            self._verify_all_codes()
            self._update_preview_sum()

            print(
                f"[DEBUG] State restored for '{self.item_name}' | Cached Masters: {len(self.master_details_cache)}"
            )

        except Exception as e:
            print(f"[ERROR] Error restoring state: {e}")
            import traceback

            traceback.print_exc()

    def get_apply_data(self):
        """
        선택 적용된 데이터 반환
        반환 형식: list of dict
        [{'name': '조명기구명', 'formula': '산출수식'}, ...]
        """
        data = []
        for r in range(self.master_table.rowCount()):
            # 산출수식(2번 컬럼)에 값이 있는 경우만 수집
            formula_item = self.master_table.item(r, 2)
            if formula_item and formula_item.text().strip():
                formula = formula_item.text().strip()
                name_item = self.master_table.item(r, 0)
                name = name_item.text().strip() if name_item else ""

                data.append({"name": name, "formula": formula})
        return data

    def get_final_sum(self):
        """[Step 12] 세부산출조서의 최종 합계 계산 (모든 마스터 항목의 합계)"""
        try:
            total = 0.0
            # [Step 12] 마스터 테이블의 '산출수식'(2번 컬럼)에 입력된 모든 값의 합계 계산
            for r in range(self.master_table.rowCount()):
                item = self.master_table.item(r, 2)
                if item and item.text().strip():
                    formula = item.text().strip().replace(",", "")
                    total += evaluate_math(formula)
            return total
        except Exception as e:
            print(f"[ERROR] Error calculating final sum: {e}")
            return 0.0

    def save_to_gapji(self):
        """[NEW / Step 10] 세부산출조서 데이터를 산출내역서(갑지)에 1식으로 저장"""
        try:
            # [Step 10] 입력 데이터 유효성 검사 (미매칭 코드 등)
            errors = self._validate_all_inputs()
            if errors:
                if not self._show_validation_errors(errors):
                    return False  # 사용자가 No 선택 시 저장 취소

            # [Step 12] 현재 작업 중인 상세 내역을 캐시에 최종 저장
            if self.current_master_row != -1:
                curr_data = []
                for r in range(self.detail_table.rowCount()):
                    row_dict = {}
                    for c in range(self.detail_table.columnCount()):
                        detail_item = self.detail_table.item(r, c)
                        row_dict[c] = detail_item.text() if detail_item else ""
                    curr_data.append(row_dict)
                self.master_details_cache[self.current_master_row] = curr_data

            if not self.parent_tab:
                print("[WARNING] parent_tab not set. Cannot save to gapji.")
                return False

            if self.current_row < 0:
                print("[WARNING] current_row not set. Cannot save to gapji.")
                return False

            # 산출내역서의 현재 행 참조
            gapji_table = self.parent_tab.gapji_table

            if not gapji_table or self.current_row >= gapji_table.rowCount():
                print(f"[WARNING] Invalid row {self.current_row}")
                return False

            # [Step 10] 산출수식/합계 계산
            final_sum = self.get_final_sum()
            sum_text = (
                f"{int(final_sum)}" if final_sum == int(final_sum) else f"{final_sum:g}"
            )

            # [Step 12] 마스터 테이블의 수식 정보 저장
            master_formulas = {}
            for r in range(self.master_table.rowCount()):
                f_item = self.master_table.item(r, 2)
                if f_item and f_item.text().strip():
                    master_formulas[r] = f_item.text().strip()

            # [Step 11] UI 상태 추가 저장 (마지막 행, 스크롤 위치)
            last_row = self.detail_table.currentRow()
            scroll_pos = self.detail_table.verticalScrollBar().value()

            # 저장용 구조: 헤드명 + 수량 리스트 (JSON)
            save_payload = {
                "item_header": self.item_name,
                "final_total": final_sum,
                "master_formulas": master_formulas,  # 마스터 테이블의 수식들
                "master_details_cache": self.master_details_cache,  # 상세 내역 전체 캐시
                "ui_state": {
                    "last_master_row": self.current_master_row,
                    "last_row": last_row,
                    "scroll_pos": scroll_pos,
                },
            }

            # [Step 12] 외부(LightingPowerManager)에서 사용하기 위해 최근 저장 데이터로 보관
            self.last_save_payload = save_payload

            # 산출내역서 업데이트 (매칭 컬럼 주의)
            gapji_table.blockSignals(True)

            # 산출목록 (Col 3) = 선택된 공종명
            item_widget = QTableWidgetItem(self.item_name)
            # [CRITICAL] 상세 데이터를 UserRole에 영구 저장 (재진입용)
            item_widget.setData(Qt.ItemDataRole.UserRole, save_payload)
            gapji_table.setItem(self.current_row, 3, item_widget)

            # 나머지 정보 업데이트...

            # 단위 (Col 4) = 식
            gapji_table.setItem(self.current_row, 4, QTableWidgetItem("식"))

            # 산출수식 (Col 5) = 1
            gapji_table.setItem(self.current_row, 5, QTableWidgetItem("1"))

            # 계 (Col 6) = 세부산출조서 최종 합계
            gapji_table.setItem(self.current_row, 6, QTableWidgetItem(sum_text))

            gapji_table.blockSignals(False)

            # [Step 10] 부모 탭의 저장 로직 트리거
            if hasattr(self.parent_tab, "_save_eulji_data"):
                self.parent_tab._save_eulji_data(self.parent_tab.current_gongjong)

            print(f"[DEBUG] Saved to gapji row {self.current_row} | Sum: {sum_text}")
            return True

        except Exception as e:
            print(f"[ERROR] Error saving to gapji: {e}")
            import traceback

            traceback.print_exc()
            return False

    def accept(self):
        """[NEW] 내보내기 버튼 또는 ESC → 1식 저장 후 팝업 닫기"""
        # 상태 저장
        self.save_state()

        # 1식 저장 시도
        if self.save_to_gapji():
            print("[DEBUG] Data saved successfully. Closing popup.")
            super().accept()
        else:
            print("[WARNING] Failed to save data. Popup remains open.")
            # 저장 실패 시 팝업 유지

    def keyPressEvent(self, event):
        """[NEW] ESC 키: 저장 후 산출내역서로 복귀"""
        if event.key() == Qt.Key.Key_Escape:
            # ESC 키: 현재까지의 작업 저장 후 종료
            print("[DEBUG] ESC pressed - saving and closing popup")
            self.accept()
            return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        """[Step 6/6단계/Fix] 단축키 처리 및 특수 입력 처리 (통합 버전)"""
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            is_ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)

            # 1. TAB 키 처리 (자료사전 호출 등)
            if key == Qt.Key.Key_Tab:
                focused = self.focusWidget()
                # 위젯 타입 판별 세분화
                is_on_master = obj == self.master_table or (
                    obj.isWidgetType() and self.master_table.isAncestorOf(obj)
                )
                is_on_detail = obj == self.detail_table or (
                    obj.isWidgetType() and self.detail_table.isAncestorOf(obj)
                )

                # [산출목록 -> 산출일위 이동] (좌측 패널 어느 컬럼에서든 즉시 이동)
                if is_on_master:
                    # 에디터가 열려있는 경우 커밋
                    if self.master_table.state() == QTableWidget.State.EditingState:
                        self.master_table.setCurrentCell(
                            self.master_table.currentRow(),
                            self.master_table.currentColumn(),
                        )

                    target_row = self.detail_table.currentRow()
                    if target_row < 0:
                        target_row = 0

                    # [FIX] CODE 컬럼(Index 1)으로 커서 즉시 이동
                    self.detail_table.setCurrentCell(target_row, 1)
                    self.detail_table.setFocus()
                    return True

                # [산출일위 -> 자료사전 호출] (우측 패널 '산출목록' 칸에서 팝업 열기)
                if is_on_detail:
                    row = self.detail_table.currentRow()
                    col = self.detail_table.currentColumn()
                    # 산출목록(Col 2) 또는 CODE(Col 1)에서 호출 허용
                    if col in [1, 2] and row >= 0:
                        # 편집 모드면 데이터 확정
                        if self.detail_table.state() == QTableWidget.State.EditingState:
                            try:
                                editor = (
                                    obj
                                    if isinstance(obj, QLineEdit)
                                    else self.focusWidget()
                                )
                                if editor and self.detail_table.viewport().isAncestorOf(
                                    editor
                                ):
                                    self.detail_table.commitData(editor)
                                    self.detail_table.closeEditor(
                                        editor, QAbstractItemDelegate.EndEditHint.NoHint
                                    )
                            except:
                                pass

                        self._show_reference_db_popup()
                        return True

                return False

            # 2. master_table 전용 처리 (숫자 누적 입력)
            if obj == self.master_table or obj == self.master_table.viewport():
                # 숫자 키 입력 시 값 누적 (+)
                is_digit = Qt.Key.Key_0 <= key <= Qt.Key.Key_9
                if (
                    is_digit
                    and modifiers == Qt.KeyboardModifier.NoModifier
                    and self.master_table.state() != QTableWidget.State.EditingState
                ):
                    current_row = self.master_table.currentRow()
                    current_col = self.master_table.currentColumn()
                    if current_col == 2:
                        item = self.master_table.item(current_row, current_col)
                        if item and item.text().strip():
                            text = item.text()
                            char = event.text()
                            new_text = f"{text}+{char}"
                            item.setText(new_text)
                            self.master_table.editItem(item)
                            return True

                # 엔터 키 -> 다음 행 이동
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    current_row = self.master_table.currentRow()
                    current_col = self.master_table.currentColumn()
                    if current_col == 2:
                        next_row = current_row + 1
                        if next_row < self.master_table.rowCount():
                            self.master_table.setCurrentCell(next_row, current_col)
                            return True

            # 3. 공통 단축키 처리
            # ESC 키 → 1식 저장 + 팝업 닫기
            if key == Qt.Key.Key_Escape:
                self.accept()
                return True

            # F9 키 → 저장 (조각파일 저장)
            if key == Qt.Key.Key_F9:
                self._save_piece_file()
                return True

            # F5 키 → 다중 선택 모드 토글
            if key == Qt.Key.Key_F5:
                self._toggle_multi_selection()
                return True

            # F6 키 → 복사 (Copy)
            if key == Qt.Key.Key_F6:
                self._copy_selection()
                return True

            # F7 키 → 붙여넣기 (Paste)
            if key == Qt.Key.Key_F7:
                self._paste_selection()
                return True

            # F4 키 → 이동 (Cut/Move)
            if key == Qt.Key.Key_F4:
                self._cut_selection()
                return True

            # Ctrl+Y → 선택 행 삭제
            if is_ctrl and key == Qt.Key.Key_Y:
                self._delete_selected_rows()
                return True

            # Ctrl+N → 선택 행 위에 새 행 삽입
            if is_ctrl and key == Qt.Key.Key_N:
                self._insert_row_above()
                return True

            # [PHASE 3-3] Ctrl+S → 현재 상태 저장
            if is_ctrl and key == Qt.Key.Key_S:
                self._save_current_state()
                return True

            # [PHASE 3-3] Ctrl+Z → 이전 상태 복구
            if is_ctrl and key == Qt.Key.Key_Z:
                self._restore_previous_state()
                return True

        # [PHASE 3-5] 드래그 앤 드롭 이벤트 처리
        if obj == self.detail_table:
            if event.type() == QEvent.Type.DragEnter:
                return self._drag_enter_event(event)
            elif event.type() == QEvent.Type.Drop:
                return self._drop_event(event)

        return super().eventFilter(obj, event)

    def _show_reference_db_popup(self):
        """[Step 7/9] TAB 키 감지 시 자료사전 DB 팝업 호출 (캐싱 적용으로 딜레이 제거)"""
        try:
            current_row = self.detail_table.currentRow()
            current_col = self.detail_table.currentColumn()

            if current_row < 0:
                return

            # [OPTIMIZE] 팝업 인스턴스 싱글톤 적용 (최초 1회만 생성)
            if self.reference_popup is None:
                from database_reference_popup import DatabaseReferencePopup

                print("[DEBUG] Initializing Reference DB Popup (One-time)")
                # [FIX] self(QDialog)를 부모로 전달하되 parent_popup으로 별도 설정
                self.reference_popup = DatabaseReferencePopup(self)
                self.reference_popup.parent_popup = self  # 명시적 설정

            # 창 표시 데이터 준비 (현재 행/열 동기화)
            self.reference_popup.prepare_show(
                current_row, current_col, self.detail_table
            )

            # 실행 (재사용)
            self.reference_popup.exec()

        except ImportError as e:
            print(f"[WARNING] DatabaseReferencePopup not found: {e}")
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "알림", "자료사전 조회 모듈을 찾을 수 없습니다.")
        except Exception as e:
            print(f"[ERROR] Failed to show reference DB popup: {e}")
            import traceback

            traceback.print_exc()

    def _toggle_multi_selection(self):
        """F5: 다중 선택 모드 토글"""
        current_mode = self.detail_table.selectionMode()
        if current_mode == QTableWidget.SelectionMode.ExtendedSelection:
            self.detail_table.setSelectionMode(
                QTableWidget.SelectionMode.SingleSelection
            )
            print("[DEBUG] Selection Mode: Single")
        else:
            self.detail_table.setSelectionMode(
                QTableWidget.SelectionMode.ExtendedSelection
            )
            print("[DEBUG] Selection Mode: Extended (Multi)")

    def _copy_selection(self):
        """F6: 선택 데이터를 내부 클립보드에 복사"""
        from piece_file_manager import PieceFileManager

        cols_info = {"W": 0, "CODE": 1, "산출목록": 2, "단위수식": 3, "계": 4}
        self._internal_clipboard = PieceFileManager.extract_selected_rows(
            self.detail_table, cols_info
        )
        print(
            f"[DEBUG] Selection copied to internal clipboard: {len(self._internal_clipboard)} items"
        )

    def _paste_selection(self):
        """F7: 클립보드 데이터를 현재 행에 붙여넣기"""
        if not self._internal_clipboard:
            return

        current_row = self.detail_table.currentRow()
        if current_row < 0:
            current_row = self.detail_table.rowCount()

        from piece_file_manager import PieceFileManager

        cols_info = {"W": 0, "CODE": 1, "산출목록": 2, "단위수식": 3, "계": 4}

        # 붙여넣기 수행
        PieceFileManager.insert_piece_data(
            self.detail_table, self._internal_clipboard, current_row, cols_info
        )

        # W 상태 재검증
        self._verify_all_codes()
        print(
            f"[DEBUG] Pasted {len(self._internal_clipboard)} items from internal clipboard"
        )

    def _cut_selection(self):
        """F4: 선택 데이터 이동 (복사 후 삭제)"""
        self._copy_selection()
        if self._internal_clipboard:
            self._delete_selected_rows()
            print("[DEBUG] Cut operation completed")

    def _delete_selected_rows(self):
        """Ctrl+Y: 선택된 행들을 삭제"""
        ranges = self.detail_table.selectedRanges()
        if not ranges:
            return

        # 삭제 중 인덱스 꼬임 방지를 위해 역순 처리
        rows_to_delete = set()
        for r in ranges:
            for row in range(r.topRow(), r.bottomRow() + 1):
                rows_to_delete.add(row)

        self.detail_table.blockSignals(True)
        for row in sorted(list(rows_to_delete), reverse=True):
            self.detail_table.removeRow(row)
        self.detail_table.blockSignals(False)

        print(f"[DEBUG] Deleted {len(rows_to_delete)} rows")

    def _insert_row_above(self):
        """Ctrl+N: 현재 행 위에 새 행 삽입"""
        current_row = self.detail_table.currentRow()
        if current_row < 0:
            current_row = 0

        self.detail_table.blockSignals(True)
        self.detail_table.insertRow(current_row)
        # 기본 아이템 생성 (W 마커 초기화 등 위해)
        for col in range(5):
            self.detail_table.setItem(current_row, col, QTableWidgetItem(""))
        self.detail_table.blockSignals(False)

        # W 마커 초기화 (빈값 처리)
        self._verify_all_codes()
        print(f"[DEBUG] Inserted new row at {current_row}")

    def _save_piece_file(self):
        """[NEW] F9: 선택 행들을 조각파일로 저장"""
        try:
            from piece_file_manager import PieceFileManager

            # detail_table에서 선택된 행 추출
            columns_info = {"W": 0, "CODE": 1, "산출목록": 2, "단위수식": 3, "계": 4}

            selected_data = PieceFileManager.extract_selected_rows(
                self.detail_table, columns_info
            )

            if not selected_data:
                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.warning(self, "알림", "저장할 행을 선택해주세요.")
                return

            # 조각파일 저장
            PieceFileManager.save_piece_file(self, selected_data)

        except Exception as e:
            print(f"[ERROR] Error saving piece file: {e}")
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.critical(self, "오류", f"조각파일 저장 실패:\n{str(e)}")

    def _save_current_state(self):
        """[PHASE 3-3] Ctrl+S: 현재 테이블 상태를 Undo 스택에 저장"""
        # 테이블 데이터 스냅샷 생성
        state_snapshot = []

        for row in range(self.detail_table.rowCount()):
            row_data = []
            for col in range(self.detail_table.columnCount()):
                item = self.detail_table.item(row, col)
                row_data.append(item.text() if item else "")
            state_snapshot.append(row_data)

        # Undo 스택에 추가
        self.undo_stack.append(state_snapshot)

        # 스택 크기 제한
        if len(self.undo_stack) > self.undo_max:
            self.undo_stack.pop(0)

        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(
            self, "저장됨", f"현재 상태가 저장되었습니다. (총 {len(self.undo_stack)}개)"
        )

        print(f"[DEBUG] State saved. Undo stack size: {len(self.undo_stack)}")

    def _restore_previous_state(self):
        """[PHASE 3-3] Ctrl+Z: 이전 저장된 상태 복구"""
        if not self.undo_stack:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "경고", "복구할 이전 상태가 없습니다.")
            return

        # 마지막 저장된 상태 가져오기
        state_snapshot = self.undo_stack.pop()

        # 테이블 복구
        self.detail_table.blockSignals(True)
        self.detail_table.setRowCount(len(state_snapshot))

        for row, row_data in enumerate(state_snapshot):
            for col, text in enumerate(row_data):
                item = QTableWidgetItem(text)
                if col == 1:  # CODE
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.detail_table.setItem(row, col, item)

        self.detail_table.blockSignals(False)

        # 색상 강조 재적용
        QTimer.singleShot(100, self._verify_all_codes)

        # 실시간 합계 업데이트
        QTimer.singleShot(150, self._update_preview_sum)

        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            "복구됨",
            f"이전 상태로 복구되었습니다. (남은 저장 상태: {len(self.undo_stack)}개)",
        )

        print(f"[DEBUG] State restored. Undo stack size: {len(self.undo_stack)}")

    def _auto_complete_product(self, row, product_text):
        """[PHASE 3-4] 산출목록 입력 시 자동 완성 (자료사전 검색 + CODE 자동 입력)"""
        if not product_text.strip():
            return

        # 정확히 일치하는 품목 찾기
        exact_match = None
        partial_matches = []

        search_text = product_text.strip().upper()

        for product, (spec, code) in self.reference_products.items():
            product_upper = product.upper()

            # 정확한 일치
            if product_upper == search_text:
                exact_match = (product, spec, code)
                break

            # 부분 일치 (시작 일치)
            if product_upper.startswith(search_text):
                partial_matches.append((product, spec, code))

        # 일치 결과 적용
        match_found = exact_match or (partial_matches[0] if partial_matches else None)

        if match_found:
            product, spec, code = match_found

            # CODE 자동 입력 (컬럼 1)
            if code:
                self.detail_table.blockSignals(True)
                self.detail_table.setItem(row, 1, QTableWidgetItem(code))
                self.detail_table.item(row, 1).setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )
                self.detail_table.blockSignals(False)

                print(f"[DEBUG] Auto-completed: Product='{product}', CODE='{code}'")

    def _get_autocomplete_suggestions(self, partial_text):
        """[PHASE 3-4] 자동 완성 제안 목록 반환 (최대 10개)"""
        if not partial_text.strip():
            return []

        search_text = partial_text.strip().upper()
        suggestions = []

        for product in self.reference_products.keys():
            if product.upper().startswith(search_text):
                suggestions.append(product)
                if len(suggestions) >= 10:
                    break

        return suggestions

    def _drag_enter_event(self, event):
        """[PHASE 3-5] 드래그 진입 이벤트: .piece 파일 감지"""
        mime_data = event.mimeData()

        # 파일이 드래그되었는지 확인
        if mime_data.hasUrls():
            urls = mime_data.urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.endswith(".piece"):
                    event.acceptProposedAction()
                    return True

        event.ignore()
        return False

    def _drop_event(self, event):
        """[PHASE 3-5] 드롭 이벤트: 조각파일 드롭 시 데이터 삽입"""
        mime_data = event.mimeData()

        if mime_data.hasUrls():
            urls = mime_data.urls()
            for url in urls:
                file_path = url.toLocalFile()

                # .piece 파일 처리
                if file_path.endswith(".piece"):
                    self._load_piece_file_from_path(file_path)
                    event.acceptProposedAction()
                    return True

        event.ignore()
        return False

    def _load_piece_file_from_path(self, file_path):
        """[PHASE 3-5] 경로로부터 조각파일 로드 및 삽입"""
        try:
            from piece_file_manager import PieceFileManager

            # 조각파일 로드
            piece_data = PieceFileManager.load_piece_file_from_path(file_path)

            if not piece_data:
                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.warning(self, "오류", "조각파일을 읽을 수 없습니다.")
                return

            # 현재 선택된 행의 다음 행부터 삽입
            current_row = self.detail_table.currentRow()
            start_row = max(0, current_row + 1)

            # 컬럼 정보
            columns_info = {"W": 0, "CODE": 1, "산출목록": 2, "단위수식": 3, "계": 4}

            # 조각파일 데이터 삽입
            success = PieceFileManager.insert_piece_data(
                self.detail_table, piece_data, start_row, columns_info
            )

            if success:
                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.information(
                    self,
                    "드롭 완료",
                    f"조각파일이 삽입되었습니다. ({len(piece_data)}행)",
                )
                print(f"[DEBUG] Piece file loaded from: {file_path}")

                # 색상 강조 재적용
                QTimer.singleShot(100, self._verify_all_codes)
                QTimer.singleShot(150, self._update_preview_sum)

        except Exception as e:
            print(f"[ERROR] Error loading piece file from path: {e}")
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.critical(self, "오류", f"조각파일 로드 실패:\n{str(e)}")

    # [REMOVED] Duplicate _update_preview_sum

    # ============================================
    # [PHASE 2-3] 재진입 상태 복구 메서드 (Popup 위젯 내부로 이동)
    # ============================================

    def _get_state_file_path(self):
        """상태 파일 저장 경로 반환"""
        app_data = Path.home() / "AppData" / "Local" / "EasyMax"
        app_data.mkdir(parents=True, exist_ok=True)
        # item_name을 파일명으로 사용 (공종명별 상태 분리)
        sanitized_name = re.sub(r'[<>:"/\\|?*]', "_", self.item_name)
        state_file = app_data / f"state_{sanitized_name}.json"
        return state_file

    def save_state(self):
        """팝업의 현재 상태를 저장: 테이블 데이터, 커서, 스크롤 위치, 창 크기"""
        try:
            state = {
                "version": "1.0",
                "window_geometry": {
                    "x": self.x(),
                    "y": self.y(),
                    "width": self.width(),
                    "height": self.height(),
                },
                "detail_table": {
                    "current_row": self.detail_table.currentRow(),
                    "current_col": self.detail_table.currentColumn(),
                    "scroll_v": self.detail_table.verticalScrollBar().value(),
                    "scroll_h": self.detail_table.horizontalScrollBar().value(),
                    "data": [],
                },
                "master_table": {
                    "scroll_v": self.master_table.verticalScrollBar().value(),
                    "scroll_h": self.master_table.horizontalScrollBar().value(),
                },
                "splitter": {"sizes": self.splitter.sizes()},
            }

            # detail_table 데이터 저장
            for row in range(self.detail_table.rowCount()):
                row_data = {}
                for col in range(self.detail_table.columnCount()):
                    item = self.detail_table.item(row, col)
                    row_data[col] = item.text() if item else ""
                state["detail_table"]["data"].append(row_data)

            # 상태 파일에 저장
            state_file = self._get_state_file_path()
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

            print(f"[DEBUG] State saved to {state_file}")

        except Exception as e:
            print(f"[ERROR] Failed to save state: {e}")

    def restore_state(self):
        """저장된 상태를 복구: 테이블 데이터, 커서, 스롤 위치, 창 크기"""
        try:
            state_file = self._get_state_file_path()
            if not state_file.exists():
                print(f"[DEBUG] State file not found: {state_file}")
                return False

            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            # 창 기하학 복구
            if "window_geometry" in state:
                geo = state["window_geometry"]
                self.setGeometry(geo["x"], geo["y"], geo["width"], geo["height"])

            # detail_table 데이터 복구
            if "detail_table" in state:
                detail_state = state["detail_table"]
                detail_data = detail_state.get("data", [])

                # 테이블 크기 조정
                if detail_data:
                    self.detail_table.setRowCount(len(detail_data))

                    # 데이터 복구
                    for row, row_data in enumerate(detail_data):
                        for col, value in row_data.items():
                            col_idx = int(col)
                            if col_idx < self.detail_table.columnCount():
                                item = QTableWidgetItem(value)
                                self.detail_table.setItem(row, col_idx, item)

                    # 색상 강조 재적용
                    QTimer.singleShot(100, self._verify_all_codes)

                # 커서 위치 복구
                current_row = detail_state.get("current_row", 0)
                current_col = detail_state.get("current_col", 0)
                if current_row >= 0 and current_col >= 0:
                    self.detail_table.setCurrentCell(current_row, current_col)

                # 스크롤 위치 복구
                self.detail_table.verticalScrollBar().setValue(
                    detail_state.get("scroll_v", 0)
                )
                self.detail_table.horizontalScrollBar().setValue(
                    detail_state.get("scroll_h", 0)
                )

            # master_table 스크롤 복구
            if "master_table" in state:
                master_state = state["master_table"]
                self.master_table.verticalScrollBar().setValue(
                    master_state.get("scroll_v", 0)
                )
                self.master_table.horizontalScrollBar().setValue(
                    master_state.get("scroll_h", 0)
                )

            # splitter 크기 복구
            if "splitter" in state:
                splitter_state = state["splitter"]
                sizes = splitter_state.get("sizes", [])
                if sizes and len(sizes) == 2:
                    self.splitter.setSizes(sizes)

            print(f"[DEBUG] State restored from {state_file}")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to restore state: {e}")
            return False

    def closeEvent(self, event):
        """팝업 종료 시 상태 저장"""
        self.save_state()
        super().closeEvent(event)

    def showEvent(self, event):
        """팝업 표시 시 상태 복구 (첫 진입 제외)"""
        super().showEvent(event)
        # detail_table에 데이터가 없으면 상태 복구 시도
        if self.detail_table.rowCount() == 0:
            QTimer.singleShot(100, self.restore_state)


class LightingPowerManager:
    """
    을지 산출내역서 - 전등/전열 기능 관리자
    """

    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        self.panel = None
        self.list_widget = None
        self.file_path = r"D:\오아시스\사용자목록\전등,전열 산출공종.txt"

    def create_side_panel(self):
        """을지 우측에 배치될 산출공종 패널 생성"""
        self.panel = QFrame()
        self.panel.setFixedWidth(250)
        self.panel.setStyleSheet(
            "background-color: #f8f9fa; border-left: 1px solid #dee2e6;"
        )
        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 헤더
        header = QLabel("산출공종")
        header.setFixedHeight(30)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(
            "background-color: #e9ecef; color: #495057; font-family: '새굴림'; font-size: 11pt;"
        )
        layout.addWidget(header)

        # 리스트 위젯
        self.list_widget = QListWidget()
        self.list_widget.setFont(QFont("새굴림", 11))
        self.list_widget.setStyleSheet("""
            QListWidget { border: none; background-color: white; font-size: 11pt; }
            QListWidget::item { height: 22px; padding-left: 5px; border-bottom: 1px solid #f1f3f5; }
            QListWidget::item:hover { background-color: #f1f3f5; }
            QListWidget::item:selected { background-color: #e7f5ff; color: #007bff; }
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

        self.panel.hide()  # 초기에는 숨김
        self._is_opening_popup = False  # [NEW] 크래시 방지용 가드 변수
        return self.panel

    def toggle_panel(self):
        """패널 표시/숨김 토글 및 데이터 로드"""
        if self.panel.isVisible():
            self.panel.hide()
        else:
            self._load_list_data()
            self.panel.show()
            # [FIX] 스플리터 크기 강제 설정 (표시 시 시야 확보)
            if hasattr(self.parent_tab, "eulji_splitter"):
                # 전체 너비를 고려하여 8:2 비율 또는 고정 크기 배분
                total_w = self.parent_tab.eulji_splitter.width()
                if total_w > 300:
                    self.parent_tab.eulji_splitter.setSizes([total_w - 250, 250])
                else:
                    self.parent_tab.eulji_splitter.setSizes([800, 250])

    def _load_list_data(self):
        """파일에서 리스트 데이터 로드"""
        print(f"[DEBUG] Loading lighting/power list from: {self.file_path}")
        if not os.path.exists(self.file_path):
            print(f"[DEBUG] File not found: {self.file_path}")
            self.list_widget.clear()
            self.list_widget.addItem(f"파일 없음: {self.file_path}")
            return

        try:
            self.list_widget.clear()
            # 한글 인코딩 대응 (UTF-8 우선, 실패 시 CP949)
            lines = []
            try:
                print("[DEBUG] Attempting UTF-8 read")
                with open(self.file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                print("[DEBUG] UTF-8 failed, attempting CP949 read")
                with open(self.file_path, "r", encoding="cp949") as f:
                    lines = f.readlines()

            print(f"[DEBUG] Read {len(lines)} lines")
            for line in lines:
                text = line.strip()
                if text:
                    self.list_widget.addItem(text)
        except Exception as e:
            print(f"[DEBUG] Error loading list: {e}")
            self.list_widget.addItem(f"로드 오류: {e}")

    def _on_item_clicked(self, item):
        """리스트 아이템 클릭 시 산출목록 명칭 복사 및 팝업 호출"""
        if self._is_opening_popup:
            print("[DEBUG] Popup already opening, ignore click")
            return

        if "파일 없음" in item.text() or "로드 오류" in item.text():
            return

        self._is_opening_popup = True  # 가드 설정
        # [FIX] 동기적 테이블 수정(setItem)을 모두 제거하고,
        # 지연 실행 메서드로 이관하여 commitData 충돌 방지
        QTimer.singleShot(100, lambda: self._process_selection_and_open(item.text()))

    def _process_selection_and_open(self, title):
        """테이블 상태 정리, 선행 입력 후 팝업 호출"""
        table = self.parent_tab.eulji_table

        # 편집 강제 종료 (포커스 이동)
        if table.state() == QTableWidget.State.EditingState:
            table.setCurrentItem(None)

        # [NEW] 팝업 띄우기 전에 메인 테이블에 즉시 입력 (사용자 요청)
        current_row = table.currentRow()

        # 선택된 행이 없으면 빈 행 탐색 (1행부터 채우기 위함)
        if current_row < 0:
            found_empty = False
            item_col = self.parent_tab.EULJI_COLS["ITEM"]

            for r in range(table.rowCount()):
                item = table.item(r, item_col)
                if not item or not item.text().strip():
                    current_row = r
                    found_empty = True
                    break

            # 빈 행이 없으면 맨 끝에 추가
            if not found_empty:
                current_row = table.rowCount()
                table.insertRow(current_row)

        # 해당 행에 텍스트 입력 (시각적 피드백)
        table.blockSignals(True)
        table.setItem(
            current_row, self.parent_tab.EULJI_COLS["ITEM"], QTableWidgetItem(title)
        )
        table.blockSignals(False)

        # 스크롤 이동
        table.scrollToItem(table.item(current_row, 0))

        # 팝업 호출 (행 인덱스 전달)
        self._open_popup(title, current_row)

    def _open_popup(self, title, target_row, saved_data=None):
        """실제 팝업 오픈 및 데이터 처리"""
        try:
            popup = LightingPowerPopup(
                self.parent_tab.main_window, title, parent_tab=self.parent_tab
            )

            popup.current_row = target_row

            # [Step 11] 저장 데이터가 있으면 복구 시도
            if not saved_data:
                # 전달받은 데이터가 없으면 직접 Gapji 테이블에서 확인 (백업용)
                item = self.parent_tab.gapji_table.item(target_row, 3)  # GONGJONG_COL
                if item:
                    saved_data = item.data(Qt.ItemDataRole.UserRole)

            if saved_data:
                popup.load_from_saved_state(saved_data)

            if popup.exec() == QDialog.DialogCode.Accepted:
                # [Step 12] 팝업에서 생성된 전체 상태 페이로드 가져오기
                save_payload = getattr(popup, "last_save_payload", None)

                if save_payload:
                    table = self.parent_tab.eulji_table

                    # [FIX] 전달받은 target_row 사용 (데이터 소실 방지)
                    current_row = target_row
                    # 혹시 그 사이 행이 삭제되었을 수도 있으므로 유효성 체크
                    if current_row >= table.rowCount():
                        current_row = table.rowCount()
                        table.insertRow(current_row)

                    # [중요] 단일 행에 "조명기구 Type산출" 입력 (1식)
                    table.blockSignals(True)

                    # 1. 산출목록 (ITEM) -> "조명기구 Type산출" (고정)
                    table.setItem(
                        current_row,
                        self.parent_tab.EULJI_COLS["ITEM"],
                        QTableWidgetItem("조명기구 Type산출"),
                    )

                    # [Step 12] 페이로드에서 합계 금액 가져오기
                    total_sum = save_payload.get("final_total", 0.0)

                    # 2. 산출수식 (FORMULA) -> 총 합계값
                    sum_text = (
                        f"{int(total_sum)}"
                        if total_sum == int(total_sum)
                        else f"{total_sum:g}"
                    )
                    table.setItem(
                        current_row,
                        self.parent_tab.EULJI_COLS["FORMULA"],
                        QTableWidgetItem(sum_text),
                    )

                    # 3. 단위 (UNIT) -> "식"
                    unit_item = QTableWidgetItem("식")
                    unit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    table.setItem(
                        current_row, self.parent_tab.EULJI_COLS["UNIT"], unit_item
                    )

                    # 4. 계 (TOTAL) -> "1"
                    qty_item = QTableWidgetItem("1")
                    qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    table.setItem(
                        current_row, self.parent_tab.EULJI_COLS["TOTAL"], qty_item
                    )

                    # [Step 12] 상세 데이터 전체를 UserRole에 영구 저장 (재진입용 핵심)
                    item_widget = table.item(
                        current_row, self.parent_tab.EULJI_COLS["ITEM"]
                    )
                    item_widget.setData(Qt.ItemDataRole.UserRole, save_payload)

                    table.blockSignals(False)
                    # [FIX] 해당 행으로 스크롤 이동 (사용자 시야 확보)
                    table.scrollToItem(table.item(current_row, 0))

                    # [FIX] 데이터 저장 트리거 (시그널 차단했으므로 수동 저장)
                    # 현재 활성화된 공종명을 알아내어 저장
                    if (
                        hasattr(self.parent_tab, "current_gongjong")
                        and self.parent_tab.current_gongjong
                    ):
                        self.parent_tab._save_eulji_data(
                            self.parent_tab.current_gongjong
                        )
                        self.parent_tab._update_gapji_marker(
                            self.parent_tab.current_gongjong
                        )

                    cached_count = len(save_payload.get("master_details_cache", {}))
                    print(
                        f"[DEBUG] Applied single row with {cached_count} master types."
                    )
        finally:
            self._is_opening_popup = False  # 가드 해제

    def edit_row(self, row):
        """기존 을지 행 편집 (재진입)"""
        table = self.parent_tab.eulji_table
        item_widget = table.item(row, self.parent_tab.EULJI_COLS["ITEM"])

        if not item_widget:
            return

        title = item_widget.text()
        # [Step 11] UserRole에서 저장된 상세 데이터 가져오기
        saved_data = item_widget.data(Qt.ItemDataRole.UserRole)

        # 팝업 호출 (저장된 데이터 전달)
        self._open_popup(title, row, saved_data=saved_data)

    def edit_gapji_row(self, row):
        """[Step 11] 산출내역서(갑지) 행에서 TAB 키 재진입"""
        table = self.parent_tab.gapji_table
        # GONGJONG_COL (Index 3)에 품목명과 상세 데이터가 저장됨
        item_widget = table.item(row, 3)

        if not item_widget:
            return

        title = item_widget.text()
        saved_data = item_widget.data(Qt.ItemDataRole.UserRole)

        # 팝업 호출 (저장된 데이터 전달)
        self._open_popup(title, row, saved_data=saved_data)

    # [REDUNDANT REMOVED] _show_reference_db_popup was moved to LightingPowerPopup class.

    # [REMOVED] State/Event methods relocated to LightingPowerPopup
