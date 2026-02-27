# -*- coding: utf-8 -*-
"""
전등/전열 산출 매니저 (복구용 최소 구현)
"""

import os
import re
import sqlite3

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from utils.column_settings import DEFAULT_ROW_HEIGHT


class LightingTypePopup(QDialog):
    """전등수량(갯수)산출용 조명기구 타입 조회 팝업."""

    MASTER_HEADERS = ["번호", "타입별 조명기구", "구분", "산출수식", "비고"]
    DETAIL_HEADERS = ["번호", "W", "CODE", "산출목록", "단위수식", "계"]
    MASTER_TABLE_CANDIDATES = [
        "조명기구 목록",
        "조명기구목록",
        "조명기구 타입 목록",
        "조명기구타입",
    ]

    def __init__(self, parent_tab):
        super().__init__(parent_tab.main_window)
        self.parent_tab = parent_tab
        self.db_path = getattr(
            parent_tab,
            "lighting_type_db_path",
            os.path.normpath(
                os.path.join(parent_tab.project_root, "..", "산출목록", "조명기구타입.db")
            ),
        )
        self.master_table_name = None
        self._detail_cache = getattr(self.parent_tab, "_lighting_detail_cache", None)
        if self._detail_cache is None:
            self._detail_cache = {}
            self.parent_tab._lighting_detail_cache = self._detail_cache
        self._current_detail_key = None
        self._is_loading_detail = False
        self._is_loading_master = False
        self._current_type_name = ""
        self._context_key = None  # (gongjong_name, eulji_row)
        self._context_row = -1
        self._master_rowids = []
        self._master_base_values = {}
        self._project_master_overrides = getattr(
            self.parent_tab, "_lighting_master_overrides", None
        )
        if self._project_master_overrides is None:
            self._project_master_overrides = {}
            self.parent_tab._lighting_master_overrides = self._project_master_overrides
        self._project_row_selection = getattr(
            self.parent_tab, "_lighting_row_selection", None
        )
        if self._project_row_selection is None:
            self._project_row_selection = {}
            self.parent_tab._lighting_row_selection = self._project_row_selection

        self.setWindowTitle("전등수량(갯수)산출")
        self.resize(1200, 760)

        self._init_ui()
        self._load_master_table()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(0)
        self.content_layout = content_layout
        root_layout.addLayout(content_layout, 1)

        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        content_layout.addLayout(left_layout, 1)

        left_layout.addWidget(QLabel("조명기구 타입 목록"))
        self.master_table = QTableWidget()
        self.master_table.setColumnCount(len(self.MASTER_HEADERS))
        self.master_table.setHorizontalHeaderLabels(self.MASTER_HEADERS)
        self.master_table.verticalHeader().setVisible(False)
        self.master_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.master_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.master_table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.SelectedClicked
            | QTableWidget.EditTrigger.EditKeyPressed
            | QTableWidget.EditTrigger.AnyKeyPressed
        )
        self.master_table.verticalHeader().setDefaultSectionSize(DEFAULT_ROW_HEIGHT)
        self.master_table.verticalHeader().setMinimumSectionSize(DEFAULT_ROW_HEIGHT)
        self.master_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.master_table.setStyleSheet(
            """
            QTableWidget::item:selected {
                background-color: #cfe8ff;
                color: #000000;
            }
            """
        )
        self.master_table.itemChanged.connect(self._on_master_item_changed)
        self.master_table.itemSelectionChanged.connect(self._on_master_selection_changed)
        self.master_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.master_table.horizontalHeader().setStretchLastSection(False)
        left_layout.addWidget(self.master_table, 1)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)
        content_layout.addLayout(right_layout, 1)

        self.detail_title = QLabel("산출일위표")
        right_layout.addWidget(self.detail_title)

        self.detail_table = QTableWidget()
        self.detail_table.verticalHeader().setVisible(False)
        self.detail_table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.SelectedClicked
            | QTableWidget.EditTrigger.EditKeyPressed
            | QTableWidget.EditTrigger.AnyKeyPressed
        )
        self.detail_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.detail_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.detail_table.verticalHeader().setDefaultSectionSize(DEFAULT_ROW_HEIGHT)
        self.detail_table.verticalHeader().setMinimumSectionSize(DEFAULT_ROW_HEIGHT)
        self.detail_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.detail_table.setStyleSheet(
            """
            QTableWidget::item:selected {
                background-color: #cfe8ff;
                color: #000000;
            }
            """
        )
        self.detail_table.itemChanged.connect(self._on_detail_item_changed)
        self.detail_table.cellClicked.connect(self._on_detail_cell_clicked)
        self.detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.detail_table.horizontalHeader().setStretchLastSection(False)
        right_layout.addWidget(self.detail_table, 1)

    def _recalculate_dialog_width(self):
        """테이블 컬럼 합 기준으로 팝업 최소 폭 재계산."""
        def table_width(table_widget):
            if table_widget.columnCount() == 0:
                return 0
            header = table_widget.horizontalHeader()
            columns = 0
            for col in range(table_widget.columnCount()):
                mode = header.sectionResizeMode(col)
                if mode == QHeaderView.ResizeMode.Stretch:
                    hint = table_widget.sizeHintForColumn(col)
                    columns += max(140, min(360, hint if hint > 0 else 200))
                else:
                    columns += table_widget.columnWidth(col)
            frame = table_widget.frameWidth() * 2
            v_header = table_widget.verticalHeader().width()
            return columns + frame + v_header + 32

        master_w = table_width(self.master_table)
        detail_w = table_width(self.detail_table)
        target = max(760, master_w + detail_w + 40)
        if hasattr(self, "content_layout"):
            self.content_layout.setStretch(0, max(1, master_w))
            self.content_layout.setStretch(1, max(1, detail_w))
        self.setMinimumWidth(target)
        self.setMaximumWidth(target)
        self.resize(target, self.height())

    def _get_table_names(self):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def _resolve_master_table_name(self, table_names):
        normalized_map = {
            re.sub(r"\s+", "", name): name
            for name in table_names
        }

        for candidate in self.MASTER_TABLE_CANDIDATES:
            key = re.sub(r"\s+", "", candidate)
            if key in normalized_map:
                return normalized_map[key]

        for name in table_names:
            compact = re.sub(r"\s+", "", name)
            if "조명기구" in compact and ("목록" in compact or "타입" in compact):
                return name

        return None

    def _load_master_table(self):
        if not os.path.exists(self.db_path):
            QMessageBox.warning(self, "파일 없음", f"DB 파일을 찾을 수 없습니다.\n{self.db_path}")
            return

        try:
            table_names = self._get_table_names()
            self.master_table_name = self._resolve_master_table_name(table_names)
            if not self.master_table_name:
                QMessageBox.warning(
                    self,
                    "테이블 없음",
                    "'조명기구 목록' 테이블을 찾지 못했습니다.",
                )
                return

            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(f"SELECT rowid, * FROM [{self.master_table_name}]")
                rows = cursor.fetchall()
            finally:
                conn.close()

            def normalize_row(row_data):
                values = []
                for col in range(len(self.MASTER_HEADERS)):
                    value = row_data[col + 1] if (col + 1) < len(row_data) else ""
                    text = "" if value is None else str(value).strip()
                    if col == 0 and text:
                        try:
                            numeric = float(text)
                            if numeric.is_integer():
                                text = str(int(numeric))
                        except Exception:
                            pass
                    values.append(text)
                return values

            normalized_rows = [normalize_row(row_data) for row_data in rows]
            normalized_rows = [
                row_data
                for row_data in normalized_rows
                if any(cell for cell in row_data)
            ]

            def row_sort_key(row_data):
                number_text = row_data[0]
                try:
                    return (0, float(number_text))
                except Exception:
                    return (1, number_text)

            normalized_rows.sort(key=row_sort_key)

            row_data_pairs = []
            for raw in rows:
                normalized = normalize_row(raw)
                if any(cell for cell in normalized):
                    row_data_pairs.append((raw[0], normalized))

            row_data_pairs.sort(key=lambda item: row_sort_key(item[1]))

            self._is_loading_master = True
            try:
                self.master_table.setRowCount(0)
                self._master_rowids = []
                self._master_base_values = {}
                for rowid, row_data in row_data_pairs:
                    row_index = self.master_table.rowCount()
                    self.master_table.insertRow(row_index)
                    self._master_rowids.append(rowid)

                    for col in range(len(self.MASTER_HEADERS)):
                        text = row_data[col]
                        override_key = (self.master_table_name, rowid, col)
                        if override_key in self._project_master_overrides:
                            text = self._project_master_overrides[override_key]
                        self._master_base_values[override_key] = row_data[col]
                        table_item = QTableWidgetItem(text)
                        if col in (0, 2):
                            table_item.setTextAlignment(
                                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                            )

                        if col in (1, 3):
                            table_item.setFlags(
                                table_item.flags()
                                | Qt.ItemFlag.ItemIsEditable
                                | Qt.ItemFlag.ItemIsEnabled
                                | Qt.ItemFlag.ItemIsSelectable
                            )
                        else:
                            table_item.setFlags(
                                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                            )
                        self.master_table.setItem(row_index, col, table_item)
            finally:
                self._is_loading_master = False

            self.master_table.resizeColumnsToContents()
            # [REQ] 현재 폭 대비 비율 적용
            current_no = self.master_table.columnWidth(0)
            current_type = self.master_table.columnWidth(1)
            current_group = self.master_table.columnWidth(2)
            current_formula = self.master_table.columnWidth(3)

            self.master_table.setColumnWidth(0, max(35, int(current_no * 0.5)))       # 번호 1/2
            self.master_table.setColumnWidth(1, max(120, int(current_type * 1.3)))    # 타입별 조명기구 +30%
            self.master_table.setColumnWidth(2, max(50, int(current_group * 0.85)))   # 구분 -15%
            self.master_table.setColumnWidth(3, max(180, int(current_formula * 1.8)))  # 산출수식 확장 (요청 반영)
            self.master_table.setColumnWidth(4, 90)                                    # 비고 적당
            self._recalculate_dialog_width()

            if self.master_table.rowCount() > 0:
                self.master_table.setCurrentCell(0, 0)
                self._on_master_selection_changed()

        except Exception as exc:
            QMessageBox.critical(self, "로딩 오류", f"조명기구 타입 목록 로딩 실패\n{exc}")

    def _on_master_item_changed(self, item):
        """조명기구 타입 목록 편집 내용을 현재 프로젝트 세션에만 반영."""
        if self._is_loading_master or item is None:
            return

        row = item.row()
        col = item.column()

        if col not in (1, 3):
            return

        if row < 0 or row >= len(self._master_rowids):
            return

        rowid = self._master_rowids[row]
        value = item.text().strip() if item.text() else ""
        override_key = (self.master_table_name, rowid, col)

        # [REQ] 산출수식 컬럼: 기존 값이 있을 때 숫자만 입력 후 Enter하면 기존값 + 입력값으로 자동 결합
        if col == 3:
            previous_value = self._project_master_overrides.get(
                override_key, self._master_base_values.get(override_key, "")
            )
            is_plain_number = re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value) is not None
            if previous_value and is_plain_number and value != previous_value:
                merged_value = f"{previous_value}+{value}"
                self._is_loading_master = True
                try:
                    item.setText(merged_value)
                finally:
                    self._is_loading_master = False
                value = merged_value

        self._project_master_overrides[override_key] = value

        # 현재 선택 행의 타입명 변경 시 우측 산출일위표 즉시 동기화
        current_row = self.master_table.currentRow()
        if col == 1 and row == current_row:
            group_item = self.master_table.item(row, 2)
            group_name = group_item.text().strip() if group_item else ""
            if group_name:
                self._current_type_name = value
                self._load_group_sheet(group_name, self._current_type_name)

    def _on_master_selection_changed(self):
        self._save_current_detail_to_cache()

        row = self.master_table.currentRow()
        if row < 0:
            return

        if self._context_key is not None:
            self._project_row_selection[self._context_key] = row

        type_item = self.master_table.item(row, 1)
        self._current_type_name = type_item.text().strip() if type_item else ""

        group_item = self.master_table.item(row, 2)
        group_name = group_item.text().strip() if group_item else ""
        if not group_name:
            self.detail_title.setText("산출일위표")
            self.detail_table.setRowCount(0)
            self.detail_table.setColumnCount(0)
            return

        self.detail_title.setText("산출일위표")
        self._load_group_sheet(group_name, self._current_type_name)

    def set_eulji_context(self, row):
        """현재 편집 대상 을지 행 컨텍스트를 설정하고, 기존 산출 데이터를 복원."""
        self._save_current_detail_to_cache()

        gongjong_name = getattr(self.parent_tab, "current_gongjong", "") or ""
        self._context_row = row if row is not None and row >= 0 else -1
        self._context_key = (gongjong_name, self._context_row)

        selected_master_row = self._project_row_selection.get(self._context_key)
        if selected_master_row is None or not (0 <= selected_master_row < self.master_table.rowCount()):
            selected_master_row = 0 if self.master_table.rowCount() > 0 else -1

        if selected_master_row >= 0:
            self.master_table.setCurrentCell(selected_master_row, 1)
            self._on_master_selection_changed()

    def closeEvent(self, event):
        """팝업 종료 시 현재 편집 데이터를 프로젝트 세션 캐시에 보존."""
        try:
            self._save_current_detail_to_cache()
        finally:
            super().closeEvent(event)

    def _save_current_detail_to_cache(self):
        """현재 산출일위표 편집 상태를 메모리에 저장 (DB 미반영)."""
        if not self._current_detail_key:
            return

        rows = []
        for row in range(self.detail_table.rowCount()):
            row_values = []
            for col in range(self.detail_table.columnCount()):
                cell = self.detail_table.item(row, col)
                row_values.append(cell.text() if cell else "")
            rows.append(row_values)

        self._detail_cache[self._current_detail_key] = rows

    def _on_detail_item_changed(self, item):
        """산출일위표 편집 내용을 시트별 메모리 캐시에 즉시 반영."""
        if self._is_loading_detail:
            return

        if item and item.column() == 4:
            self._recalculate_row_total(item.row())
        self._save_current_detail_to_cache()

    def _on_detail_cell_clicked(self, row, column):
        """첫 행 목록 클릭 시 현재 컨텍스트의 기존 산출 데이터를 재로딩."""
        if row != 0 or column != 3:
            return
        if not self._current_detail_key or self._current_detail_key not in self._detail_cache:
            return

        cached_rows = [saved_row[:] for saved_row in self._detail_cache[self._current_detail_key]]
        if not cached_rows:
            return
        self._set_detail_table_rows(cached_rows)

    def _recalculate_row_total(self, row):
        qty_item = self.detail_table.item(row, 4)
        qty_text = qty_item.text().strip() if qty_item else ""

        total_text = ""
        if qty_text:
            try:
                from utils.formula_parser import parse_formula

                result = parse_formula(qty_text)
                if result == int(result):
                    total_text = str(int(result))
                else:
                    total_text = str(result)
            except Exception:
                total_text = ""

        total_item = self.detail_table.item(row, 5)
        if total_item is None:
            total_item = QTableWidgetItem("")
            self.detail_table.setItem(row, 5, total_item)

        self._is_loading_detail = True
        try:
            total_item.setText(total_text)
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        finally:
            self._is_loading_detail = False

    def _set_detail_table_rows(self, rows):
        self._is_loading_detail = True
        try:
            self.detail_table.setColumnCount(len(self.DETAIL_HEADERS))
            self.detail_table.setHorizontalHeaderLabels(self.DETAIL_HEADERS)
            self.detail_table.setRowCount(0)

            for row_data in rows:
                row_index = self.detail_table.rowCount()
                self.detail_table.insertRow(row_index)
                for col in range(len(self.DETAIL_HEADERS)):
                    value = row_data[col] if col < len(row_data) else ""
                    text = "" if value is None else str(value)
                    if col == 0 and text:
                        try:
                            numeric = float(text)
                            if numeric.is_integer():
                                text = str(int(numeric))
                        except Exception:
                            pass

                    table_item = QTableWidgetItem(text)
                    if col == 0:
                        table_item.setTextAlignment(
                            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                        )
                    self.detail_table.setItem(row_index, col, table_item)

            self.detail_table.resizeColumnsToContents()
            # [REQ] 현재 폭 대비 비율 적용
            current_no = self.detail_table.columnWidth(0)
            current_w = self.detail_table.columnWidth(1)
            current_code = self.detail_table.columnWidth(2)
            current_item = self.detail_table.columnWidth(3)
            current_formula = self.detail_table.columnWidth(4)
            current_total = self.detail_table.columnWidth(5)

            self.detail_table.setColumnWidth(0, max(35, int(current_no * 0.5)))         # 번호 1/2
            self.detail_table.setColumnWidth(1, max(25, int(current_w * 0.5)))           # W 1/2
            self.detail_table.setColumnWidth(2, max(90, int(current_code * 0.5)))        # CODE -50%
            self.detail_table.setColumnWidth(3, max(244, int(current_item * 1.1165)))    # 산출목록 (+40% from current setting)
            self.detail_table.setColumnWidth(4, max(130, int(current_formula * 1.3)))    # 단위수식 1.3배
            self.detail_table.setColumnWidth(5, max(50, int(current_total * 0.5)))        # 계 0.5배
            self._recalculate_dialog_width()
        finally:
            self._is_loading_detail = False

    def _load_group_sheet(self, sheet_name, type_name):
        detail_key = (self._context_key, sheet_name, type_name)

        if detail_key in self._detail_cache:
            self._current_detail_key = detail_key
            cached_rows = [row[:] for row in self._detail_cache[detail_key]]
            if not cached_rows:
                cached_rows = [["" for _ in self.DETAIL_HEADERS]]
            cached_rows[0][3] = "전등수량(갯수) 목록"
            self._detail_cache[detail_key] = cached_rows
            self._set_detail_table_rows(cached_rows)
            return

        try:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (sheet_name,),
                )
                exists = cursor.fetchone()
                if not exists:
                    self.detail_table.setRowCount(0)
                    self.detail_table.setColumnCount(0)
                    self.detail_title.setText("산출일위표")
                    self._current_detail_key = detail_key
                    return

                cursor.execute(f"PRAGMA table_info([{sheet_name}])")
                columns = [col[1] for col in cursor.fetchall()]
                if not columns:
                    self.detail_table.setRowCount(0)
                    self.detail_table.setColumnCount(0)
                    self._current_detail_key = detail_key
                    return

                cursor.execute(f"SELECT * FROM [{sheet_name}]")
                rows = cursor.fetchall()
            finally:
                conn.close()

            normalized_rows = []
            for row_data in rows:
                normalized_rows.append([
                    "" if (row_data[col] if col < len(row_data) else "") is None else str(row_data[col] if col < len(row_data) else "")
                    for col in range(len(self.DETAIL_HEADERS))
                ])

            if not normalized_rows:
                normalized_rows.append(["" for _ in self.DETAIL_HEADERS])

            normalized_rows[0][3] = "전등수량(갯수) 목록"

            self._current_detail_key = detail_key
            self._detail_cache[detail_key] = normalized_rows
            self._set_detail_table_rows(normalized_rows)

        except Exception as exc:
            QMessageBox.warning(self, "시트 로딩 실패", f"'{sheet_name}' 시트 로딩 실패\n{exc}")


class LightingPowerManager:
    """OutputDetailTab과 연결되는 전등/전열 매니저."""

    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        self._side_panel = None
        self._lighting_popup = None
        self._current_row = None
        self._list_widget = None
        self._menu_file_path = os.path.normpath(
            os.path.join(
                self.parent_tab.project_root,
                "..",
                "사용자목록",
                "전등,전열 산출공종.txt",
            )
        )

    def create_side_panel(self):
        """을지 우측 패널 생성/재사용."""
        if self._side_panel is not None:
            return self._side_panel

        panel = QFrame()
        panel.setObjectName("lightingPowerPanel")
        panel.setMinimumWidth(220)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("전등/전열")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(title)

        self._status_label = QLabel("선택된 산출 행이 없습니다.")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        self._count_label = QLabel("목록: 0개")
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._count_label)

        self._list_widget = QListWidget()
        self._list_widget.itemClicked.connect(self._on_menu_item_clicked)
        self._list_widget.itemDoubleClicked.connect(self._on_menu_item_clicked)
        layout.addWidget(self._list_widget, 1)

        panel.hide()
        self._side_panel = panel
        return panel

    def _load_menu_list(self):
        """전등/전열 산출공종 텍스트 파일을 읽어 우측 리스트를 갱신."""
        panel = self.create_side_panel()
        if self._list_widget is None:
            return

        self._list_widget.clear()

        if not os.path.exists(self._menu_file_path):
            self._list_widget.addItem(f"파일 없음: {self._menu_file_path}")
            return

        text = None
        for encoding in ("utf-8", "utf-8-sig", "cp949", "euc-kr", "utf-16"):
            try:
                with open(self._menu_file_path, "r", encoding=encoding) as file:
                    text = file.read()
                break
            except UnicodeDecodeError:
                continue
            except Exception as exc:
                self._list_widget.addItem(f"Read Error: {exc}")
                return

        if text is None:
            self._list_widget.addItem("Encoding Fail: 지원 인코딩으로 읽지 못했습니다.")
            return

        normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
        normalized_text = normalized_text.replace("---------------", "\n---------------\n")
        lines = normalized_text.split("\n")

        loaded_count = 0
        for line in lines:
            normalized = re.sub(r"\s+", " ", line).strip()
            if normalized:
                self._list_widget.addItem(normalized)
                loaded_count += 1

        if loaded_count == 0:
            self._list_widget.addItem("(내용 없음)")

        self._count_label.setText(f"목록: {loaded_count}개")

        if panel.isVisible():
            panel.updateGeometry()

    def show_panel(self):
        """전등/전열 우측 패널을 열고 메뉴 리스트를 표시."""
        panel = self.create_side_panel()
        self._load_menu_list()
        splitter = getattr(self.parent_tab, "eulji_splitter", None)
        if splitter is not None:
            sizes = splitter.sizes()
            if len(sizes) >= 2:
                total = sum(sizes)
                target_panel_width = 340
                left_width = max(total - target_panel_width, 300)
                splitter.setSizes([left_width, target_panel_width])
        panel.show()

    def hide_panel(self):
        """전등/전열 우측 패널 숨김."""
        panel = self.create_side_panel()
        panel.hide()

    def toggle_panel(self):
        """우측 패널 표시/숨김 토글."""
        panel = self.create_side_panel()
        if panel.isVisible():
            panel.hide()
            return

        self._load_menu_list()
        panel.show()

    def _on_menu_item_clicked(self, item):
        """우측 전등/전열 메뉴 클릭 시 기존 실행 경로 복구."""
        if item is None:
            return

        selected_text = item.text().strip()
        if not selected_text or selected_text == "---------------":
            return

        table = getattr(self.parent_tab, "eulji_table", None)
        if table is None:
            return

        item_col = self.parent_tab.EULJI_COLS.get("ITEM", 5)
        target_row = table.currentRow()

        # [개선] 전등수량(갯수)산출은 기존 행 우선 재사용, 없으면 빈 행 자동 배치
        if selected_text == "전등수량(갯수)산출":
            if target_row < 0:
                target_row = self._current_row if self._current_row is not None else -1

            if target_row < 0:
                for row_index in range(table.rowCount()):
                    cell_item = table.item(row_index, item_col)
                    if cell_item and cell_item.text().strip() == selected_text:
                        target_row = row_index
                        break

            if target_row < 0:
                for row_index in range(table.rowCount()):
                    cell_item = table.item(row_index, item_col)
                    if cell_item is None or not cell_item.text().strip():
                        target_row = row_index
                        break

            if target_row < 0:
                prev_count = table.rowCount()
                table.setRowCount(prev_count + 10)
                target_row = prev_count

        elif target_row < 0:
            target_row = self._current_row if self._current_row is not None else -1

        if target_row < 0:
            self._status_label.setText("을지 행을 먼저 선택해 주세요.")
            return

        current_item = table.item(target_row, item_col)
        if current_item is None:
            current_item = QTableWidgetItem("")
            table.setItem(target_row, item_col, current_item)

        current_item.setText(selected_text)
        table.setCurrentCell(target_row, item_col)
        self._status_label.setText(f"행 {target_row + 1}: {selected_text}")

        if selected_text == "전등수량(갯수)산출":
            self._apply_lighting_marker_fields(target_row)
            self._open_lighting_type_popup(target_row)
            return

        # [복구] 특수 항목은 기존 클릭 실행 루틴으로 전달
        try:
            from core.unit_price_trigger import EXCLUDED_ITEM_TEXTS

            if selected_text in EXCLUDED_ITEM_TEXTS:
                self.parent_tab.on_eulji_cell_clicked(target_row, item_col)
        except Exception as exc:
            self._status_label.setText(f"실행 오류: {exc}")

    def _apply_lighting_marker_fields(self, row):
        """전등수량(갯수)산출 행에 1식 마커를 자동 반영."""
        table = getattr(self.parent_tab, "eulji_table", None)
        if table is None or row < 0:
            return

        formula_col = self.parent_tab.EULJI_COLS.get("FORMULA", 6)
        unit_col = self.parent_tab.EULJI_COLS.get("UNIT", 8)

        formula_item = table.item(row, formula_col)
        if formula_item is None:
            formula_item = QTableWidgetItem("")
            table.setItem(row, formula_col, formula_item)
        formula_item.setText("1")

        unit_item = table.item(row, unit_col)
        if unit_item is None:
            unit_item = QTableWidgetItem("")
            table.setItem(row, unit_col, unit_item)
        unit_item.setText("식")
        unit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

    def _open_lighting_type_popup(self, row=None):
        """전등수량(갯수)산출 전용 팝업 표시."""
        try:
            if self._lighting_popup is None:
                self._lighting_popup = LightingTypePopup(self.parent_tab)

            context_row = row if row is not None else self._current_row
            if context_row is None:
                context_row = -1
            self._lighting_popup.set_eulji_context(context_row)

            self._lighting_popup.show()
            self._lighting_popup.raise_()
            self._lighting_popup.activateWindow()
        except Exception as exc:
            self._status_label.setText(f"팝업 실행 오류: {exc}")

    def edit_row(self, row):
        """선택한 을지 행을 패널 상태에 반영."""
        self._current_row = row

        table = getattr(self.parent_tab, "eulji_table", None)
        item_col = self.parent_tab.EULJI_COLS.get("ITEM", 5)
        item_text = ""

        if table is not None and row >= 0:
            table.setCurrentCell(row, item_col)
            item = table.item(row, item_col)
            if item is not None:
                item_text = item.text().strip()

        panel = self.create_side_panel()
        if item_text:
            self._status_label.setText(f"행 {row + 1}: {item_text}")
        else:
            self._status_label.setText(f"행 {row + 1} 편집")
        self.show_panel()

        if item_text == "전등수량(갯수)산출":
            self._apply_lighting_marker_fields(row)
            self._open_lighting_type_popup(row)

    def edit_gapji_row(self, row):
        """갑지 선택 시 을지로 이동 후 전등/전열 편집 상태 동기화."""
        if hasattr(self.parent_tab, "_navigate_to_eulji"):
            try:
                self.parent_tab._navigate_to_eulji(row)
            except Exception:
                pass

        self.edit_row(row)
