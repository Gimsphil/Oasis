# -*- coding: utf-8 -*-
import os
import re
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QPushButton, QLabel, QHeaderView,
    QAbstractItemView, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from utils.column_settings import (
    UNIT_PRICE_COL_NAMES, UNIT_PRICE_COL_WIDTHS, 
    UNIT_PRICE_COLS, DEFAULT_ROW_HEIGHT,
    setup_common_table, CleanStyleDelegate, CenterAlignmentDelegate
)

class UnitPricePanel(QWidget):
    """
    [MODULAR] 산출일위표 통합 패널
    독립 팝업과 전등/전열 팝업 양쪽에서 동일한 기능과 UI를 제공하기 위한 통합 모듈
    """
    
    data_saved = pyqtSignal(str) # 저장된 항목 이름 알림 (필요시)

    def __init__(self, parent_tab=None, parent_dialog=None):
        super().__init__()
        self.parent_tab = parent_tab
        self.parent_dialog = parent_dialog
        self.target_row = -1
        self.UNIT_PRICE_COLS = UNIT_PRICE_COLS
        
        # 경로 설정
        root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.debug_log = os.path.join(root_path, "debug_trigger.log")
        self.base_chunk_dir = os.path.join(root_path, "data", "unit_price_chunks")
        os.makedirs(self.base_chunk_dir, exist_ok=True)
        
        self._init_ui()
        
        # 지연 저장용 타이머
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save_data)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 테이블 생성
        self.table = QTableWidget()
        setup_common_table(self.table, UNIT_PRICE_COL_NAMES, UNIT_PRICE_COL_WIDTHS)
        
        # [NEW] 스타일링 및 델리게이트
        self.table.setItemDelegate(CleanStyleDelegate(self.table))
        # 마커 컬럼 중앙 정렬
        self.table.setItemDelegateForColumn(
            self.UNIT_PRICE_COLS["MARK"], 
            CenterAlignmentDelegate(self.table, [self.UNIT_PRICE_COLS["MARK"]])
        )
        
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.AnyKeyPressed)
        # [FIX] 셀별 독립 선택 지원 (SelectRows → SelectItems)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
        # 헤더 자동 확장
        self.table.horizontalHeader().setSectionResizeMode(self.UNIT_PRICE_COLS["LIST"], QHeaderView.ResizeMode.Stretch)
        
        self.table.cellChanged.connect(self._on_cell_changed)
        
        layout.addWidget(self.table)

    def set_context(self, item_name, row_idx):
        """항목명과 행 번호를 설정하고 데이터 로드"""
        self.target_row = row_idx
        # 데이터 로드 전 타이머 중단
        self.save_timer.stop()
        self._load_data(item_name)
        self.current_item_name = item_name

    def _get_chunk_file_path(self, item_name):
        """프로젝트별/세션별 저장 경로 생성"""
        project_name = ""
        if self.parent_tab:
            project_label = getattr(self.parent_tab, "lbl_project_name", None)
            if project_label:
                project_name = project_label.text().replace("Project: ", "").strip()
        
        if not project_name or project_name == "-":
            project_name = "_unsaved_session_"
            
        safe_p_name = re.sub(r'[\\/*?:"<>|]', "_", project_name).strip()
        project_dir = os.path.join(self.base_chunk_dir, safe_p_name)
        os.makedirs(project_dir, exist_ok=True)
        
        if not item_name:
            if self.target_row >= 0:
                item_name = f"unnamed_row_{self.target_row}"
            else:
                return None
                
        safe_name = re.sub(r'[\\/*?:"<>|]', "_", item_name).strip()
        if not safe_name: return None
        return os.path.join(project_dir, f"{safe_name}.json")

    def _load_data(self, item_name):
        try:
            self.table.setRowCount(0)
            orig_blocked = self.table.blockSignals(True)
            
            file_path = self._get_chunk_file_path(item_name)
            loaded = False
            
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    if isinstance(data, list):
                        for row_data in data:
                            row = self.table.rowCount()
                            self.table.insertRow(row)
                            self.table.setRowHeight(row, 18)
                            
                            mark_text = str(row_data.get("mark", ""))
                            mark_item = QTableWidgetItem(mark_text)
                            mark_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            
                            if mark_text == "i":
                                mark_item.setForeground(QColor("#000080"))
                                f = mark_item.font()
                                f.setBold(True)
                                mark_item.setFont(f)
                            
                            self.table.setItem(row, self.UNIT_PRICE_COLS["MARK"], mark_item)
                            self.table.setItem(row, self.UNIT_PRICE_COLS["CODE"], QTableWidgetItem(str(row_data.get("code", ""))))
                            self.table.setItem(row, self.UNIT_PRICE_COLS["LIST"], QTableWidgetItem(str(row_data.get("list", ""))))
                            self.table.setItem(row, self.UNIT_PRICE_COLS["UNIT_QTY"], QTableWidgetItem(str(row_data.get("qty", ""))))
                            self._update_row_total(row)
                        loaded = True
                except: pass

            if not loaded:
                for _ in range(30):
                    self.add_row()
            
            self.table.blockSignals(orig_blocked)
            if self.table.rowCount() > 0:
                self.table.setCurrentCell(0, self.UNIT_PRICE_COLS["LIST"])
                
        except Exception as e:
            self.table.blockSignals(False)
            print(f"[ERROR] _load_data failed: {e}")

    def _save_data(self):
        try:
            item_name = self.current_item_name if hasattr(self, 'current_item_name') else ""
            file_path = self._get_chunk_file_path(item_name)
            if not file_path: return
            
            data = []
            has_valid_data = False
            
            for r in range(self.table.rowCount()):
                mark = self.table.item(r, self.UNIT_PRICE_COLS["MARK"])
                code_item = self.table.item(r, self.UNIT_PRICE_COLS["CODE"])
                list_item = self.table.item(r, self.UNIT_PRICE_COLS["LIST"])
                qty = self.table.item(r, self.UNIT_PRICE_COLS["UNIT_QTY"])
                
                mark_text = mark.text().strip() if mark else ""
                code_text = code_item.text().strip() if code_item else ""
                list_text = list_item.text().strip() if list_item else ""
                qty_text = qty.text().strip() if qty else ""
                
                if mark_text or code_text or list_text or qty_text:
                    has_valid_data = True
                
                data.append({
                    "mark": mark_text,
                    "code": code_text,
                    "list": list_text,
                    "qty": qty_text
                })
            
            if has_valid_data:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif os.path.exists(file_path):
                os.remove(file_path)
                
        except Exception as e:
            print(f"[ERROR] _save_data failed: {e}")

    def _on_cell_changed(self, row, col):
        if col == self.UNIT_PRICE_COLS["UNIT_QTY"]:
            self._update_row_total(row)
        self.save_timer.start(1000)

    def _update_row_total(self, row):
        qty_item = self.table.item(row, self.UNIT_PRICE_COLS["UNIT_QTY"])
        if not qty_item: return
        
        try:
            expr = qty_item.text().replace(',', '').strip()
            total = eval(expr, {"__builtins__": None}, {}) if expr else 0
            
            from utils.column_settings import format_number
            total_item = QTableWidgetItem(format_number(total))
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, self.UNIT_PRICE_COLS["UNIT_TOTAL"], total_item)
        except:
            self.table.setItem(row, self.UNIT_PRICE_COLS["UNIT_TOTAL"], QTableWidgetItem("0"))

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 18)
        # 마커 컬럼 초기화
        self.table.setItem(row, self.UNIT_PRICE_COLS["MARK"], QTableWidgetItem(""))
        self.table.setItem(row, self.UNIT_PRICE_COLS["CODE"], QTableWidgetItem(""))
        self.table.setItem(row, self.UNIT_PRICE_COLS["LIST"], QTableWidgetItem(""))
        self.table.setItem(row, self.UNIT_PRICE_COLS["UNIT_QTY"], QTableWidgetItem(""))
        self.table.setItem(row, self.UNIT_PRICE_COLS["UNIT_TOTAL"], QTableWidgetItem("0"))

    def delete_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self.save_timer.start(100)

    def get_total_sum(self):
        total = 0
        from utils.column_settings import parse_number
        for r in range(self.table.rowCount()):
            item = self.table.item(r, self.UNIT_PRICE_COLS["UNIT_TOTAL"])
            if item:
                total += parse_number(item.text())
        return total
