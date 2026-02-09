# -*- coding: utf-8 -*-
"""
산출일위표(일위대가) 팝업 모듈
Calculation Unit Price Table Popup
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QHeaderView,
    QAbstractItemView, QLineEdit, QFrame, QStyledItemDelegate,
    QAbstractItemDelegate, QFileDialog, QMessageBox, QSizePolicy,
    QWidget, QTableWidgetSelectionRange
)
import re
import sys
import os
import json
from datetime import datetime
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer, QPoint
from PyQt6.QtGui import QFont, QColor, QKeyEvent

from utils.column_settings import (
    UNIT_PRICE_COL_NAMES, UNIT_PRICE_COL_WIDTHS,
    UNIT_PRICE_COLS, DEFAULT_ROW_HEIGHT, DEFAULT_FONT_SIZE,
    UNIT_PRICE_ROW_HEIGHT,
    setup_common_table, CleanStyleDelegate
)

class UnitPriceTable(QTableWidget):
    """산출일위표 전용 테이블 - Tab 키 및 단축키 처리를 위젯 레벨에서 제어"""
    def __init__(self, parent=None, popup=None):
        super().__init__(parent)
        self.popup = popup

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        ctrl = modifiers & Qt.KeyboardModifier.ControlModifier
        
        # [CORE] Tab 키 처리는 팝업의 eventFilter에서 중앙 집중 관리하므로 여기서는 제거
        # (테이블 본체에서 Tab 입력 시 focusNextChild가 발생하기 전 eventFilter가 먼저 감지함)
        
        # Ctrl+N (행 추가)
        if key == Qt.Key.Key_N and ctrl:
            if self.popup: self.popup.add_row()
            return
        
        # Ctrl+Y (행 삭제)
        if key == Qt.Key.Key_Y and ctrl:
            if self.popup: self.popup.delete_row()
            return

        super().keyPressEvent(event)

class CalculationUnitPricePopup(QDialog):
    """산출내역서의 산출목록별 세부 일위대가 내역을 편집하는 팝업"""
    
    data_changed = pyqtSignal(int, int, str) # row, col, new_value (필요시 사용)

    MAX_UNIT_PRICE_ROWS = 15  # 산출일위대가 최대 항목 수 (매뉴얼 기준)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_tab = None
        self.target_row = -1
        self.target_col = -1
        self.is_manually_moved = False  # 사용자가 직접 이동했는지 여부
        self._drag_pos = None
        self._internal_clipboard = []  # 내부 클립보드 (F6/F7용)
        self._block_start = -1  # F5 블럭 선택 시작 행
        self._block_end = -1    # F5 블럭 선택 종료 행
        self._is_block_mode = False  # 블럭 모드 활성화 여부
        self._move_mode = False  # F7 이동 모드 (잘라내기 후 붙이기 대기)

        # [NEW] 외부 모듈(자료사전 등)에서 참조할 수 있도록 속성 노출
        from utils.column_settings import UNIT_PRICE_COLS
        self.UNIT_PRICE_COLS = UNIT_PRICE_COLS

        self._init_ui()
        
    def _init_ui(self):
        """UI 초기화"""
        # [NEW] 자료사전 조각 파일 저장 경로 설정 (부모 탭 정보 활용 우선)
        root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.debug_log = os.path.join(root_path, "debug_trigger.log")
        self.base_chunk_dir = os.path.join(root_path, "data", "unit_price_chunks")
        os.makedirs(self.base_chunk_dir, exist_ok=True)
        
        # [NEW] 지연 저장용 타이머
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save_data)
        
        self.setWindowTitle("산출일위표")
        self.setMinimumSize(600, 400)
        
        # 프레임 스타일 설정
        self.setStyleSheet("""
            QLabel#TitleLabel {
                font-family: '새굴림';
                font-size: 11pt;
                font-weight: bold;
                color: #333;
                background-color: transparent;
                border: none;
            }
        """)
        
        # 외곽 테두리용 외부 레이아웃
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 외곽 테두리 프레임 (전체 콘텐츠를 감쌈)
        self.border_frame = QFrame()
        self.border_frame.setStyleSheet("""
            QFrame#BorderFrame {
                background-color: #f8f9fa;
                border: 2px solid #505050;
            }
        """)
        self.border_frame.setObjectName("BorderFrame")
        outer_layout.addWidget(self.border_frame)

        layout = QVBoxLayout(self.border_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. 헤더 영역 (타이틀 및 목록 버튼)
        self.header_frame = QFrame()
        self.header_frame.setFixedHeight(24)
        self.header_frame.setStyleSheet("""
            background-color: #e1e1e1;
            border: none;
            border-bottom: 1px solid #707070;
        """)
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(8, 0, 8, 0)
        
        self.lbl_title = QLabel("산출일위표")
        self.lbl_title.setObjectName("TitleLabel")
        header_layout.addWidget(self.lbl_title)
        
        header_layout.addStretch()
        
        self.btn_list = QPushButton("목록")
        self.btn_list.setFixedSize(50, 20)
        self.btn_list.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #999;
                padding: 1px 4px;
                font-family: '새굴림';
                font-size: 9pt;
            }
            QPushButton:hover { background-color: #e0e0e0; }
        """)
        self.btn_list.clicked.connect(self._on_list_button_clicked)
        header_layout.addWidget(self.btn_list)
        
        layout.addWidget(self.header_frame)
        
        # 헤더 프레임에도 이벤트 필터 설치하여 드래그 지원
        self.header_frame.installEventFilter(self)
        
        # 2. 요약 정보 (1행 데이터)
        info_frame = QFrame()
        info_frame.setFixedHeight(24)
        info_frame.setStyleSheet("background-color: #fff; border: none; border-bottom: 1px solid #ccc;")
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(8, 0, 8, 0)

        self.lbl_item_name = QLabel("산출일위목록: -")
        self.lbl_item_name.setStyleSheet("font-family: '굴림체'; font-size: 10pt; font-weight: bold;")
        info_layout.addWidget(self.lbl_item_name)
        
        info_layout.addStretch()
        layout.addWidget(info_frame)
        
        # 3. 테이블 영역
        # [NEW] 서브클래싱된 전용 테이블 적용 (Tab 키 등 제어용)
        self.table = UnitPriceTable(popup=self)
        self.table.setColumnCount(len(UNIT_PRICE_COL_NAMES))
        self.table.setHorizontalHeaderLabels(UNIT_PRICE_COL_NAMES)
        
        # 컬럼 너비 설정
        for i, name in enumerate(UNIT_PRICE_COL_NAMES):
            key = list(UNIT_PRICE_COL_WIDTHS.keys())[i]
            self.table.setColumnWidth(i, UNIT_PRICE_COL_WIDTHS[key])
            
        layout.addWidget(self.table)

        # [NEW] 공통 스타일 및 잔상 제거 적용
        setup_common_table(self.table, UNIT_PRICE_COL_NAMES, UNIT_PRICE_COL_WIDTHS)

        # 산출일위표 전용: 헤더와 데이터 행 높이 통일 (UNIT_PRICE_ROW_HEIGHT)
        self.table.horizontalHeader().setFixedHeight(UNIT_PRICE_ROW_HEIGHT)

        # [NEW] 편집기에서 Tab 키 가로채기 위한 델리게이트 확장
        self.table.setItemDelegate(UnitPriceDelegate(self.table, self))
        
        # 추가 스타일 미세 조정 (팝업 전용: 독립 셀 선택 모드 고정)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.AnyKeyPressed | QAbstractItemView.EditTrigger.DoubleClicked)
        
        # [NEW] 셀 내용 변경 시 계산 연동
        self.table.cellChanged.connect(self._on_unit_price_cell_changed)
        
        # [NEW] 단위수량 컬럼 및 단위계 컬럼 델리게이트 조정 (숫자 형식)
        from utils.column_settings import NumericDelegate, CenterAlignmentDelegate
        num_delegate = NumericDelegate(self.table, [UNIT_PRICE_COLS["UNIT_QTY"], UNIT_PRICE_COLS["UNIT_TOTAL"]])
        self.table.setItemDelegateForColumn(UNIT_PRICE_COLS["UNIT_QTY"], num_delegate)
        self.table.setItemDelegateForColumn(UNIT_PRICE_COLS["UNIT_TOTAL"], num_delegate)
        
        # [NEW] 마커 컬럼은 중앙 정렬
        self.table.setItemDelegateForColumn(UNIT_PRICE_COLS["MARK"], CenterAlignmentDelegate(self.table, [UNIT_PRICE_COLS["MARK"]]))
        
        # 이벤트 필터 설치 (키 바인딩용)
        self.table.installEventFilter(self)

        # ── 4. 하단 메뉴 바 ──────────────────────────────
        self._create_bottom_menu(layout)
        
    # ================================================================
    # 하단 메뉴 바
    # ================================================================

    def _create_bottom_menu(self, parent_layout):
        """하단 기능 메뉴 바 생성 (가로 균등 배분 레이아웃)"""
        menu_frame = QFrame()
        menu_frame.setObjectName("BottomMenu")
        menu_frame.setFixedHeight(105)
        menu_frame.setStyleSheet("""
            QFrame#BottomMenu {
                background-color: #e8e8e8;
                border: none;
                border-top: 1px solid #999;
            }
        """)

        menu_layout = QVBoxLayout(menu_frame)
        menu_layout.setContentsMargins(12, 6, 12, 6)
        menu_layout.setSpacing(6)

        # ── 버튼 공통 스타일 ──
        btn_style = """
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #aaa;
                padding: 2px 4px;
                font-family: '굴림';
                font-size: 9pt;
                min-width: 65px;
            }
            QPushButton:hover { background-color: #dde8f0; }
            QPushButton:pressed { background-color: #c0d0e0; }
        """
        key_style = """
            QLabel {
                color: #666;
                font-family: '굴림';
                font-size: 8pt;
                padding: 0px;
                border: none;
                background: transparent;
            }
        """

        def make_btn(text, shortcut_text, callback, fixed_w=None):
            """버튼 + 라벨 세로 배치 컨테이너 반환"""
            container_widget = QWidget()
            layout = QVBoxLayout(container_widget)
            layout.setSpacing(1)
            layout.setContentsMargins(0, 0, 0, 0)

            btn = QPushButton(text)
            if fixed_w: btn.setFixedWidth(fixed_w)
            btn.setFixedHeight(26)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(callback)

            lbl = QLabel(shortcut_text)
            lbl.setFixedHeight(14)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(key_style)

            layout.addWidget(btn)
            layout.addWidget(lbl)
            return container_widget, btn

        # ── 1행: 버튼 6개 균등 배분 ──
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        
        c1, self.btn_search = make_btn("자료찾기", "Tab", self._on_search_click, 75)
        c2, self.btn_unitprice = make_btn("일위대가", "F11", self._on_unitprice_click, 75)
        c3, self.btn_block = make_btn("블럭", "F5", self._on_block_click, 60)
        c4, self.btn_copy = make_btn("복사", "F6", self._on_copy_click, 60)
        c5, self.btn_move = make_btn("이동", "F7", self._on_move_click, 60)
        c6, self.btn_release = make_btn("해제", "F8", self._on_release_click, 60)
        
        row1.addWidget(c1)
        row1.addStretch()
        row1.addWidget(c2)
        row1.addStretch()
        row1.addWidget(c3)
        row1.addStretch()
        row1.addWidget(c4)
        row1.addStretch()
        row1.addWidget(c5)
        row1.addStretch()
        row1.addWidget(c6)
        
        menu_layout.addLayout(row1)

        # ── 2행: 버튼 6개 균등 배분 (긴 텍스트 버튼 포함) ──
        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)

        c7, self.btn_list_switch = make_btn("작업목록바꾸기", "PgUp/Dn", self._on_list_switch_click, 110)
        c8, self.btn_screen_copy = make_btn("현재화면복사", "F9", self._on_screen_copy_click, 100)
        c9, self.btn_paste = make_btn("붙이기", "F10", self._on_paste_click, 65)

        # 저장/취소 버튼들도 일관성을 위해 래퍼를 씌워 균등 배치 참여
        def wrap_action_btn(btn_obj):
            wrap = QWidget()
            l = QVBoxLayout(wrap)
            l.setContentsMargins(0, 0, 0, 0)
            l.setSpacing(1)
            l.addWidget(btn_obj)
            l.addSpacing(15) # 하단 라벨 공간만큼 여백 추가하여 정렬 맞춤
            return wrap

        self.btn_save = QPushButton("저장")
        self.btn_save.setFixedWidth(70)
        self.btn_save.setFixedHeight(26)
        self.btn_save.setStyleSheet(btn_style)
        self.btn_save.clicked.connect(self._on_save_click)

        self.btn_piece_save = QPushButton("조각파일저장")
        self.btn_piece_save.setFixedWidth(100)
        self.btn_piece_save.setFixedHeight(26)
        self.btn_piece_save.setStyleSheet(btn_style)
        self.btn_piece_save.clicked.connect(self._on_piece_save_click)

        self.btn_cancel = QPushButton("취소(ESC)")
        self.btn_cancel.setFixedWidth(85)
        self.btn_cancel.setFixedHeight(26)
        self.btn_cancel.setStyleSheet(btn_style)
        self.btn_cancel.clicked.connect(self._on_cancel_click)

        row2.addWidget(c7)
        row2.addStretch()
        row2.addWidget(c8)
        row2.addStretch()
        row2.addWidget(c9)
        row2.addStretch()
        row2.addWidget(wrap_action_btn(self.btn_save))
        row2.addStretch()
        row2.addWidget(wrap_action_btn(self.btn_piece_save))
        row2.addStretch()
        row2.addWidget(wrap_action_btn(self.btn_cancel))

        menu_layout.addLayout(row2)
        parent_layout.addWidget(menu_frame)


    # ================================================================
    # 하단 메뉴 버튼 핸들러
    # ================================================================

    def _on_search_click(self):
        """자료찾기 (Tab) - 자료사전 호출"""
        row = self.table.currentRow()
        col = self.UNIT_PRICE_COLS["LIST"]
        if row >= 0:
            self._on_table_list_pick(row, col)

    def _on_unitprice_click(self):
        """일위대가 (F11) - 목록 버튼과 동일"""
        self._on_list_button_clicked()

    def _on_block_click(self):
        """블럭 (F5) - 범위 선택 (첫 F5: 시작점, 두번째 F5: 종료점)
        매뉴얼 기준: F5로 시작행 지정 → 커서 이동 → F5로 종료행 지정
        """
        row = self.table.currentRow()
        if row < 0:
            return

        if not self._is_block_mode:
            # 첫 번째 F5: 블럭 시작점 설정
            self._block_start = row
            self._block_end = -1
            self._is_block_mode = True
            self._move_mode = False
            # 시작 행만 선택 표시
            self.table.selectRow(row)
            print(f"[BLOCK] Start at row {row}")
        else:
            # 두 번째 F5: 블럭 종료점 설정 → 범위 선택
            self._block_end = row
            start = min(self._block_start, self._block_end)
            end = max(self._block_start, self._block_end)
            # 범위 선택 (다중 행)
            self.table.clearSelection()
            sel_range = QTableWidgetSelectionRange(start, 0, end, self.table.columnCount() - 1)
            self.table.setRangeSelected(sel_range, True)
            print(f"[BLOCK] Range: row {start} ~ {end}")

    def _on_copy_click(self):
        """복사 (F6) - 블럭 선택된 행들을 현재 커서 위치에 복사-삽입
        매뉴얼 기준: F5로 범위 선택 → 커서 이동 → F6으로 복사-삽입
        """
        # 블럭 범위에서 데이터 수집
        selected = self.table.selectedRanges()
        if not selected:
            return

        clipboard_data = []
        for sr in selected:
            for r in range(sr.topRow(), sr.bottomRow() + 1):
                row_data = {}
                for col_key, col_idx in self.UNIT_PRICE_COLS.items():
                    item = self.table.item(r, col_idx)
                    row_data[col_key] = item.text() if item else ""
                clipboard_data.append(row_data)

        if not clipboard_data:
            return

        # 내부 클립보드에도 저장 (F10 붙이기 용)
        self._internal_clipboard = clipboard_data

        # 블럭 모드가 아닌 경우(단순 선택 상태) 클립보드만 저장하고 종료
        if not self._is_block_mode:
            print(f"[COPY] {len(clipboard_data)} rows copied to clipboard")
            return

        # 블럭 모드에서는 현재 커서 위치에 즉시 삽입
        cursor_row = self.table.currentRow()
        if cursor_row < 0:
            cursor_row = 0

        # 15행 제한 체크
        valid_data_count = self._count_valid_rows()
        if valid_data_count + len(clipboard_data) > self.MAX_UNIT_PRICE_ROWS:
            QMessageBox.warning(self, "제한 초과",
                f"산출일위대가는 최대 {self.MAX_UNIT_PRICE_ROWS}개 항목까지 입력 가능합니다.\n"
                f"현재 {valid_data_count}개, 복사 {len(clipboard_data)}개")
            return

        self.table.blockSignals(True)
        for i, row_data in enumerate(clipboard_data):
            insert_row = cursor_row + i
            self.table.insertRow(insert_row)
            self.table.setRowHeight(insert_row, UNIT_PRICE_ROW_HEIGHT)
            for col_key, col_idx in self.UNIT_PRICE_COLS.items():
                val = row_data.get(col_key, "")
                item = QTableWidgetItem(val)
                if col_idx == self.UNIT_PRICE_COLS["MARK"]:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(insert_row, col_idx, item)
        self.table.blockSignals(False)

        # 블럭 해제
        self._on_release_click()
        self.save_timer.start(500)
        print(f"[COPY] {len(clipboard_data)} rows inserted at row {cursor_row}")

    def _on_move_click(self):
        """이동 (F7) - 블럭 선택된 행들을 현재 커서 위치로 이동
        매뉴얼 기준: F5로 범위 선택 → 커서 이동 → F7로 이동 (잘라내기+삽입)
        """
        selected = self.table.selectedRanges()
        if not selected:
            return

        # 선택된 행 데이터 수집
        move_data = []
        rows_to_delete = set()
        for sr in selected:
            for r in range(sr.topRow(), sr.bottomRow() + 1):
                row_data = {}
                for col_key, col_idx in self.UNIT_PRICE_COLS.items():
                    item = self.table.item(r, col_idx)
                    row_data[col_key] = item.text() if item else ""
                move_data.append(row_data)
                rows_to_delete.add(r)

        if not move_data:
            return

        cursor_row = self.table.currentRow()
        if cursor_row < 0:
            cursor_row = 0

        self.table.blockSignals(True)

        # 1단계: 원본 행 삭제 (역순으로)
        for r in sorted(rows_to_delete, reverse=True):
            self.table.removeRow(r)

        # 커서 위치 보정 (삭제된 행이 커서 앞에 있었으면 그만큼 감소)
        deleted_before_cursor = sum(1 for r in rows_to_delete if r < cursor_row)
        insert_at = cursor_row - deleted_before_cursor
        if insert_at < 0:
            insert_at = 0

        # 2단계: 새 위치에 삽입
        for i, row_data in enumerate(move_data):
            row_pos = insert_at + i
            self.table.insertRow(row_pos)
            self.table.setRowHeight(row_pos, UNIT_PRICE_ROW_HEIGHT)
            for col_key, col_idx in self.UNIT_PRICE_COLS.items():
                val = row_data.get(col_key, "")
                item = QTableWidgetItem(val)
                if col_idx == self.UNIT_PRICE_COLS["MARK"]:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_pos, col_idx, item)

        self.table.blockSignals(False)

        # 블럭 해제
        self._on_release_click()
        self.save_timer.start(500)
        print(f"[MOVE] {len(move_data)} rows moved to row {insert_at}")

    def _on_release_click(self):
        """해제 (F8/ESC) - 블럭 선택 해제 및 블럭 모드 종료"""
        self.table.clearSelection()
        self._internal_clipboard = []
        self._block_start = -1
        self._block_end = -1
        self._is_block_mode = False
        self._move_mode = False

    def _on_list_switch_click(self, direction=1):
        """작업목록바꾸기 (PgUp/PgDn) - 이전/다음 산출목록 항목으로 이동
        매뉴얼 기준: 산출일위대가 창이 열린 상태에서 부모 을지 테이블의
        이전/다음 산출목록 항목으로 전환하며 팝업도 해당 데이터로 갱신
        Args:
            direction: 1=다음(PgDn), -1=이전(PgUp)
        """
        if not self.parent_tab or not hasattr(self.parent_tab, 'eulji_table'):
            return

        e_table = self.parent_tab.eulji_table
        e_cols = getattr(self.parent_tab, "EULJI_COLS", {})
        item_col = e_cols.get("ITEM", 5)
        current_row = self.target_row

        # 현재 데이터 저장
        if self.save_timer.isActive():
            self.save_timer.stop()
        self._save_data()

        # 산출목록 컬럼에 데이터가 있는 행들 검색
        total_rows = e_table.rowCount()
        next_row = -1

        if direction > 0:
            # 다음 항목 찾기 (PgDn)
            for r in range(current_row + 1, total_rows):
                item = e_table.item(r, item_col)
                if item and item.text().strip():
                    next_row = r
                    break
        else:
            # 이전 항목 찾기 (PgUp)
            for r in range(current_row - 1, -1, -1):
                item = e_table.item(r, item_col)
                if item and item.text().strip():
                    next_row = r
                    break

        if next_row >= 0:
            # 부모 을지 테이블의 현재 셀도 이동
            e_table.setCurrentCell(next_row, item_col)
            # 팝업 데이터 갱신
            self.prepare_show(self.parent_tab, next_row, item_col)
            print(f"[LIST_SWITCH] Switched to row {next_row} (direction={direction})")
        else:
            print(f"[LIST_SWITCH] No more items in direction {direction}")

    def _on_screen_copy_click(self):
        """현재화면복사 (F9) - 현재 테이블 데이터를 클립보드에 복사"""
        from PyQt6.QtWidgets import QApplication
        lines = []
        for r in range(self.table.rowCount()):
            cols = []
            has_data = False
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                text = item.text() if item else ""
                cols.append(text)
                if text.strip():
                    has_data = True
            if has_data:
                lines.append("\t".join(cols))
        if lines:
            QApplication.clipboard().setText("\n".join(lines))

    def _on_paste_click(self):
        """붙이기 (F10) - 내부 클립보드 데이터를 현재 위치에 삽입"""
        if not hasattr(self, '_internal_clipboard') or not self._internal_clipboard:
            return

        # 15행 제한 체크
        valid_count = self._count_valid_rows()
        if valid_count + len(self._internal_clipboard) > self.MAX_UNIT_PRICE_ROWS:
            QMessageBox.warning(self, "제한 초과",
                f"산출일위대가는 최대 {self.MAX_UNIT_PRICE_ROWS}개 항목까지 입력 가능합니다.\n"
                f"현재 {valid_count}개, 붙이기 {len(self._internal_clipboard)}개")
            return

        row = self.table.currentRow()
        if row < 0:
            row = 0
        self.table.blockSignals(True)
        for i, row_data in enumerate(self._internal_clipboard):
            insert_row = row + i
            self.table.insertRow(insert_row)
            self.table.setRowHeight(insert_row, UNIT_PRICE_ROW_HEIGHT)
            for col_key, col_idx in self.UNIT_PRICE_COLS.items():
                val = row_data.get(col_key, "")
                item = QTableWidgetItem(val)
                if col_idx == self.UNIT_PRICE_COLS["MARK"]:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(insert_row, col_idx, item)
        self.table.blockSignals(False)
        self._internal_clipboard = []
        self.save_timer.start(500)

    def _on_save_click(self):
        """저장 - 현재 데이터를 즉시 저장"""
        if self.save_timer.isActive():
            self.save_timer.stop()
        self._save_data()

    def _on_piece_save_click(self):
        """조각파일저장 - 산출일위목록 데이터를 .piece 파일로 저장"""
        from piece_file_manager import PieceFileManager

        # 테이블 전체 데이터 추출 (유효 행만)
        data = []
        for r in range(self.table.rowCount()):
            row_data = {}
            has_data = False
            for col_key, col_idx in self.UNIT_PRICE_COLS.items():
                item = self.table.item(r, col_idx)
                val = item.text().strip() if item else ""
                row_data[col_key] = val
                if val:
                    has_data = True
            if has_data:
                data.append(row_data)

        if not data:
            QMessageBox.information(self, "조각파일저장", "저장할 데이터가 없습니다.")
            return

        if PieceFileManager.save_piece_file(self, data):
            QMessageBox.information(self, "조각파일저장", f"{len(data)}개 행이 조각파일로 저장되었습니다.")

    def _on_piece_load_click(self):
        """조각파일 불러오기 (Ctrl+R) - .piece 파일을 현재 위치에 삽입"""
        from piece_file_manager import PieceFileManager

        file_path, _ = QFileDialog.getOpenFileName(
            self, "조각파일 불러오기 (Load Piece File)",
            os.path.expanduser("~/Documents"),
            "Piece Files (*.piece);;All Files (*)"
        )
        if not file_path:
            return

        data = PieceFileManager.load_piece_file_from_path(file_path)
        if not data:
            QMessageBox.warning(self, "조각파일", "파일을 불러올 수 없거나 데이터가 비어있습니다.")
            return

        # 15행 제한 체크
        valid_count = self._count_valid_rows()
        if valid_count + len(data) > self.MAX_UNIT_PRICE_ROWS:
            QMessageBox.warning(self, "제한 초과",
                f"산출일위대가는 최대 {self.MAX_UNIT_PRICE_ROWS}개 항목까지 입력 가능합니다.\n"
                f"현재 {valid_count}개, 불러오기 {len(data)}개")
            return

        # 현재 커서 위치에 삽입
        cursor_row = self.table.currentRow()
        if cursor_row < 0:
            cursor_row = 0

        self.table.blockSignals(True)
        for i, row_data in enumerate(data):
            insert_row = cursor_row + i
            self.table.insertRow(insert_row)
            self.table.setRowHeight(insert_row, UNIT_PRICE_ROW_HEIGHT)

            # 데이터 키 매핑 (piece 파일은 다양한 키 형식을 가질 수 있음)
            for col_key, col_idx in self.UNIT_PRICE_COLS.items():
                val = ""
                # 키 이름 직접 매핑 시도
                if col_key in row_data:
                    val = str(row_data[col_key])
                # 소문자 매핑 시도 (mark, list, qty 등)
                elif col_key.lower() in row_data:
                    val = str(row_data[col_key.lower()])

                item = QTableWidgetItem(val)
                if col_idx == self.UNIT_PRICE_COLS["MARK"]:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(insert_row, col_idx, item)
        self.table.blockSignals(False)

        self.save_timer.start(500)
        QMessageBox.information(self, "조각파일", f"{len(data)}개 행을 불러왔습니다.")

    def _count_valid_rows(self):
        """유효한 데이터가 있는 행의 수를 반환"""
        count = 0
        for r in range(self.table.rowCount()):
            for col_idx in self.UNIT_PRICE_COLS.values():
                item = self.table.item(r, col_idx)
                if item and item.text().strip():
                    count += 1
                    break
        return count

    def _on_cancel_click(self):
        """취소 (ESC) - 팝업 닫기"""
        self.hide_popup()

    def mousePressEvent(self, event):
        """마우스 클릭 시 드래그 시작 위치 저장"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """마우스 이동 시 윈도우 이동"""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            self.is_manually_moved = True # 이동됨을 기록
            event.accept()

    def mouseReleaseEvent(self, event):
        """드래그 종료"""
        self._drag_pos = None
        event.accept()

    def eventFilter(self, obj, event):
        # 1. 헤더 드래그 이동 처리
        if obj == self.header_frame:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
                    self.move(event.globalPosition().toPoint() - self._drag_pos)
                    self.is_manually_moved = True
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_pos = None
                return True

        # 2. 키보드 이벤트 처리 (테이블 본체 및 내부 편집기 통합 관리)
        if event.type() in [QEvent.Type.KeyPress, QEvent.Type.ShortcutOverride]:
            if not hasattr(event, "key"): return False
            key = event.key()
            modifiers = event.modifiers()
            ctrl = modifiers & Qt.KeyboardModifier.ControlModifier

            # ESC 키 → 블럭 모드면 해제, 아니면 팝업 닫기
            if key == Qt.Key.Key_Escape and event.type() == QEvent.Type.KeyPress:
                if self._is_block_mode:
                    self._on_release_click()
                    return True
                self._on_cancel_click()
                return True

            # Ctrl+W → 조각파일 저장 (매뉴얼: 블럭 선택된 데이터를 조각파일로 저장)
            if key == Qt.Key.Key_W and ctrl and event.type() == QEvent.Type.KeyPress:
                self._on_piece_save_click()
                return True

            # Ctrl+R → 조각파일 불러오기 (매뉴얼: 조각파일을 현재 위치에 삽입)
            if key == Qt.Key.Key_R and ctrl and event.type() == QEvent.Type.KeyPress:
                self._on_piece_load_click()
                return True

            # PageUp/PageDown → 부모 테이블 이전/다음 산출목록 항목 전환
            if event.type() == QEvent.Type.KeyPress and modifiers == Qt.KeyboardModifier.NoModifier:
                if key == Qt.Key.Key_PageUp:
                    self._on_list_switch_click(direction=-1)
                    return True
                elif key == Qt.Key.Key_PageDown:
                    self._on_list_switch_click(direction=1)
                    return True

            # F5~F11 단축키
            if event.type() == QEvent.Type.KeyPress and modifiers == Qt.KeyboardModifier.NoModifier:
                if key == Qt.Key.Key_F5:
                    self._on_block_click(); return True
                elif key == Qt.Key.Key_F6:
                    self._on_copy_click(); return True
                elif key == Qt.Key.Key_F7:
                    self._on_move_click(); return True
                elif key == Qt.Key.Key_F8:
                    self._on_release_click(); return True
                elif key == Qt.Key.Key_F9:
                    self._on_screen_copy_click(); return True
                elif key == Qt.Key.Key_F10:
                    self._on_paste_click(); return True
                elif key == Qt.Key.Key_F11:
                    self._on_unitprice_click(); return True

            if key == Qt.Key.Key_Tab and modifiers == Qt.KeyboardModifier.NoModifier:
                # [CORE] Tab 키 가로채기
                is_target_obj = (obj == self.table or isinstance(obj, QLineEdit) or (hasattr(self.table, "viewport") and obj == self.table.viewport()))

                if is_target_obj:
                    row = self.table.currentRow()
                    col = self.table.currentColumn()

                    # 산출일위목록(UNIT_PRICE_COLS["LIST"] == 1) 컬럼에서 Tab 입력 시 자료사전 호출
                    if col == 1 and row >= 0:
                        event.accept()
                        if event.type() == QEvent.Type.KeyPress:
                            state = self.table.state()
                            if state == QAbstractItemView.State.EditingState:
                                try:
                                    editor = obj if isinstance(obj, QLineEdit) else self.table.focusWidget()
                                    if editor:
                                        self.table.commitData(editor)
                                        self.table.closeEditor(editor, QAbstractItemDelegate.EndEditHint.NoHint)
                                except Exception:
                                    pass
                            try:
                                self._on_table_list_pick(row, col)
                            except Exception as e:
                                print(f"[ERROR] _on_table_list_pick failed: {e}")
                        return True

        return super().eventFilter(obj, event)

    def _on_table_list_pick(self, row, col):
        """팝업 내부 테이블의 특정 행에서 자료사전 호출"""
        print(f"[DEBUG] _on_table_list_pick called. parent_tab={self.parent_tab}")
        if self.parent_tab:
            print(f"[DEBUG] parent_tab has reference_popup? {hasattr(self.parent_tab, 'reference_popup')}")
            
        if self.parent_tab and hasattr(self.parent_tab, "reference_popup"):
            # [FIX] reference_popup이 None인 경우 초기화
            if self.parent_tab.reference_popup is None:
                print("[DEBUG] Initializing reference_popup for the first time...")
                from popups.database_reference_popup import DatabaseReferencePopup
                self.parent_tab.reference_popup = DatabaseReferencePopup(self.parent_tab)
                
            print("[DEBUG] Opening reference popup...")
            self.hide() # 자료사전이 보이도록 일시 숨김
            self.parent_tab.reference_popup.parent_popup = self # 일시적으로 부모를 이 팝업으로 설정
            self.parent_tab.reference_popup.prepare_show(row, col, self.table)
            self.parent_tab.reference_popup.exec()
            
            # 원복
            self.parent_tab.reference_popup.parent_popup = self.parent_tab
            self.show() # 다시 표시
            self.raise_()
            self.activateWindow()
            print("[DEBUG] Reference popup closed and parent restored.")
        else:
            print("[ERROR] Cannot open reference popup: parent_tab is missing or has no reference_popup")

    def _check_database_match(self, item_name):
        """사용자 요청에 따라 [미등록 품목] 메시지 기능 제거됨"""
        pass

    def _on_list_button_clicked(self):
        """목록 버튼 클릭 시 자료사전 호출"""
        try:
            if not self.parent_tab:
                print("[ERROR] parent_tab is missing")
                return

            if not hasattr(self.parent_tab, "reference_popup"):
                print("[ERROR] parent_tab has no reference_popup attribute")
                return

            # [FIX] reference_popup이 None인 경우 초기화
            if self.parent_tab.reference_popup is None:
                print("[DEBUG] Initializing reference_popup from list button...")
                from popups.database_reference_popup import DatabaseReferencePopup
                self.parent_tab.reference_popup = DatabaseReferencePopup(self.parent_tab)

            # 부모 탭의 자료사전 팝업을 활용 (이미 구현된 기능 재사용)
            ref_popup = self.parent_tab.reference_popup
            
            # [IMPORTANT] 부모를 탭으로 설정하여 탭 데이터가 갱신되도록 함
            ref_popup.parent_popup = self.parent_tab 
            ref_popup.prepare_show(self.target_row, self.target_col)
            
            self.hide() # 자료사전을 가리지 않게 숨김
            if ref_popup.exec():
                # 자료사전에서 선택된 값으로 갱신 (탭 데이터 기반)
                item = self.parent_tab.eulji_table.item(self.target_row, self.target_col)
                if item:
                    new_val = item.text()
                    self.lbl_item_name.setText(f"산출일위목록: {new_val}")
                    # 새 데이터 로드
                    self._load_data(new_val)
            self.show() # 원복
            self.raise_()
            self.activateWindow()
        except Exception as e:
            import traceback
            error_msg = f"[ERROR] _on_list_button_clicked failed: {e}\n{traceback.format_exc()}"
            print(error_msg)
            try:
                with open(self.debug_log, "a", encoding="utf-8") as f:
                    f.write(error_msg + "\n")
            except: pass

    def _get_chunk_file_path(self, item_name):
        """항목명을 기반으로 안전한 파일 경로 생성 (프로젝트별 격리 저장)"""
        # 1. 프로젝트명 확인
        project_name = "-"
        if hasattr(self, 'parent_tab') and hasattr(self.parent_tab, 'lbl_project_name'):
            project_label = self.parent_tab.lbl_project_name.text()
            if project_label.startswith("Project: "):
                project_name = project_label.replace("Project: ", "").strip()
        
        if not project_name or project_name == "-":
            project_name = "_unsaved_session_"
            
        # 2. 프로젝트 폴더 경로 생성
        safe_p_name = re.sub(r'[\\/*?:"<>|]', "_", project_name).strip()
        project_dir = os.path.join(self.base_chunk_dir, safe_p_name)
        os.makedirs(project_dir, exist_ok=True)
        
        # 3. 항목 파일명 생성
        if not item_name:
            if self.target_row >= 0:
                # 항목명이 없는 경우 행 번호를 이용해 임시 저장
                item_name = f"unnamed_row_{self.target_row}"
            else:
                return None
                
        safe_name = re.sub(r'[\\/*?:"<>|]', "_", item_name).strip()
        if not safe_name: return None
        return os.path.join(project_dir, f"{safe_name}.json")

    def _load_data(self, item_name):
        """저장된 조각 파일 로드 또는 기본 30행 초기화"""
        try:
            self.table.setRowCount(0)
            orig_blocked = self.table.blockSignals(True)
            
            file_path = self._get_chunk_file_path(item_name)
            loaded = False
            
            log_msg = f"[{datetime.now()}] _load_data for '{item_name}' (Path: {file_path})\n"
            
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    if isinstance(data, list):
                        for row_data in data:
                            row = self.table.rowCount()
                            self.table.insertRow(row)
                            self.table.setRowHeight(row, UNIT_PRICE_ROW_HEIGHT)
                            
                            # 데이터 채우기 (MARK, LIST, UNIT_QTY)
                            mark_text = str(row_data.get("mark", ""))
                            mark_item = QTableWidgetItem(mark_text)
                            mark_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            
                            # [NEW] 'i'인 경우 짙은 청색 및 볼드 처리
                            if mark_text == "i":
                                mark_item.setForeground(QColor("#000080"))
                                f = mark_item.font()
                                f.setBold(True)
                                mark_item.setFont(f)
                            
                            self.table.setItem(row, self.UNIT_PRICE_COLS["MARK"], mark_item)
                            
                            self.table.setItem(row, self.UNIT_PRICE_COLS["LIST"], QTableWidgetItem(str(row_data.get("list", ""))))
                            self.table.setItem(row, self.UNIT_PRICE_COLS["UNIT_QTY"], QTableWidgetItem(str(row_data.get("qty", ""))))
                            
                            # 단위계 계산 (blockSignals 상태이므로 직접 호출)
                            self._update_row_total(row)
                        loaded = True
                        log_msg += f"  -> Success: {len(data)} rows loaded.\n"
                except Exception as e:
                    log_msg += f"  -> Error: {e}\n"

            # 로드 실패 시 또는 데이터가 없는 경우 기본 30행 구성
            if not loaded:
                for _ in range(30):
                    self.add_row()
                log_msg += "  -> No data found, initialized 30 blank rows.\n"
            
            self.table.blockSignals(orig_blocked)
            
            # 첫 번째 셀 선택
            if self.table.rowCount() > 0:
                self.table.setCurrentCell(0, self.UNIT_PRICE_COLS["LIST"])
            
            # [LOG]
            try:
                with open(self.debug_log, "a", encoding="utf-8") as f:
                    f.write(log_msg)
            except: pass
                
        except Exception as e:
            self.table.blockSignals(False)
            print(f"[ERROR] _load_data failed: {e}")

    def _save_data(self):
        """현재 테이블 내용을 조각 파일로 저장"""
        try:
            item_name = self.lbl_item_name.text().replace("산출일위목록: ", "").strip()
            if item_name == "-": item_name = ""
            
            file_path = self._get_chunk_file_path(item_name)
            if not file_path: return
            
            data = []
            has_valid_data = False
            for r in range(self.table.rowCount()):
                mark_item = self.table.item(r, self.UNIT_PRICE_COLS["MARK"])
                list_item = self.table.item(r, self.UNIT_PRICE_COLS["LIST"])
                qty_item = self.table.item(r, self.UNIT_PRICE_COLS["UNIT_QTY"])
                
                mark_text = mark_item.text().strip() if mark_item else ""
                list_text = list_item.text().strip() if list_item else ""
                qty_text = qty_item.text().strip() if qty_item else ""
                
                if mark_text or list_text or qty_text:
                    data.append({
                        "mark": mark_text,
                        "list": list_text,
                        "qty": qty_text
                    })
                    has_valid_data = True
            
            log_msg = f"[{datetime.now()}] _save_data for '{item_name}' (ValidData={has_valid_data}, Rows={len(data)})\n"
            
            if has_valid_data:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                log_msg += f"  -> Successfully saved to {file_path}\n"
            else:
                log_msg += "  -> No data to save.\n"
                
            # [LOG]
            try:
                with open(self.debug_log, "a", encoding="utf-8") as f:
                    f.write(log_msg)
            except: pass
                
        except Exception as e:
            print(f"[ERROR] _save_data failed: {e}")
            try:
                with open(self.debug_log, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] _save_data EXCEPTION: {e}\n")
            except: pass

    def add_row(self):
        """테이블에 새 행 추가 (빈 행은 제한 없이 추가, 유효 데이터 입력 시 15행 제한 적용)"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, UNIT_PRICE_ROW_HEIGHT)
        
    def delete_row(self):
        """현재 선택된 행 삭제"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
            # [NEW] 행 삭제 후 30행 그리드 유지를 위해 마지막에 빈 행 추가
            self.table.insertRow(self.table.rowCount())
            self._sync_to_parent()
            self.save_timer.start(500) # 행 삭제 시 즉시 예약 저장
            
    def _evaluate_math(self, expression):
        """사칙연산 수식을 계산하여 결과를 반환"""
        if not expression:
            return 0.0
        try:
            # 전처리: 공백 제거, 특수 대괄호를 소괄호로, x 또는 X를 *로 변경
            expr = str(expression).strip()
            expr = expr.replace(' ', '')
            expr = expr.replace('{', '(').replace('}', ')')
            expr = expr.replace('[', '(').replace(']', ')')
            expr = expr.replace('x', '*').replace('X', '*')
            
            # 사칙연산 및 숫자, 소괄호 외의 문자 차단
            clean_expr = re.sub(r'[^0-9+\-*/().]', '', expr)
            
            if not clean_expr:
                return 0.0
                
            # 계산 실행 (안전한 eval을 위해 전역/지역 변수 제한)
            return float(eval(clean_expr, {"__builtins__": None}, {}))
        except Exception:
            return 0.0

    def _on_unit_price_cell_changed(self, row, col):
        """셀 데이터 변경 시 처리 (단위수량 변경 시 해당 행의 단위계 계산 및 부모 동기화)"""
        if col == self.UNIT_PRICE_COLS["UNIT_QTY"]:
            self._update_row_total(row)

        # 15행 초과 경고 (데이터가 있는 행만 카운트)
        valid_count = self._count_valid_rows()
        if valid_count > self.MAX_UNIT_PRICE_ROWS:
            print(f"[WARN] Unit price rows ({valid_count}) exceed max ({self.MAX_UNIT_PRICE_ROWS})")

        # [NEW] 데이터 존재 여부에 따라 부모 탭(을지) 업데이트 (식, 1, 대표자료)
        self._sync_to_parent()

        # [NEW] 데이터 변경 시 지연 저장 (500ms)
        self.save_timer.start(500)
            
    def _update_row_total(self, row):
        """특정 행의 단위수량 수식을 계산하여 단위계 컬럼에 출력"""
        try:
            qty_item = self.table.item(row, self.UNIT_PRICE_COLS["UNIT_QTY"])
            if not qty_item:
                return
            
            formula = qty_item.text().strip()
            result = self._evaluate_math(formula)
            
            from utils.column_settings import format_number
            
            orig_blocked = self.table.blockSignals(True)
            
            total_item = self.table.item(row, self.UNIT_PRICE_COLS["UNIT_TOTAL"])
            if not total_item:
                total_item = QTableWidgetItem()
                self.table.setItem(row, self.UNIT_PRICE_COLS["UNIT_TOTAL"], total_item)
            
            # 계산 결과가 0이 아니거나 수식이 있는 경우에만 표시 (또는 항상 표시)
            total_item.setText(format_number(result) if result != 0 or formula else "")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            self.table.blockSignals(orig_blocked)
            
            # [DEBUG] 행별 합계 갱신 로그
            print(f"[DEBUG] Row {row} Unit Total Updated: {result}")
        except Exception as e:
            print(f"[ERROR] _update_row_total failed for row {row}: {e}")

    def _sync_to_parent(self):
        """일위표 데이터 존재 여부에 따라 부모 테이블(을지) 업데이트
        1. 단위 → '식', 수량 → '1' 설정
        2. 산출목록 컬럼이 비어있으면 산출일위표의 대표(첫행) 자료로 자동 입력
        """
        try:
            if not self.parent_tab or self.target_row < 0:
                return

            # 데이터가 하나라도 있는지 확인 + 첫 번째 유효 행의 데이터 수집
            has_data = False
            first_row_text = ""
            for r in range(self.table.rowCount()):
                list_item = self.table.item(r, self.UNIT_PRICE_COLS["LIST"])
                qty_item = self.table.item(r, self.UNIT_PRICE_COLS["UNIT_QTY"])
                list_text = list_item.text().strip() if list_item else ""
                qty_text = qty_item.text().strip() if qty_item else ""
                if list_text or qty_text:
                    has_data = True
                    if not first_row_text and list_text:
                        first_row_text = list_text  # 대표(첫행) 산출일위목록 텍스트
                    break

            if has_data:
                # 부모 테이블(을지) 참조
                e_cols = getattr(self.parent_tab, "EULJI_COLS", {})
                if not e_cols: return

                e_table = getattr(self.parent_tab, "eulji_table", None)
                if not e_table: return

                e_table.blockSignals(True)

                # 단위 (Index 8) → "식"
                unit_col = e_cols.get("UNIT", 8)
                e_table.setItem(self.target_row, unit_col, QTableWidgetItem("식"))

                # 수량/수식 (Index 6) → "1"
                formula_col = e_cols.get("FORMULA", 6)
                e_table.setItem(self.target_row, formula_col, QTableWidgetItem("1"))

                # [NEW] 산출목록 컬럼이 비어있으면 산출일위표의 대표(첫행) 자료로 채움
                item_col = e_cols.get("ITEM", 5)
                existing_item = e_table.item(self.target_row, item_col)
                existing_text = existing_item.text().strip() if existing_item else ""
                if not existing_text and first_row_text:
                    e_table.setItem(self.target_row, item_col, QTableWidgetItem(first_row_text))
                    print(f"[DEBUG] Parent row {self.target_row} ITEM auto-filled with representative: '{first_row_text}'")

                e_table.blockSignals(False)

                # 부모 테이블의 합계 및 상태 갱신 트리거
                if hasattr(self.parent_tab, "on_eulji_cell_changed"):
                    self.parent_tab.on_eulji_cell_changed(self.target_row, formula_col)

                print(f"[DEBUG] Parent row {self.target_row} synced to '식, 1' due to unit price data.")
        except Exception as e:
            print(f"[ERROR] _sync_to_parent failed: {e}")

    def _adjust_position(self):
        """부모(을지 테이블)의 전체 컬럼 우측 끝에 팝업 배치 (산출수식 가림 방지)
        [FIX] 산출목록 컬럼 우측이 아닌, 테이블 뷰포트의 우측 끝에 배치하여
        산출수식/계/단위/비고 컬럼이 가려지지 않도록 함
        """
        if self.parent_tab and hasattr(self.parent_tab, 'eulji_table'):
            table = self.parent_tab.eulji_table

            # 1. 테이블 뷰포트의 우측 끝 전역 좌표 계산
            viewport_rect = table.viewport().rect()
            viewport_right_global = table.viewport().mapToGlobal(
                QPoint(viewport_rect.right(), 0)
            )

            # 2. 테이블 데이터 영역 상단 기준 Y 좌표
            table_top_global = table.viewport().mapToGlobal(QPoint(0, 0))

            target_x = viewport_right_global.x() + 5  # 뷰포트 우측 끝에서 5px 여백
            target_y = table_top_global.y()

            # 3. 화면 영역을 벗어나지 않도록 보정
            from PyQt6.QtWidgets import QApplication
            screen_rect = QApplication.primaryScreen().availableGeometry()

            if target_x + self.width() > screen_rect.right():
                target_x = screen_rect.right() - self.width() - 10
            if target_y + self.height() > screen_rect.bottom():
                target_y = screen_rect.bottom() - self.height() - 10
            if target_y < screen_rect.top():
                target_y = screen_rect.top() + 10

            self.move(target_x, target_y)
            print(f"[DEBUG] Popup moved to: ({target_x}, {target_y}) - right of table viewport")

    def prepare_show(self, parent_tab, row, col):
        """팝업 표시 전 데이터 및 위치 초기화"""
        try:
            # 1. 이전 항목 저장 상태 확인 (이전 행/열 정보 활용)
            if hasattr(self, 'save_timer') and self.save_timer.isActive():
                self.save_timer.stop()
                self._save_data()
            
            self.parent_tab = parent_tab
            this_old_row = self.target_row
            this_old_col = self.target_col
            self.target_row = row
            self.target_col = col

            # 2. 대상 아이템명 가져오기
            item_name = ""
            if parent_tab and hasattr(parent_tab, 'eulji_table'):
                 item = parent_tab.eulji_table.item(row, col)
                 if item:
                     item_name = item.text().strip()
            
            # [STABILIZED] 만약 행은 같은데 이름만 빈칸에서 이름이 생긴 경우라면?
            # (이름을 나중에 입력하는 경우를 위해 기존 데이터 유실 방지)
            prev_label = self.lbl_item_name.text().replace("산출일위목록: ", "").strip()
            if prev_label == "-": prev_label = ""
            
            if this_old_row == row and not prev_label and item_name:
                print(f"[DEBUG] Row {row} now has a name: '{item_name}'. Syncing unnamed data.")
                # 기존 데이터가 있으면 이름을 붙여서 저장
                self.lbl_item_name.setText(f"산출일위목록: {item_name}")
                self._save_data() 
            
            # 3. UI 업데이트 및 데이터 로드
            self.lbl_item_name.setText(f"산출일위목록: {item_name if item_name else '-'}")
            self._load_data(item_name)
            
            # 4. 위치 조정 (항상 산출목록 컬럼 우측으로 재정렬)
            self._adjust_position()
                
            # [LOG]
            try:
                with open(self.debug_log, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] prepare_show: row={row}, col={col}, item='{item_name}'\n")
            except: pass
            
        except Exception as e:
            import traceback
            with open("debug_popup_chain.log", "a", encoding="utf-8") as f:
                f.write(f"[ERROR] prepare_show failed: {e}\n{traceback.format_exc()}\n")

    def show_popup(self):
        """팝업 표시 (Non-modal)
        [FIX] 포커스를 산출일위표로 빼앗지 않음 - 산출내역서에 입력 우선권 유지
        사용자가 Enter 키 등으로 명시적으로 진입해야만 산출일위표에 포커스 이동
        """
        try:
            with open("debug_trigger.log", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] show_popup called.\n")
                f.flush()

            # [STABILIZED] 윈도우 플래그 설정
            # WindowStaysOnTopHint 제거 (자료사전을 가리는 문제 해결)
            flags = (
                Qt.WindowType.Tool |
                Qt.WindowType.FramelessWindowHint
            )
            if self.windowFlags() != flags:
                self.setWindowFlags(flags)

            self.show()
            self.raise_()       # 맨 앞으로 가져오기
            # [FIX] activateWindow() 및 setFocus() 제거
            # 산출목록 클릭 시 포커스가 산출내역서에 유지되어야 함
            # 사용자가 Enter 키로 명시적으로 진입할 때만 포커스 이동 (event_filter.py에서 처리)

            try:
                with open(self.debug_log, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] show_popup finished. Visible: {self.isVisible()}\n")
            except: pass
        except Exception as e:
            import traceback
            error_msg = f"[ERROR] show_popup failed: {e}\n{traceback.format_exc()}"
            try:
                with open(self.debug_log, "a", encoding="utf-8") as f:
                    f.write(error_msg + "\n")
            except: pass
            print(error_msg)

    def hide_popup(self):
        """팝업 숨기기 및 데이터 세이프 가드"""
        if self.save_timer.isActive():
            self.save_timer.stop()
            self._save_data()
        self.hide()

    def hideEvent(self, event):
        """팝업이 어떤 방식으로든 닫힐 때 데이터 저장"""
        if hasattr(self, 'save_timer') and self.save_timer.isActive():
            self.save_timer.stop()
            self._save_data()
        super().hideEvent(event)

class UnitPriceDelegate(CleanStyleDelegate):
    """산출일위표 전용 델리게이트 - 잔상 제거(CleanStyle) 및 편집 중 Tab 키 가로채기 지원"""
    def __init__(self, parent=None, popup=None):
        super().__init__(parent)
        self.popup = popup

    def createEditor(self, parent, option, index):
        print(f"[DEBUG] UnitPriceDelegate.createEditor called for row={index.row()}, col={index.column()}")
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit) and self.popup:
            print(f"[DEBUG] Installing event filter on editor for row={index.row()}, col={index.column()}")
            # [IMPORTANT] 편집기(QLineEdit)에 팝업의 이벤트 필터 설치하여 Tab 키 감지
            editor.installEventFilter(self.popup)
        return editor
