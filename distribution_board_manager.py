# -*- coding: utf-8 -*-
"""
분전반 산출 관리 모듈
Distribution Board Management Module
"""

import os
import sqlite3
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QPushButton, QHeaderView, QAbstractItemView,
    QFrame, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QFont, QColor

from utils.column_settings import CleanStyleDelegate, setup_common_table, UNIT_PRICE_ROW_HEIGHT, UNIT_PRICE_COL_NAMES, UNIT_PRICE_COL_WIDTHS, UNIT_PRICE_COLS, NumericDelegate, CenterAlignmentDelegate

class UnitPriceTable(QTableWidget):
    """산출일위표 전용 테이블 - Tab 키 및 단축키 처리를 위젯 레벨에서 제어"""
    def __init__(self, parent=None, popup=None):
        super().__init__(parent)
        self.popup = popup

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        ctrl = modifiers & Qt.KeyboardModifier.ControlModifier

        # Ctrl+N (행 추가)
        if key == Qt.Key.Key_N and ctrl:
            if self.popup:
                self.popup.add_row()
            return

        # Ctrl+Y (행 삭제)
        if key == Qt.Key.Key_Y and ctrl:
            if self.popup:
                self.popup.delete_row()
            return

        super().keyPressEvent(event)

class UnitPriceDelegate(CleanStyleDelegate):
    """산출일위표 전용 델리게이트 - 잔상 제거(CleanStyle) 및 편집 중 Tab 키 가로채기 지원"""
    def __init__(self, parent=None, popup=None):
        super().__init__(parent)
        self.popup = popup

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        # 안전하게 체크
        from PyQt6.QtWidgets import QLineEdit
        if isinstance(editor, QLineEdit) and self.popup:
            # [IMPORTANT] 편집기(QLineEdit)에 팝업의 이벤트 필터 설치하여 Tab 키 감지
            editor.installEventFilter(self.popup)
        return editor

def evaluate_math(expression):
    """사칙연산 수식을 계산하여 결과를 반환 (안전한 eval)"""
    if not expression:
        return 0.0
    try:
        import re
        expr = str(expression).strip()
        expr = expr.replace(" ", "")
        expr = expr.replace("{", "(").replace("}", ")")
        expr = expr.replace("[", "(").replace("]", ")")
        expr = expr.replace("x", "*").replace("X", "*")
        clean_expr = re.sub(r"[^0-9+\-*/().]", "", expr)
        if not clean_expr:
            return 0.0
        return float(eval(clean_expr))
    except Exception:
        return 0.0

class DistributionBoardPopup(QDialog):
    """
    분전반 산출 전용 팝업창
    DB: D:\오아시스\산출목록\분전반\분전반목록.db
    Columns: ID, 분전반 목록, 구분, 산출수량
    """
    def __init__(self, parent=None, title="분전반 산출", parent_tab=None, saved_data=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.parent_tab = parent_tab
        self.db_path = r"D:\오아시스\산출목록\분전반\분전반목록.db"
        self.current_row = -1 # 을지 테이블 행 번호
        
        self._init_ui()
        self._load_data(saved_data)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 타이틀
        title_lbl = QLabel("분전반 산출 목록")
        title_lbl.setStyleSheet("font-family: '새굴림'; font-size: 11pt; font-weight: bold; color: #333;")
        layout.addWidget(title_lbl)
        
        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "분전반 목록", "구분", "산출수량"])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 50)  # ID
        self.table.setColumnWidth(1, 400) # 분전반 목록
        self.table.setColumnWidth(2, 100) # 구분
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # 산출수량
        
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(25)
        self.table.setFont(QFont("새굴림", 11))
        
        # 스타일 및 델리게이트 적용
        self.table.setItemDelegate(CleanStyleDelegate(self.table))
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.AnyKeyPressed)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        # [NEW] 단일 선택 모드 (행 단위 선택)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        
        self.table.itemClicked.connect(self._on_table_item_clicked)
        self.table.cellChanged.connect(self._on_main_table_cell_changed)
        
        layout.addWidget(self.table)
        
        # [NEW] 상세 일위표 팝업 (LightingPowerPopup 구조 차용)
        self._create_detail_popup()
        
        # 하단 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        export_btn = QPushButton("내보내기")
        export_btn.setFixedSize(120, 35)
        export_btn.clicked.connect(self.accept)
        
        close_btn = QPushButton("닫기")
        close_btn.setFixedSize(100, 35)
        close_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _load_data(self, saved_data=None):
        """DB에서 분전반 목록 로드 또는 저장된 데이터 복원 (Sheet1 테이블)"""
        if saved_data:
            self._restore_state(saved_data)
            return

        if not os.path.exists(self.db_path):
            print(f"[ERROR] DB file not found: {self.db_path}")
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Sheet1 테이블에서 번호, 분전반 목록, 구분, 산출수량 로드
            cursor.execute("SELECT 번호, [분전반 목록], 구분, 산출수량 FROM Sheet1")
            rows = cursor.fetchall()
            
            self.table.setUpdatesEnabled(False)
            self.table.setRowCount(max(len(rows), 30)) # 최소 30행 보장
            self.table.setShowGrid(True)
            
            for r_idx, row_data in enumerate(rows):
                for c_idx, val in enumerate(row_data):
                    text = str(val) if val is not None else ""
                    item = QTableWidgetItem(text)
                    
                    # 분전반 목록(1번)과 산출수량(3번) 편집 가능하게 설정
                    if c_idx in [1, 3]:
                        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                    else:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    
                    if c_idx in [0, 2]: # ID, 구분 중앙 정렬
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        
                    self.table.setItem(r_idx, c_idx, item)
                self.table.setRowHeight(r_idx, 25)

            # 빈 행 처리
            for r in range(len(rows), 30):
                self.table.setRowHeight(r, 25)
                for c in range(4):
                    self.table.setItem(r, c, QTableWidgetItem(""))
            
            self.table.setUpdatesEnabled(True)
            conn.close()
        except Exception as e:
            print(f"[ERROR] Failed to load distribution board data: {e}")

    def _restore_state(self, saved_data):
        """저장된 페이로드를 기반으로 테이블 상태 복원"""
        items = saved_data.get("items", [])
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(max(len(items), 30))
        self.table.setShowGrid(True)
        
        for r_idx, row_data in enumerate(items):
            # ID, Name, Gubun, Formula
            data_list = [row_data.get("id", ""), row_data.get("name", ""), row_data.get("gubun", ""), row_data.get("formula", "")]
            for c_idx, text in enumerate(data_list):
                item = QTableWidgetItem(str(text))
                if c_idx == 3:
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                else:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                if c_idx in [0, 2]:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r_idx, c_idx, item)
            self.table.setRowHeight(r_idx, 25)
            
        # 나머지 빈 행
        for r in range(len(items), 30):
            self.table.setRowHeight(r, 25)
            for c in range(4):
                self.table.setItem(r, c, QTableWidgetItem(""))
                
        self.table.setUpdatesEnabled(True)

    def get_result_data(self):
        """결과 데이터를 딕셔너리로 반환 (저장용)"""
        results = []
        total_qty = 0.0
        for r in range(self.table.rowCount()):
            id_item = self.table.item(r, 0)
            name_item = self.table.item(r, 1)
            gubun_item = self.table.item(r, 2)
            formula_item = self.table.item(r, 3)
            
            if name_item and name_item.text().strip():
                formula = formula_item.text().strip() if formula_item else ""
                qty = evaluate_math(formula)
                total_qty += qty
                results.append({
                    "id": id_item.text().strip() if id_item else "",
                    "name": name_item.text().strip(),
                    "gubun": gubun_item.text().strip() if gubun_item else "",
                    "formula": formula,
                    "qty": qty
                })
        return {"items": results, "total_qty": total_qty}


    def _create_detail_popup(self):
        """산출일위표 팝업 생성"""
        self._detail_popup = QDialog(self)
        self._detail_popup.setWindowTitle("산출일위표(분전반)")
        self._detail_popup.setMinimumSize(800, 600)
        
        outer_layout = QVBoxLayout(self._detail_popup)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        outer_layout.setSpacing(0)
        
        # 테두리
        border_frame = QFrame()
        border_frame.setStyleSheet("background-color: #f8f9fa; border: 2px solid #505050;")
        outer_layout.addWidget(border_frame)
        
        layout = QVBoxLayout(border_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 헤더
        header_frame = QFrame()
        header_frame.setFixedHeight(26)
        header_frame.setStyleSheet("background-color: #e1e1e1; border: none; border-bottom: 1px solid #707070;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 0, 8, 0)
        
        title_lbl = QLabel("산출일위표(분전반)")
        title_lbl.setStyleSheet("font-family: '새굴림'; font-size: 10pt; font-weight: bold; color: #444;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        
        layout.addWidget(header_frame)
        
        # 정보창 (어떤 항목인지 표시)
        info_frame = QFrame()
        info_frame.setFixedHeight(24)
        info_frame.setStyleSheet("background-color: white; border-bottom: 1px solid #ccc;")
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(8, 0, 8, 0)
        
        self.edt_detail_item_name = QLineEdit("-")
        self.edt_detail_item_name.setStyleSheet("font-family: '굴림체'; font-size: 9pt; font-weight: bold; border: none;")
        self.edt_detail_item_name.textChanged.connect(self._on_detail_name_changed)
        
        info_layout.addWidget(self.edt_detail_item_name)
        layout.addWidget(info_frame)
        
        # 테이블
        # 테이블
        self.detail_table = UnitPriceTable(popup=self)
        cols = UNIT_PRICE_COL_NAMES # ["W", "CODE", "산출일위목록", "단위수식", "계"]
        width_map = UNIT_PRICE_COL_WIDTHS
        cols = UNIT_PRICE_COL_NAMES # ["W", "CODE", "산출일위목록", "단위수식", "계"]
        width_map = UNIT_PRICE_COL_WIDTHS
        
        setup_common_table(self.detail_table, cols, width_map)
        
        self.detail_table.verticalHeader().setDefaultSectionSize(UNIT_PRICE_ROW_HEIGHT)
        self.detail_table.horizontalHeader().setFixedHeight(30)
        
        # 델리게이트
        self.detail_table.setItemDelegate(UnitPriceDelegate(self.detail_table, self))
        
        # [NEW] 셀 내용 변경 시 계산 연동
        self.detail_table.cellChanged.connect(self._on_unit_price_cell_changed)
        
        # 숫자 컬럼 델리게이트
        self.detail_table.setItemDelegateForColumn(UNIT_PRICE_COLS["UNIT_TOTAL"], NumericDelegate(self.detail_table, [UNIT_PRICE_COLS["UNIT_TOTAL"]]))
        self.detail_table.setItemDelegateForColumn(UNIT_PRICE_COLS["MARK"], CenterAlignmentDelegate(self.detail_table, [UNIT_PRICE_COLS["MARK"]]))
        
        layout.addWidget(self.detail_table)
        
        # 하단 메뉴 (닫기 버튼 등)
        menu_frame = QFrame()
        menu_frame.setFixedHeight(40)
        menu_frame.setStyleSheet("background-color: #e8e8e8; border-top: 1px solid #999;")
        menu_layout = QHBoxLayout(menu_frame)
        menu_layout.setContentsMargins(10, 5, 10, 5)
        menu_layout.addStretch()
        
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self._detail_popup.hide)
        menu_layout.addWidget(btn_close)
        
        layout.addWidget(menu_frame)

    def _on_table_item_clicked(self, item):
        """마스터 테이블 아이템 클릭 시 - 분전반 목록(컬럼 1) 클릭 시에만 팝업 표시"""
        if item.column() == 1:
            row = item.row()
            name = item.text()
            rect = self.table.visualItemRect(item)
            global_pos = self.table.mapToGlobal(rect.topRight())
            
            # 현재 선택된 행 저장 (상호 연동을 위해)
            self._current_detail_row = row
            
            # 팝업 데이터 로드
            self.edt_detail_item_name.blockSignals(True)
            self.edt_detail_item_name.setText(name)
            self.edt_detail_item_name.blockSignals(False)
            
            self._load_detail_data(name)
            
            # 팝업 위치 설정 (메인 팝업 오른쪽에 붙이기)
            main_rect = self.geometry()
            main_top_right = self.mapToGlobal(main_rect.topRight())
            # 메인 팝업의 우측 상단에 배치 (X 좌표를 메인 팝업 우측 끝 + 5px로 설정)
            # Y 좌표는 클릭한 아이템의 높이에 맞추거나 메인 팝업 상단에 맞춤
            
            # 옵션 1: 메인 팝업 바로 오른쪽에 붙이기
            popup_x = self.pos().x() + self.width() + 5
            popup_y = self.pos().y()
            
            # 화면 밖으로 나가는지 체크 (간단히)
            # screen_geom = self.screen().availableGeometry()
            # if popup_x + self._detail_popup.width() > screen_geom.right():
            #    popup_x = self.pos().x() - self._detail_popup.width() - 5 
            
            self._detail_popup.move(popup_x, popup_y)
            self._detail_popup.show()
            self._detail_popup.raise_()
            self._detail_popup.activateWindow()

    def _load_detail_data(self, item_name):
        """상세 데이터 로드 (현재는 데이터가 없으므로 빈 30행)"""
        self.detail_table.setRowCount(0)
        self.detail_table.setRowCount(30)
        self.detail_table.setShowGrid(True)
        
        # 첫 행에 아이템 이름 자동 입력
        if item_name:
            self.detail_table.setItem(0, UNIT_PRICE_COLS["LIST"], QTableWidgetItem(item_name))
            self.detail_table.setItem(0, UNIT_PRICE_COLS["UNIT_FORMULA"], QTableWidgetItem("1"))
            
        for r in range(30):
            self.detail_table.setRowHeight(r, UNIT_PRICE_ROW_HEIGHT)

    def eventFilter(self, source, event):
        """Tab 키 및 엔터키 처리"""
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Tab:
                # 탭 키 처리 (다음 셀로 이동 또는 자료사전 호출)
                # 여기서는 단순 이동만 구현 (필요시 확장)
                return False 
        return super().eventFilter(source, event)

    def add_row(self):
        """행 추가"""
        row = self.detail_table.rowCount()
        self.detail_table.insertRow(row)
        self.detail_table.setRowHeight(row, UNIT_PRICE_ROW_HEIGHT)

    def delete_row(self):
        """행 삭제"""
        row = self.detail_table.currentRow()
        if row >= 0:
            self.detail_table.removeRow(row)

    def _on_unit_price_cell_changed(self, row, col):
        """단위수식 변경 시 계 계산"""
        if col == UNIT_PRICE_COLS["UNIT_FORMULA"]:
            item = self.detail_table.item(row, col)
            formula = item.text() if item else ""
            try:
                # 간단한 수식 계산
                result = evaluate_math(formula)
                
                # 결과 포맷팅
                res_text = f"{int(result)}" if result == int(result) else f"{result:g}"
                
                # 계 컬럼 업데이트 (신호 차단)
                self.detail_table.blockSignals(True)
                self.detail_table.setItem(row, UNIT_PRICE_COLS["UNIT_TOTAL"], QTableWidgetItem(res_text))
                self.detail_table.blockSignals(False)
                
                # 총계 업데이트가 필요하면 여기서 호출
                self._update_total_quantity()
            except:
                pass

    def _update_total_quantity(self):
        """상세 테이블의 합계를 메인 테이블 산출수량에 반영"""
        total = 0.0
        for r in range(self.detail_table.rowCount()):
            item = self.detail_table.item(r, UNIT_PRICE_COLS["UNIT_TOTAL"])
            if item and item.text():
                try:
                    total += float(item.text().replace(",", ""))
                except: pass
        
        # 메인 테이블 반영 (현재 선택된 행)
        # 단, 상세 팝업이 닫힐 때 반영하는 것이 일반적이므로 여기서는 생략하거나 실시간 반영 가능
        # self.table.item(self.current_popup_row, 3).setText(str(total))
        pass

    def _on_detail_name_changed(self, text):
        """상세 팝업의 이름 변경 시 메인 테이블에 반영"""
        if hasattr(self, '_current_detail_row') and self._current_detail_row >= 0:
            self.table.blockSignals(True)
            item = self.table.item(self._current_detail_row, 1)
            if item:
                item.setText(text)
            self.table.blockSignals(False)

    def _on_main_table_cell_changed(self, row, col):
        """메인 테이블 변경 시 상세 팝업에 반영 (이름 변경 시)"""
        # 분전반 목록(1번 컬럼) 변경이고, 현재 상세 팝업이 해당 행을 보고 있다면
        if col == 1 and hasattr(self, '_current_detail_row') and self._current_detail_row == row:
            item = self.table.item(row, col)
            if item:
                self.edt_detail_item_name.blockSignals(True)
                self.edt_detail_item_name.setText(item.text())
                self.edt_detail_item_name.blockSignals(False)

class DistributionBoardManager:
    """분전반 산출 관리자 (LightingPowerManager와 유사한 인터페이스 제공)"""
    def __init__(self, parent_tab):
        self.parent_tab = parent_tab

    def edit_row(self, row):
        """을지 테이블의 특정 행을 분전반 산출 팝업으로 편집"""
        table = self.parent_tab.eulji_table
        item_widget = table.item(row, self.parent_tab.EULJI_COLS["ITEM"])
        title = item_widget.text() if item_widget else "분전반 산출"
        
        # [Step 11] UserRole에서 저장된 상세 데이터 가져오기 (Lighting과 호환되게)
        saved_data = item_widget.data(Qt.ItemDataRole.UserRole) if item_widget else None
        
        self._open_popup(title, row, saved_data=saved_data)

    def _open_popup(self, title, target_row, saved_data=None):
        popup = DistributionBoardPopup(self.parent_tab.main_window, title, parent_tab=self.parent_tab, saved_data=saved_data)
        popup.current_row = target_row
        
        # 저장된 데이터가 있으면 복원 (필요시 구현)
        # if saved_data: popup.load_state(saved_data)
        
        if popup.exec() == QDialog.DialogCode.Accepted:
            result = popup.get_result_data()
            if result:
                table = self.parent_tab.eulji_table
                table.blockSignals(True)
                
                # 산출목록(ITEM)
                item_widget = QTableWidgetItem(title)
                item_widget.setData(Qt.ItemDataRole.UserRole, result) # 전체 데이터 저장
                table.setItem(target_row, self.parent_tab.EULJI_COLS["ITEM"], item_widget)
                
                # 산출수식(FORMULA) -> 총 수량
                qty_text = f"{result['total_qty']:g}"
                table.setItem(target_row, self.parent_tab.EULJI_COLS["FORMULA"], QTableWidgetItem(qty_text))
                
                # 단위(UNIT) -> 식
                unit_item = QTableWidgetItem("식")
                unit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(target_row, self.parent_tab.EULJI_COLS["UNIT"], unit_item)
                
                # 계(TOTAL) -> 1
                total_item = QTableWidgetItem("1")
                total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(target_row, self.parent_tab.EULJI_COLS["TOTAL"], total_item)
                
                table.blockSignals(False)
                
                # 부모 탭 저장 트리거
                if hasattr(self.parent_tab, "_save_eulji_data") and hasattr(self.parent_tab, "current_gongjong"):
                    self.parent_tab._save_eulji_data(self.parent_tab.current_gongjong)
