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
import os
import json
from datetime import datetime
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer, QPoint
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
        
        # [NEW] 단위수량 컬럼 및 단위계 컬럼 델리게이트 조정 (숫자 형식)
        from utils.column_settings import NumericDelegate, CenterAlignmentDelegate
        num_delegate = NumericDelegate(self.table, [UNIT_PRICE_COLS["UNIT_QTY"], UNIT_PRICE_COLS["UNIT_TOTAL"]])
        self.table.setItemDelegateForColumn(UNIT_PRICE_COLS["UNIT_QTY"], num_delegate)
        self.table.setItemDelegateForColumn(UNIT_PRICE_COLS["UNIT_TOTAL"], num_delegate)
        
        # [NEW] 마커 컬럼은 중앙 정렬
        self.table.setItemDelegateForColumn(UNIT_PRICE_COLS["MARK"], CenterAlignmentDelegate(self.table, [UNIT_PRICE_COLS["MARK"]]))
        
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
                            self.table.setRowHeight(row, 18)
                            
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
        """테이블에 새 행 추가"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 18)
        
    def delete_row(self):
        """현재 선택된 행 삭제"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
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
        
        # [NEW] 데이터 존재 여부에 따라 부모 탭(을지) 업데이트 (식, 1)
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
        """일위표 데이터 존재 여부에 따라 부모 테이블(을지)의 단위/수량 업데이트 ('식', '1')"""
        try:
            if not self.parent_tab or self.target_row < 0:
                return
                
            # 데이터가 하나라도 있는지 확인 (산출일위목록 또는 단위수량이 있는 행)
            has_data = False
            for r in range(self.table.rowCount()):
                list_item = self.table.item(r, self.UNIT_PRICE_COLS["LIST"])
                qty_item = self.table.item(r, self.UNIT_PRICE_COLS["UNIT_QTY"])
                if (list_item and list_item.text().strip()) or (qty_item and qty_item.text().strip()):
                    has_data = True
                    break
            
            if has_data:
                # 부모 테이블(을지) 참조
                e_cols = getattr(self.parent_tab, "EULJI_COLS", {})
                if not e_cols: return
                
                e_table = getattr(self.parent_tab, "eulji_table", None)
                if not e_table: return
                
                e_table.blockSignals(True)
                
                # 단위 (Index 8) -> "식"
                unit_col = e_cols.get("UNIT", 8)
                e_table.setItem(self.target_row, unit_col, QTableWidgetItem("식"))
                
                # 수량/수식 (Index 6) -> "1"
                # [NOTE] 사용자가 직접 수량을 입력했더라도 일위표 데이터가 있으면 "1"로 강제함 (복합성 항목)
                formula_col = e_cols.get("FORMULA", 6)
                e_table.setItem(self.target_row, formula_col, QTableWidgetItem("1"))
                
                e_table.blockSignals(False)
                
                # 부모 테이블의 합계 및 상태 갱신 트리거
                if hasattr(self.parent_tab, "on_eulji_cell_changed"):
                    self.parent_tab.on_eulji_cell_changed(self.target_row, formula_col)
                    
                print(f"[DEBUG] Parent row {self.target_row} synced to '식, 1' due to unit price data.")
        except Exception as e:
            print(f"[ERROR] _sync_to_parent failed: {e}")

    def _adjust_position(self):
        """부모(을지 테이블)의 산출목록 컬럼 우측에 팝업 배치"""
        if self.parent_tab and hasattr(self.parent_tab, 'eulji_table'):
            table = self.parent_tab.eulji_table
            
            # 1. 대상 컬럼(산출목록)의 위치 및 너비 정보 가져오기
            col_x = table.columnViewportPosition(self.target_col)
            col_w = table.columnWidth(self.target_col)
            
            # 2. 현재 선택된 행의 Y 좌표 가져오기
            row_y = table.rowViewportPosition(self.target_row)
            
            # 3. 전역 좌표로 변환
            # 산출목록 컬럼의 오른쪽 끝 지점을 시작점으로 잡음
            top_left = table.viewport().mapToGlobal(QPoint(col_x + col_w, row_y))
            
            target_x = top_left.x() + 10  # 컬럼 끝에서 10px 여백
            target_y = top_left.y()
            
            # 4. 화면 영역을 벗어나지 않도록 보정
            from PyQt6.QtWidgets import QApplication
            screen_rect = QApplication.primaryScreen().availableGeometry()
            
            # 가로 보정: 화면 오른쪽을 넘어가면 왼쪽으로 밀기
            if target_x + self.width() > screen_rect.right():
                target_x = screen_rect.right() - self.width() - 20
                
            # 세로 보정: 화면 아래를 넘어가면 위로 밀기
            if target_y + self.height() > screen_rect.bottom():
                target_y = screen_rect.bottom() - self.height() - 20
            
            # 최소 Y 좌표 보정
            if target_y < screen_rect.top():
                target_y = screen_rect.top() + 20
                
            self.move(target_x, target_y)
            print(f"[DEBUG] Popup moved to: ({target_x}, {target_y}) - to the right of column {self.target_col}")

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
            
            # 4. 위치 조정
            if not self.is_manually_moved:
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
