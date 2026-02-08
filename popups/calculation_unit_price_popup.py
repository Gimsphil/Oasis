# -*- coding: utf-8 -*-
"""
산출일위표(일위대가) 팝업 모듈
Calculation Unit Price Table Popup
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QPushButton, QLabel, QHeaderView,
    QAbstractItemView, QLineEdit, QFrame, QStyledItemDelegate,
    QAbstractItemDelegate
)
import re
import sys
from datetime import datetime
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer
from PyQt6.QtGui import QFont, QColor, QKeyEvent

from utils.column_settings import (
    UNIT_PRICE_COL_NAMES, UNIT_PRICE_COL_WIDTHS, 
    UNIT_PRICE_COLS, DEFAULT_ROW_HEIGHT, DEFAULT_FONT_SIZE,
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
        
        # [CORE] Tab 키 처리는 팝업의 eventFilter에서 중앙 집중 관리하므로 여기서는 제거
        # (테이블 본체에서 Tab 입력 시 focusNextChild가 발생하기 전 eventFilter가 먼저 감지함)
        
        # Ctrl+N (행 추가)
        if key == Qt.Key.Key_N and modifiers == Qt.KeyboardModifier.ControlModifier:
            if self.popup: self.popup.add_row()
            return
        
        # Ctrl+Y (행 삭제)
        if key == Qt.Key.Key_Y and modifiers == Qt.KeyboardModifier.ControlModifier:
            if self.popup: self.popup.delete_row()
            return

        super().keyPressEvent(event)

class CalculationUnitPricePopup(QDialog):
    """산출내역서의 산출목록별 세부 일위대가 내역을 편집하는 팝업"""
    
    data_changed = pyqtSignal(int, int, str) # row, col, new_value (필요시 사용)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_tab = None
        self.target_row = -1
        self.target_col = -1
        self.is_manually_moved = False  # 사용자가 직접 이동했는지 여부
        self._drag_pos = None
        
        # [NEW] 외부 모듈(자료사전 등)에서 참조할 수 있도록 속성 노출
        from utils.column_settings import UNIT_PRICE_COLS
        self.UNIT_PRICE_COLS = UNIT_PRICE_COLS
        
        # 절대 경로 로그 파일 설정
        import os
        self.debug_log = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug_trigger.log")
        
        self._init_ui()
        
    def _init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("산출일위표")
        self.setMinimumSize(600, 400)
        
        # 프레임 스타일 설정 (그림자 및 테두리)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                border: 2px solid #107C41;
            }
            QLabel#TitleLabel {
                font-family: '새굴림';
                font-size: 12pt;
                font-weight: bold;
                color: #333;
                background-color: #e1e1e1;
                padding: 5px;
                border-bottom: 1px solid #707070;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. 헤더 영역 (타이틀 및 목록 버튼)
        self.header_frame = QFrame()
        self.header_frame.setFixedHeight(40)
        self.header_frame.setStyleSheet("background-color: #e1e1e1; border-bottom: 1px solid #707070;")
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(10, 0, 10, 0)
        
        self.lbl_title = QLabel("산출일위표")
        self.lbl_title.setObjectName("TitleLabel")
        header_layout.addWidget(self.lbl_title)
        
        header_layout.addStretch()
        
        self.btn_list = QPushButton("목록")
        self.btn_list.setFixedWidth(80)
        self.btn_list.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #999;
                padding: 3px;
                font-family: '새굴림';
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
        info_frame.setFixedHeight(30)
        info_frame.setStyleSheet("background-color: #fff; border-bottom: 1px solid #ccc;")
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(10, 0, 10, 0)
        
        self.lbl_item_name = QLabel("산출일위목록: -")
        self.lbl_item_name.setStyleSheet("font-family: '굴림체'; font-size: 11pt; font-weight: bold;")
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
        
        # [NEW] 편집기에서 Tab 키 가로채기 위한 델리게이트 확장
        self.table.setItemDelegate(UnitPriceDelegate(self.table, self))
        
        # 추가 스타일 미세 조정 (팝업 전용: 독립 셀 선택 모드 고정)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.AnyKeyPressed | QAbstractItemView.EditTrigger.DoubleClicked)
        
        # [NEW] 셀 내용 변경 시 계산 연동
        self.table.cellChanged.connect(self._on_unit_price_cell_changed)
        
        # 이벤트 필터 설치 (키 바인딩용)
        self.table.installEventFilter(self)
        
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
            
            if key == Qt.Key.Key_Tab and modifiers == Qt.KeyboardModifier.NoModifier:
                # [CORE] Tab 키 가로채기
                # QLineEdit(편집기)이거나 테이블 자신(또는 뷰포트)인 경우 처리
                is_target_obj = (obj == self.table or isinstance(obj, QLineEdit) or (hasattr(self.table, "viewport") and obj == self.table.viewport()))
                
                if is_target_obj:
                    row = self.table.currentRow()
                    col = self.table.currentColumn()
                    
                    # 산출일위목록(UNIT_PRICE_COLS["LIST"] == 1) 컬럼에서 Tab 입력 시 자료사전 호출
                    if col == 1 and row >= 0:
                        event.accept()
                        if event.type() == QEvent.Type.KeyPress:
                            # 편집 모드인 경우 데이터 확정 및 에디터 닫기
                            state = self.table.state()
                            if state == QAbstractItemView.State.EditingState:
                                try:
                                    editor = obj if isinstance(obj, QLineEdit) else self.table.focusWidget()
                                    if editor:
                                        self.table.commitData(editor)
                                        self.table.closeEditor(editor, QAbstractItemDelegate.EndEditHint.NoHint)
                                except Exception:
                                    pass
                            
                            # 자료사전 호출 (지연 호출 없이 즉시 실행하여 반응성 확보)
                            try:
                                self._on_table_list_pick(row, col)
                            except Exception as e:
                                print(f"[ERROR] _on_table_list_pick failed: {e}")
                        return True # 시스템 포커스 이동 차단 (Tab으로 다음 셀 이동 방지)
        
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
            self.parent_tab.reference_popup.prepare_show(row, col)
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

    def _load_data(self, item_name):
        """자료사전 기반 데이터 로딩 (기본 30행 설정)"""
        try:
            self.table.setRowCount(0)
            # 사용자 요청에 따라 기본 30행 구성
            for _ in range(30):
                self.add_row()
            
            # 첫 번째 셀 선택
            if self.table.rowCount() > 0:
                self.table.setCurrentCell(0, UNIT_PRICE_COLS["LIST"])
        except Exception as e:
            print(f"[ERROR] _load_data failed: {e}")

    def add_row(self):
        """테이블에 새 행 추가"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 18)
        
    def delete_row(self):
        """현재 선택된 행 삭제"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
            
    def _on_unit_price_cell_changed(self, row, col):
        """셀 데이터 변경 시 처리 (필요시 계산 로직 추가)"""
        # [DEBUG] 셀 변경 로그
        print(f"[DEBUG] Unit Price Cell Changed: row={row}, col={col}")
        pass

    def _adjust_position(self):
        """부모 위젯의 위치에 따라 팝업 위치 조정"""
        if self.parent_tab and hasattr(self.parent_tab, 'main_window'):
            pw = self.parent_tab.main_window
            # 메인 윈도우의 현재 위치와 크기
            pw_rect = pw.geometry()
            
            # 팝업을 메인 윈도우의 우측 내부에 배치 (여백 20px)
            target_x = pw_rect.right() - self.width() - 20
            target_y = pw_rect.top() + 100
            
            # 화면 밖으로 나가지 않도록 조정 (기초적인 수준)
            self.move(target_x, target_y)

    def prepare_show(self, parent_tab, row, col):
        """팝업 표시 전 데이터 및 위치 초기화"""
        try:
            # [DEBUG] 로깅
            with open("debug_trigger.log", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] CalculationUnitPricePopup.prepare_show: row={row}, col={col}\n")
                f.flush()
            
            self.parent_tab = parent_tab
            self.target_row = row
            self.target_col = col
            
            # 1. 대상 아이템명 가져오기
            item_name = ""
            if parent_tab and hasattr(parent_tab, 'eulji_table'):
                 item = parent_tab.eulji_table.item(row, col)
                 if item:
                     item_name = item.text()
            
            # 2. UI 업데이트
            self.lbl_item_name.setText(f"산출일위목록: {item_name}")
            
            # 3. 데이터 로드 (기존 데이터가 있으면 로드, 없으면 빈 폼)
            self._load_data(item_name)
            
            # [NEW] 로깅 강화
            try:
                with open(self.debug_log, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] prepare_show successful for item: {item_name}\n")
            except: pass
            
            # 4. 위치 조정 (최초 1회 또는 강제)
            if not self.is_manually_moved:
                self._adjust_position()
        except Exception as e:
            import traceback
            with open("debug_popup_chain.log", "a", encoding="utf-8") as f:
                f.write(f"[ERROR] prepare_show failed: {e}\n{traceback.format_exc()}\n")

    def show_popup(self):
        """팝업 표시 (Non-modal)"""
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
            self.activateWindow() # 활성화
            
            # 테이블 포커스 강제 (입력 준비)
            if hasattr(self, 'table'):
                self.table.setFocus()
            
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
        """팝업 숨기기"""
        self.hide()

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
