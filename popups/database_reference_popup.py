# -*- coding: utf-8 -*-
"""
자료사전 DB 팝업 (3차 창)
Database Reference Popup Window
Model-View 기반의 고성능 대용량 데이터 로딩 시스템
"""

import sqlite3
import re
import os
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableView, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QFrame, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt, QEvent, QAbstractTableModel, QModelIndex, QVariant, QTimer
from PyQt6.QtGui import QColor, QFont, QPalette
from utils.column_settings import CleanStyleDelegate

class ReferenceTableModel(QAbstractTableModel):
    """자료사전 대용량 데이터를 위한 고성능 가상 모델 (19,000+ 행 대응)"""
    def __init__(self, data=None):
        super().__init__()
        self._raw_data = data if data else []
        self._headers = ["번호", "명칭(Description)", "규격(Size)", "단위", "산출수량"]
        # 수량 입력을 저장할 딕셔너리 {row_idx: qty_text}
        self._qty_inputs = {}
        # 검색용 통합 데이터 캐시
        self._search_blobs = []
        self._prepare_search_blobs()

    def _prepare_search_blobs(self):
        """검색 성능 극대화를 위한 검색 데이터 인덱싱"""
        self._search_blobs = []
        for row in self._raw_data:
            # 대상 및 가공 규칙:
            # 1. 목록2(6) ~ 목록6(10), 약칭(11), 산출목록(13), 검색목록(14)
            # 2. '+' 기호를 공백으로 치환하여 단어 단위 검색 지원
            target_indices = [6, 7, 8, 9, 10, 11, 13, 14]
            search_parts = []
            for idx in target_indices:
                if idx < len(row):
                    val = str(row[idx]) if row[idx] is not None else ""
                    search_parts.append(val.replace('+', ' '))
            
            # 기본 검색 대상 (품명, 규격, CODE) 추가
            search_parts.extend([str(row[1]), str(row[2]), str(row[4])])
            
            combined = " ".join(search_parts).lower()
            self._search_blobs.append(combined)

    def rowCount(self, parent=QModelIndex()):
        return len(self._raw_data)

    def columnCount(self, parent=QModelIndex()):
        return 5  # 번호, 명칭, 규격, 산출수량, 단위

    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return QVariant()

    def data(self, index, role):
        if not index.isValid():
            return QVariant()

        row = index.row()
        col = index.column()

        # 텍스트 출력
        if role == Qt.ItemDataRole.DisplayRole:
            # col 4: 산출수량 (입력 컬럼)
            if col == 4:  # 산출수량 (입력 컬럼)
                return self._qty_inputs.get(row, "")
            
            # 컬럼 매핑 (SQL 결과 순서 대응)
            # 0:ID, 1:품명, 2:규격, 3:단위, 4:CODE, ..., 11:약칭
            mapping = {
                0: 0,   # 번호 (ID)
                1: 13,  # [FIX] 명칭(Description) 대신 산출목록(13) 표시
                2: 2,   # 규격(Size)
                3: 3    # 단위
            }
            raw_idx = mapping.get(col, -1)
            if raw_idx == -1:
                return ""
            
            # [NEW] 산출목록(13)이 비어있는 경우 품명(1)으로 대체 출력
            if col == 1:
                val = self._raw_data[row][13] if (len(self._raw_data[row]) > 13 and self._raw_data[row][13]) else self._raw_data[row][1]
                return str(val) if val is not None else ""
                
            return str(self._raw_data[row][raw_idx]) if self._raw_data[row][raw_idx] is not None else ""

        # 텍스트 색상
        if role == Qt.ItemDataRole.ForegroundRole:
            if col == 4:  # 산출수량 입력 컬럼
                return QColor("#008800") # 입력 수식 밝고 진한 녹색
            return QColor(0, 102, 0) # 기본 데이터 진한 녹색

        # 정렬
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 3:  # 단위 컬럼
                return Qt.AlignmentFlag.AlignCenter
            if col == 4:  # 산출수량 컬럼 - 왼쪽 정렬 (사용자 요청)
                return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        return QVariant()

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        """산출수량 컬럼 데이터 수정 지원 (자동 누적 입력 로직 포함)"""
        if index.isValid() and index.column() == 4 and role == Qt.ItemDataRole.EditRole:
            row = index.row()
            new_val = str(value).strip()
            existing_val = self._qty_inputs.get(row, "").strip()
            
            # [NEW] 자동 누적 입력 로직
            # 기존 값이 있고, 새로운 값도 입력되었으며, 기존 값과 새로운 값이 다를 경우
            # (단, 새로운 값이 이미 기존 값을 포함하는 수식 형태로 들어온 경우는 제외)
            if existing_val and new_val and existing_val != new_val:
                # 숫자 또는 사칙연산 기호로 시작하는 경우에만 '+' 자동 누적
                # (특수 명령 '===' 등은 누적에서 제외)
                import re
                if re.match(r'^[0-9.]', new_val) and not new_val.startswith(existing_val):
                    # 기존 값이 수식인 경우 괄호 처리 고려 가능하나, 
                    # 사용자 요청에 따라 단순하게 '+'로 연결
                    new_val = f"{existing_val}+{new_val}"
            
            self._qty_inputs[row] = new_val
            self.dataChanged.emit(index, index, [role])
            return True
        return False

    @property
    def is_main_sheet(self):
        """메인 시트 모드인지 판별 (동적)"""
        return hasattr(self.parent_popup, "eulji_table") and not hasattr(self.parent_popup, "UNIT_PRICE_COLS")

    @property
    def is_lighting_calc(self):
        """전등수량 산출 모드인지 판별 (동적)"""
        return getattr(self.parent_popup, 'item_name', '') == "전등수량(갯수)산출"

    @property
    def is_unit_price_popup(self):
        """산출일위표 팝업 모드인지 판별 (동적)"""
        return hasattr(self.parent_popup, "UNIT_PRICE_COLS")

    def clear_all_qty(self):
        """모든 수량 입력 데이터 초기화 (신규 프로젝트/공종용)"""
        self._qty_inputs = {}
        self.layoutChanged.emit()

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        
        # 산출수량(4) 컬럼만 편집 가능
        if index.column() == 4:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

class DatabaseReferencePopup(QDialog):
    """
    자료사전 DB 팝업 (3차 창)
    고성능 Model-View 방식으로 재설계됨
    """
    # 메모리 캐싱을 위한 외부 가용한 데이터 저장소
    _CACHE_DATA = None

    def __init__(self, parent_popup):
        # [FIX] 부모가 QWidget이 아닌 경우를 위해 부모 위젯 추출
        from PyQt6.QtWidgets import QWidget
        parent_widget = parent_popup if isinstance(parent_popup, QWidget) else None
        super().__init__(parent_widget)
        self.setWindowTitle("자료사전")
        self.parent_popup = parent_popup
        self.current_row = -1
        self.current_col = -1
        
        # 경로 및 설정
        self.original_mapping_path = r"D:\오아시스\data\manual_mapping.json"
        # [NEW] 호출 모드 판별 로직 (동적 프로퍼티로 이관)
        
        # UI 및 데이터 초기화
        self._adjust_window_geometry()
        self._init_ui()
        self._load_reference_data()

    @property
    def is_main_sheet(self):
        """부모가 을지(상세산출) 탭인지 판별"""
        return hasattr(self.parent_popup, "eulji_table") and not hasattr(self.parent_popup, "UNIT_PRICE_COLS")

    @property
    def is_unit_price_popup(self):
        """부모가 산출일위표 팝업인지 판별"""
        return hasattr(self.parent_popup, "UNIT_PRICE_COLS")

    @property
    def is_lighting_calc(self):
        """부모가 전등/전열 산출 팝업인지 판별"""
        # lighting_power_manager.py의 LightingPowerPopup 클래스 확인
        return hasattr(self.parent_popup, 'master_table') and hasattr(self.parent_popup, 'detail_table')

    @property
    def ref_db_path(self):
        """부모가 가진 DB 경로를 우선 참조, 없으면 기본값 사용"""
        return getattr(self.parent_popup, 'ref_db_path', r"D:\오아시스\data\자료사전.db")

    def prepare_show(self, current_row, current_col):
        """창을 표시하기 전에 필요한 정보를 갱신 (Parent와 동기화)"""
        self.current_row = current_row
        self.current_col = current_col
        
        # 상단 리스트 갱신 (현재 행 기준으로 자동 선택) - 세부산출 모드에서만 수행
        if not self.is_main_sheet:
            self._populate_product_list(target_row=current_row)
        else:
            # 메인 시트 모드에서는 상단 바 숨김
            if hasattr(self, 'top_container'):
                self.top_container.hide()
        
        # 뷰 상태 초기화 및 포커스 강제 부여
        if self.model and self.model.rowCount() > 0:
            index = self.model.index(0, 4) # 첨 행 산출수량 컬럼
            self.reference_table.setCurrentIndex(index)
            self.reference_table.setFocus() # 강제 포커스
            self.reference_table.scrollToTop()
        
        self.reference_table.viewport().update()
        self.status_label.setText("자료사전 준비 완료 (Model-View 입력 대기)")

    def _adjust_window_geometry(self):
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().availableGeometry()
        # 테이블(872) + 미세 여백 = 약 882px
        total_width = 882
        y_pos = screen.top() + 50
        usable_height = screen.height() - 100
        self.setGeometry(screen.center().x() - total_width // 2, y_pos, total_width, usable_height)
        self.setMinimumHeight(400) 

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)  # 여백 축소
        main_layout.setSpacing(3)
        
        # [상단] 매칭 영역 - 전체를 하나의 프레임으로 감싸기
        self.top_container = QFrame()
        self.top_container.setFixedHeight(30) # 높이 상향 (26 -> 30)
        # 테이블 너비와 완벽 일치: 30(헤더) + 820(컬럼) + 20(스크롤바) + 2(테두리) = 872px
        self.top_container.setFixedWidth(872)
        self.top_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #707070;
            }
        """)
        if self.is_main_sheet:
            self.top_container.hide()
            
        top_h_layout = QHBoxLayout(self.top_container)
        top_h_layout.setContentsMargins(0, 0, 0, 0)
        top_h_layout.setSpacing(0)
        
        # [NEW] 행 헤더 오프셋 (30px)
        header_spacer = QLabel()
        header_spacer.setFixedWidth(30)
        header_spacer.setFixedHeight(28) # 내부 높이 확보
        header_spacer.setStyleSheet("border: none; border-right: 1px solid #707070; background-color: #e1e1e1;")
        top_h_layout.addWidget(header_spacer)
        
        # 매칭 레이블
        top_label = QLabel("매칭")
        top_label.setFixedWidth(60)
        top_label.setFixedHeight(28) # 높이 보정
        top_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_label.setStyleSheet("""
            QLabel {
                background-color: #e1e1e1;
                border: none;
                border-right: 1px solid #707070;
                font-family: '새굴림';
                font-size: 10pt;
                font-weight: normal;
                color: black;
                padding: 0px;
            }
        """)
        top_h_layout.addWidget(top_label)
        
        # 선택 표시 레이블 (텍스트 영역)
        self.product_display = QLabel("")
        self.product_display.setFixedHeight(28) # 높이 보정
        self.product_display.setFont(QFont("새굴림", 10))
        self.product_display.setStyleSheet("""
            QLabel {
                background-color: white;
                border: none;
                color: black;
                padding-left: 10px;
                letter-spacing: 0px;
            }
        """)
        top_h_layout.addWidget(self.product_display, 1)
        
        # 위/아래 버튼 컨테이너
        nav_btn_container = QFrame()
        nav_btn_container.setFixedWidth(61) 
        nav_btn_container.setFixedHeight(28) # 높이 정밀 고정
        nav_btn_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: none;
                border-left: 1px solid #707070;
            }
        """)
        nav_btn_layout = QHBoxLayout(nav_btn_container)
        nav_btn_layout.setContentsMargins(0, 0, 0, 0) # 여백 제거
        nav_btn_layout.setSpacing(0)
        
        # [평면 화] 아래(▼) 버튼
        self.nav_down_btn = QPushButton("▼")
        self.nav_down_btn.setFixedSize(30, 28) # 너비/높이 고정으로 잘림 방지
        self.nav_down_btn.setFont(QFont("새굴림", 16))
        self.nav_down_btn.clicked.connect(self._on_nav_down)
        self.nav_down_btn.setStyleSheet("""
            QPushButton { 
                background-color: #f0f0f0; border: none; border-right: 1px solid #707070; 
                color: black; padding: 0px; margin: 0px;
            }
            QPushButton:hover { background-color: #e5e5e5; }
            QPushButton:pressed { background-color: #d0d0d0; }
        """)
        nav_btn_layout.addWidget(self.nav_down_btn)

        # [평면 화] 위(▲) 버튼
        self.nav_up_btn = QPushButton("▲")
        self.nav_up_btn.setFixedSize(30, 28) # 너비/높이 고정으로 잘림 방지
        self.nav_up_btn.setFont(QFont("새굴림", 16))
        self.nav_up_btn.clicked.connect(self._on_nav_up)
        self.nav_up_btn.setStyleSheet("""
            QPushButton { 
                background-color: #f0f0f0; border: none; 
                color: black; padding: 0px; margin: 0px;
            }
            QPushButton:hover { background-color: #e5e5e5; }
            QPushButton:pressed { background-color: #d0d0d0; }
        """)
        nav_btn_layout.addWidget(self.nav_up_btn)
        
        # [순서 교정] 버튼을 먼저 추가하고, 마지막에 스크롤바 여백(20px) 추가
        top_h_layout.addWidget(nav_btn_container)
        
        # 버튼 영역 뒤에 스크롤바 여백(20px)
        btn_tail_spacer = QLabel()
        btn_tail_spacer.setFixedWidth(20)
        btn_tail_spacer.setFixedHeight(28)
        btn_tail_spacer.setStyleSheet("background-color: #e1e1e1; border: none; border-left: 1px solid #707070;")
        top_h_layout.addWidget(btn_tail_spacer)
        
        # 내부 데이터 저장용 리스트
        self._product_items = []  # (text, row_data) 튜플 리스트
        self._current_product_index = -1
        
        main_layout.addWidget(self.top_container)
        
        # [중앙] 자료사전 테이블 (QTableView)
        self.reference_table = QTableView()
        self.model = None
        
        # 폰트 설정 (세부산출조서와 동일하게)
        table_font = QFont("새굴림", 11)
        self.reference_table.setFont(table_font)
        self.reference_table.horizontalHeader().setFont(QFont("새굴림", 11))
        self.reference_table.verticalHeader().setFont(QFont("새굴림", 11))
        self.reference_table.verticalHeader().setDefaultSectionSize(18) # 20 -> 18 (11pt 폰트에 맞춰 상하 1px 여백)
        self.reference_table.verticalHeader().setFixedWidth(30)
        self.reference_table.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # [STYLE] 테이블 스타일 정밀 보정 (셀 여백 제거 추가)
        self.reference_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.reference_table.setStyleSheet("""
            QTableView {
                border: 1px solid #707070;
                gridline-color: #d0d0d0;
                background-color: white;
            }
            QTableView::item {
                padding: 0px;
                margin: 0px;
                border: none;
            }
            QHeaderView::section {
                background-color: #e1e1e1;
                border: 1px solid #707070;
                padding: 0px;
                margin: 0px;
            }
            QScrollBar:vertical {
                border: 1px solid #c0c0c0;
                background: #f1f1f1;
                width: 20px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #c1c1c1;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a8a8a8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        # 테이블 너비 고정: 30(헤더) + 820(컬럼) + 20(스크롤바) + 2(테두리) = 872
        self.reference_table.setFixedWidth(872)
        
        self.reference_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectItems)
        self.reference_table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        # [NEW] 헤더 클릭 시 행/열 전체 선택 연결
        self.reference_table.horizontalHeader().sectionClicked.connect(self.reference_table.selectColumn)
        self.reference_table.verticalHeader().sectionClicked.connect(self.reference_table.selectRow)
        self.reference_table.setPalette(self._get_clean_palette())
        self.reference_table.setItemDelegate(CleanStyleDelegate(self.reference_table))
        # [NEW] 모던 스타일 CSS 제거 (롤백)
        self.reference_table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.reference_table.setEditTriggers(QTableView.EditTrigger.AnyKeyPressed | QTableView.EditTrigger.DoubleClicked | QTableView.EditTrigger.EditKeyPressed)
        self.reference_table.installEventFilter(self)
        self.installEventFilter(self) # 팝업 전체에 대해 키 이벤트 감지
        
        # [NEW] 컬럼 너비 설정 (5컬럼 구조 대응)
        self.reference_table.setColumnWidth(0, 60)   # 번호
        self.reference_table.setColumnWidth(1, 220)  # 명칭(Description)
        self.reference_table.setColumnWidth(2, 350)  # 규격(Size)
        self.reference_table.setColumnWidth(3, 40)   # 단위
        self.reference_table.setColumnWidth(4, 150)  # 산출수량 (입력 컬럼)
        
        # 수평 스크롤바 숨김 - 여백 없이 꼭 차게
        self.reference_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        main_layout.addWidget(self.reference_table, 1)
        
        # [하단] 상태바 및 버튼
        bottom_frame = QFrame()
        bottom_layout = QHBoxLayout(bottom_frame)
        
        self.status_label = QLabel("준비 중...")
        self.status_label.setFont(QFont("새굴림", 11))
        self.status_label.setStyleSheet("color: #666; margin-left:10px;")
        bottom_layout.addWidget(self.status_label)
        
        bottom_layout.addStretch()
        
        send_btn = QPushButton("보내기")
        send_btn.setFont(QFont("굴림체", 11))
        send_btn.setFixedSize(100, 32)
        send_btn.clicked.connect(self._on_send_clicked)
        bottom_layout.addWidget(send_btn)
        
        close_btn = QPushButton("닫기")
        close_btn.setFont(QFont("굴림체", 11))
        close_btn.setFixedSize(100, 32)
        close_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(close_btn)
        
        main_layout.addWidget(bottom_frame)

    def _get_clean_palette(self):
        palette = self.palette()
        trans = QColor(Qt.GlobalColor.transparent)
        for g in [QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled]:
            palette.setColor(g, QPalette.ColorRole.Highlight, trans)
            palette.setColor(g, QPalette.ColorRole.HighlightedText, palette.color(g, QPalette.ColorRole.Text))
        return palette

    def _load_reference_data(self):
        """DB에서 데이터를 로드하여 모델에 바인딩"""
        if self.model and self.model.rowCount() > 0:
            return
        
        if not os.path.exists(self.ref_db_path):
            QMessageBox.critical(self, "오류", f"DB 파일을 찾을 수 없습니다: {self.ref_db_path}")
            return
        
        try:
            if DatabaseReferencePopup._CACHE_DATA is None:
                conn = sqlite3.connect(self.ref_db_path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("""
                    SELECT ID, 품명, 규격, 단위, CODE,
                           그룹, 목록2, 목록3, 목록4, 목록5, 목록6, 약칭, W, 산출목록, 검색목록
                    FROM [자료사전] WHERE 품명 != '자료사전' ORDER BY ID
                """)
                rows = cursor.fetchall()
                DatabaseReferencePopup._CACHE_DATA = rows
                conn.close()
            
            self.model = ReferenceTableModel(DatabaseReferencePopup._CACHE_DATA)
            self.reference_table.setModel(self.model)
            
            # 컬럼 너비 설정 (ID, 명칭, 규격, 단위, 산출수량)
            widths = [60, 220, 350, 40, 150]
            for i, w in enumerate(widths):
                self.reference_table.setColumnWidth(i, w)
            
            self.status_label.setText(f"자료 로드 완료: {len(DatabaseReferencePopup._CACHE_DATA)}개 품목")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"데이터 로드 중 오류 발생: {e}")

    def _populate_product_list(self, target_row=None):
        """산출일위 테이블에서 품목 리스트 추출
        
        Args:
            target_row: 자동 선택할 대상 행 인덱스 (None이면 첫 번째 항목 선택)
        """
        try:
            self._product_items = []
            self._current_product_index = -1
            
            if not self.is_lighting_calc:
                self.product_display.setText("")
                self.nav_up_btn.setEnabled(False)
                self.nav_down_btn.setEnabled(False)
                return
                
            # 부모가 detail_table 또는 table을 가질 수 있음에 대응
            detail_table = getattr(self.parent_popup, 'detail_table', None)
            if not detail_table:
                detail_table = getattr(self.parent_popup, 'table', None)
            
            if not detail_table:
                return
            target_index = 0  # 기본값: 첫 번째 항목
            
            for row in range(detail_table.rowCount()):
                item = detail_table.item(row, 2)
                if item and item.text().strip():
                    # target_row와 일치하는 항목의 인덱스 저장
                    if target_row is not None and row == target_row:
                        target_index = len(self._product_items)
                    self._product_items.append((item.text().strip(), row))
            
            # target_row에 해당하는 항목 선택 (없으면 첫 번째 항목)
            if self._product_items:
                self._current_product_index = target_index
                self._update_product_display()
            else:
                self.product_display.setText("")
                
        except Exception as e:
            print(f"[ERROR] Product list error: {e}")

    def _update_product_display(self):
        """현재 선택된 품목 표시 업데이트"""
        if 0 <= self._current_product_index < len(self._product_items):
            text, row_data = self._product_items[self._current_product_index]
            display_text = f"[{self._current_product_index + 1}/{len(self._product_items)}] {text}"
            self.product_display.setText(display_text)
            self.active_target_row = row_data
            self.status_label.setText(f"대상 선택: {text}")

    def _on_nav_up(self):
        """위 버튼: 이전 품목으로 이동"""
        if self._product_items and self._current_product_index > 0:
            self._current_product_index -= 1
            self._update_product_display()

    def _on_nav_down(self):
        """아래 버튼: 다음 품목으로 이동"""
        if self._product_items and self._current_product_index < len(self._product_items) - 1:
            self._current_product_index += 1
            self._update_product_display()

    def _on_product_selected(self, item):
        """호환성 유지용 (기존 코드와의 호환)"""
        pass

    def _send_all_and_close(self):
        """ESC 키: 입력된 모든 수량 데이터 전송 후 팝업 종료"""
        try:
            if not self.model:
                self.hide()
                return
            
            sent_count = 0  # [FIX] 초기화 누락 수정
            # [NEW] 부모 타입에 따른 처리
            if hasattr(self.parent_popup, "detail_table"):
                detail_table = self.parent_popup.detail_table
                
                # 입력된 모든 수량 데이터 처리
                for row, qty_text in list(self.model._qty_inputs.items()):
                    qty_text = qty_text.strip()
                    if not qty_text or not self._is_numeric(qty_text):
                        continue
                    
                    try:
                        raw_row = self.model._raw_data[row]
                        output_name = str(raw_row[13]) if (len(raw_row) > 13 and raw_row[13]) else str(raw_row[1])
                        code = str(raw_row[4])
                        
                        target_row = self.current_row + sent_count
                        
                        # 기존 행이 채워져 있으면 아래에 삽입
                        if detail_table.item(target_row, 2) and detail_table.item(target_row, 2).text().strip():
                            detail_table.insertRow(target_row + 1)
                            target_row += 1
                        
                        detail_table.blockSignals(True)
                        detail_table.setItem(target_row, 2, QTableWidgetItem(output_name))
                        detail_table.setItem(target_row, 3, QTableWidgetItem(qty_text))
                        # detail_table.setItem(target_row, 1, QTableWidgetItem(code)) # [FIX] 구분 컬럼 입력 중단
                        detail_table.blockSignals(False)
                        sent_count += 1
                    except Exception as e:
                        print(f"[WARN] Row {row} send failed: {e}")

            elif hasattr(self.parent_popup, "eulji_table"):
                eulji_table = self.parent_popup.eulji_table
                e_cols = self.parent_popup.EULJI_COLS
                
                # 입력된 모든 수량 데이터 처리
                for row, qty_text in list(self.model._qty_inputs.items()):
                    qty_text = qty_text.strip()
                    if not qty_text or not self._is_numeric(qty_text):
                        continue
                    
                    try:
                        raw_row = self.model._raw_data[row]
                        output_name = str(raw_row[13]) if (len(raw_row) > 13 and raw_row[13]) else str(raw_row[1])
                        code = str(raw_row[4])
                        unit = str(raw_row[3])
                        
                        target_row = self.current_row + sent_count
                        
                        # 기존 행이 채워져 있으면 아래에 삽입
                        if eulji_table.item(target_row, e_cols["ITEM"]) and eulji_table.item(target_row, e_cols["ITEM"]).text().strip():
                            eulji_table.insertRow(target_row + 1)
                            target_row += 1
                        
                        eulji_table.blockSignals(True)
                        eulji_table.setItem(target_row, e_cols["ITEM"], QTableWidgetItem(output_name))
                        eulji_table.setItem(target_row, e_cols["FORMULA"], QTableWidgetItem(qty_text))
                        eulji_table.setItem(target_row, e_cols["UNIT"], QTableWidgetItem(unit))
                        # eulji_table.setItem(target_row, e_cols["GUBUN"], QTableWidgetItem(code)) # [FIX] 구분 컬럼 입력 중단
                        eulji_table.blockSignals(False)
                        
                        # [NEW] 강제 계산 트리거 (시그널 차단 중 입력되었으므로 수동 호출)
                        if hasattr(self.parent_popup, "on_eulji_cell_changed"):
                            self.parent_popup.on_eulji_cell_changed(target_row, e_cols["FORMULA"])
                        
                        sent_count += 1
                    except Exception as e:
                        print(f"[WARN] Row {row} send failed: {e}")

            elif hasattr(self.parent_popup, "table") and hasattr(self.parent_popup, "UNIT_PRICE_COLS"):
                # [NEW] 산출일위표 팝업(CalculationUnitPricePopup) 대응
                target_table = self.parent_popup.table
                u_cols = self.parent_popup.UNIT_PRICE_COLS
                
                for row, qty_text in list(self.model._qty_inputs.items()):
                    qty_text = qty_text.strip()
                    try:
                        raw_row = self.model._raw_data[row]
                        output_name = str(raw_row[13]) if (len(raw_row) > 13 and raw_row[13]) else str(raw_row[1])
                        spec = str(raw_row[2]) if raw_row[2] else ""
                        code = str(raw_row[4])
                        
                        target_row = self.current_row + sent_count
                        if target_row >= target_table.rowCount():
                            target_table.insertRow(target_row)
                        
                        target_table.blockSignals(True)
                        # [FIX] '#' 컬럼에 'i' 마커(일위대가) 표시 및 짙은 청색(#000080) 설정
                        mark_item = QTableWidgetItem("i")
                        mark_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        mark_item.setForeground(QColor("#000080"))
                        
                        # 폰트 굵게 처리
                        font = mark_item.font()
                        font.setBold(True)
                        mark_item.setFont(font)
                        
                        target_table.setItem(target_row, u_cols["MARK"], mark_item)
                        
                        target_table.setItem(target_row, u_cols["LIST"], QTableWidgetItem(output_name))
                        
                        if qty_text and self._is_numeric(qty_text):
                            target_table.setItem(target_row, u_cols["UNIT_QTY"], QTableWidgetItem(qty_text))
                        target_table.blockSignals(False)
                        
                        if hasattr(self.parent_popup, "_on_unit_price_cell_changed"):
                            self.parent_popup._on_unit_price_cell_changed(target_row, u_cols["UNIT_QTY"])
                            
                        sent_count += 1
                    except Exception as e:
                        print(f"[WARN] CalculationUnitPricePopup send failed: {e}")

            # 후속 처리
            if sent_count > 0:
                if hasattr(self.parent_popup, '_verify_all_codes'): 
                    self.parent_popup._verify_all_codes()
                if hasattr(self.parent_popup, '_update_preview_sum'): 
                    self.parent_popup._update_preview_sum()
                if hasattr(self.parent_popup, '_calculate_preview_sum'): 
                    self.parent_popup._calculate_preview_sum()
                # 을지 데이터 저장
                if hasattr(self.parent_popup, '_save_eulji_data') and hasattr(self.parent_popup, 'current_gongjong'):
                    self.parent_popup._save_eulji_data(self.parent_popup.current_gongjong)
                    
                print(f"[INFO] ESC: {sent_count}개 항목 전송 완료")
            
            # [FIX] hide() 대신 accept()를 호출하여 exec() 결과가 True가 되도록 함
            self.accept()
            
        except Exception as e:
            print(f"[ERROR] Send all failed: {e}")
            self.reject()

    def _on_send_clicked(self):
        """보내기 버튼 클릭 시 입력된 모든 항목 전송"""
        self._send_all_and_close()

    def _is_numeric(self, text):
        """숫자 및 사칙연산 수식인지 판별 (검색어와 구분)"""
        clean_text = text.replace(' ', '')
        if not clean_text or clean_text == "===": 
            return False
        # 숫자, 사칙연산 기호, 소괄호, 마침표로만 구성되어 있는지 확인
        pattern = r'^[0-9+\-*/().]+$'
        return bool(re.match(pattern, clean_text))

    def _search_and_navigate(self, text, start_row):
        """통합 검색 및 행 이동"""
        # (상향된 로직에서 이미 삭제 처리됨)

        # 검색어에서도 '+'를 공백으로 치환하여 인덱싱 데이터와 매칭
        query = text.lower().strip().replace('+', ' ')
        row_count = self.model.rowCount()
        found = -1
        
        # 순환 검색
        search_range = list(range(start_row, row_count)) + list(range(0, start_row))
        for row in search_range:
            if query in self.model._search_blobs[row]:
                found = row
                break
        
        if found != -1:
            idx = self.model.index(found, 4)
            self.reference_table.setCurrentIndex(idx)
            self.reference_table.scrollTo(idx, QTableView.ScrollHint.PositionAtCenter)
            self.status_label.setText(f"검색 결과: {found+1}행 이동")
        else:
            self.status_label.setText(f"'{text}' 검색 결과 없음")

    def _handle_manual_matching(self, row):
        """=== 입력 시 수동 매칭 영구 등록"""
        # [NEW] active_target_row가 없으면 현재 팝업을 연 current_row를 대상으로 함
        target_row = self.active_target_row if self.active_target_row is not None else self.current_row
        
        if target_row < 0:
            QMessageBox.warning(self, "오류", "매칭할 대상 행을 선택하거나 찾을 수 없습니다.")
            return
            
        try:
            raw_row = self.model._raw_data[row]
            selected_code = str(raw_row[4])
            
            detail_table = self.parent_popup.detail_table
            t_name = detail_table.item(self.active_target_row, 2).text().strip()
            t_spec = detail_table.item(self.active_target_row, 3).text().strip() if detail_table.item(self.active_target_row, 3) else ""
            
            # UI 반영
            detail_table.setItem(self.active_target_row, 1, QTableWidgetItem(selected_code))
            
            # [NEW] 저장 옵션에 따른 경로 결정
            save_to_original = True  # 기본값
            if hasattr(self.parent_popup, 'save_option_group'):
                save_to_original = (self.parent_popup.save_option_group.checkedId() == 0)
            
            if save_to_original:
                # 원본에 저장
                mapping_path = self.original_mapping_path
            else:
                # 프로젝트에만 저장
                project_data_dir = os.path.join(self.project_folder, "project_data")
                mapping_path = os.path.join(project_data_dir, "manual_mapping.json")
            
            # 파일 저장
            os.makedirs(os.path.dirname(mapping_path), exist_ok=True)
            mapping = {}
            if os.path.exists(mapping_path):
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
            
            mapping[f"{t_name}|{t_spec}"] = selected_code
            with open(mapping_path, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, ensure_ascii=False, indent=4)
            
            save_location = "원본" if save_to_original else "프로젝트"
            self.parent_popup._verify_all_codes()
            self.status_label.setText(f"수동 매칭 저장 완료 ({save_location}): {t_name}")
            
        except Exception as e:
            print(f"[ERROR] Manual match failed: {e}")

    def eventFilter(self, obj, event):
        # 팝업 대화상자나 테이블에서의 키 입력을 처리
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                # ESC: 데이터 전송 후 팝업 종료
                self._send_all_and_close()
                return True
            if key in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
                idx = self.reference_table.currentIndex()
                if not idx.isValid():
                    # 유효한 인덱스가 없으면 전송 시도 후 종료
                    self._on_send_clicked()
                    return True
                
                row = idx.row()
                qty_text = self.model._qty_inputs.get(row, "").strip()
                
                # [NEW] 다음 행 이동 로직 (연속 입력 지원)
                # 특수 명령이거나 마지막 행이면 즉시 전송 후 종료
                is_special = (qty_text in ["===", "/"]) or (qty_text and not self._is_numeric(qty_text))
                is_last_row = (row >= self.model.rowCount() - 1)
                
                if is_special or is_last_row:
                    self._on_send_clicked()
                    return True
                
                # 일반 수량 입력 시 다음 행의 산출수량 컬럼으로 이동
                next_index = self.model.index(row + 1, 4)
                if next_index.isValid():
                    self.reference_table.setCurrentIndex(next_index)
                    self.reference_table.edit(next_index) # 즉시 편집 모드 진입
                    return True
                
                # 포커스 이동 실패 시 기본 전송
                self._on_send_clicked()
                return True
                
            # [추가] 일반 문자/숫자 입력 시 자동으로 4번 컬럼(산출수량)으로 이동하여 편집 시작
            if not (event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier)):
                text = event.text()
                # 출력 가능한 문자인 경우 처리 (단일 문자)
                if text and text.isprintable() and len(text) == 1:
                    idx = self.reference_table.currentIndex()
                    # [수정] 선택된 행이 없는 경우 0행을 기본으로 함
                    row_to_use = idx.row() if idx.isValid() else 0
                    col_to_use = idx.column() if idx.isValid() else -1
                    
                    if col_to_use != 4:
                        # 4번 컬럼(산출수량)으로 이동 후 편집 시작
                        qty_idx = self.model.index(row_to_use, 4)
                        self.reference_table.setCurrentIndex(qty_idx)
                        self.reference_table.setFocus() # 포커스 재확인
        return super().eventFilter(obj, event)
