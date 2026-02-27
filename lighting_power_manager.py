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
        self._detail_cache = {}
        self._current_detail_key = None
        self._is_loading_detail = False
        self._current_type_name = ""

        self.setWindowTitle("전등수량(갯수)산출")
        self.resize(1200, 760)

        self._init_ui()
        self._load_master_table()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        root_layout.addLayout(content_layout, 1)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(6)
        content_layout.addLayout(left_layout, 1)

        left_layout.addWidget(QLabel("조명기구 타입 목록"))
        self.master_table = QTableWidget()
        self.master_table.setColumnCount(len(self.MASTER_HEADERS))
        self.master_table.setHorizontalHeaderLabels(self.MASTER_HEADERS)
        self.master_table.verticalHeader().setVisible(False)
        self.master_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.master_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.master_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.master_table.setStyleSheet(
            """
            QTableWidget::item:selected {
                background-color: #cfe8ff;
                color: #000000;
            }
            """
        )
        self.master_table.itemSelectionChanged.connect(self._on_master_selection_changed)
        self.master_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.master_table.horizontalHeader().setStretchLastSection(False)
        self.master_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        left_layout.addWidget(self.master_table, 1)

        right_layout = QVBoxLayout()
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
        self.detail_table.setStyleSheet(
            """
            QTableWidget::item:selected {
                background-color: #cfe8ff;
                color: #000000;
            }
            """
        )
        self.detail_table.itemChanged.connect(self._on_detail_item_changed)
        self.detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.detail_table.horizontalHeader().setStretchLastSection(False)
        self.detail_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.detail_table, 1)

    def _recalculate_dialog_width(self):
        """테이블 컬럼 합 기준으로 팝업 최소 폭 재계산."""
        def table_width(table_widget):
            if table_widget.columnCount() == 0:
                return 0
            columns = sum(table_widget.columnWidth(col) for col in range(table_widget.columnCount()))
            frame = table_widget.frameWidth() * 2
            v_header = table_widget.verticalHeader().width()
            return columns + frame + v_header + 32

        master_w = table_width(self.master_table)
        detail_w = table_width(self.detail_table)
        target = max(980, master_w + detail_w + 80)
        self.setMinimumWidth(target)
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
                cursor.execute(f"SELECT * FROM [{self.master_table_name}]")
                rows = cursor.fetchall()
            finally:
                conn.close()

            def normalize_row(row_data):
                values = []
                for col in range(len(self.MASTER_HEADERS)):
                    value = row_data[col] if col < len(row_data) else ""
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

            self.master_table.setRowCount(0)
            for row_data in normalized_rows:
                row_index = self.master_table.rowCount()
                self.master_table.insertRow(row_index)

                for col in range(len(self.MASTER_HEADERS)):
                    text = row_data[col]
                    table_item = QTableWidgetItem(text)
                    if col in (0, 2):
                        table_item.setTextAlignment(
                            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                        )
                    self.master_table.setItem(row_index, col, table_item)

            self.master_table.resizeColumnsToContents()
            # [FIX] 누적 배수 확장 방지를 위해 고정 폭 적용
            self.master_table.setColumnWidth(0, 70)   # 번호
            self.master_table.setColumnWidth(2, 70)   # 구분
            self.master_table.setColumnWidth(3, 110)  # 산출수식 (축소)
            self.master_table.setColumnWidth(4, 70)   # 비고 (축소)
            self._recalculate_dialog_width()

            if self.master_table.rowCount() > 0:
                self.master_table.setCurrentCell(0, 0)
                self._on_master_selection_changed()

        except Exception as exc:
            QMessageBox.critical(self, "로딩 오류", f"조명기구 타입 목록 로딩 실패\n{exc}")

    def _on_master_selection_changed(self):
        self._save_current_detail_to_cache()

        row = self.master_table.currentRow()
        if row < 0:
            return

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
            # [FIX] 누적 배수 확장 방지를 위해 고정 폭 적용
            self.detail_table.setColumnWidth(0, 70)    # 번호
            self.detail_table.setColumnWidth(1, 60)    # W
            self.detail_table.setColumnWidth(2, 250)   # CODE
            self.detail_table.setColumnWidth(4, 140)   # 단위수식
            self.detail_table.setColumnWidth(5, 70)    # 계 (축소)
            self.detail_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            self._recalculate_dialog_width()
        finally:
            self._is_loading_detail = False

    def _load_group_sheet(self, sheet_name, type_name):
        detail_key = (sheet_name, type_name)

        if detail_key in self._detail_cache:
            self._current_detail_key = detail_key
            cached_rows = [row[:] for row in self._detail_cache[detail_key]]
            if not cached_rows:
                cached_rows = [["" for _ in self.DETAIL_HEADERS]]
            cached_rows[0][3] = type_name
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

            normalized_rows[0][3] = type_name

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

        # [요청 반영] 전등수량(갯수)산출은 첫 행부터 빈 ITEM 행을 찾아 자동 배치
        if selected_text == "전등수량(갯수)산출":
            target_row = -1
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
            self._open_lighting_type_popup()
            return

        # [복구] 특수 항목은 기존 클릭 실행 루틴으로 전달
        try:
            from core.unit_price_trigger import EXCLUDED_ITEM_TEXTS

            if selected_text in EXCLUDED_ITEM_TEXTS:
                self.parent_tab.on_eulji_cell_clicked(target_row, item_col)
        except Exception as exc:
            self._status_label.setText(f"실행 오류: {exc}")

    def _open_lighting_type_popup(self):
        """전등수량(갯수)산출 전용 팝업 표시."""
        try:
            if self._lighting_popup is None:
                self._lighting_popup = LightingTypePopup(self.parent_tab)
            else:
                self._lighting_popup._load_master_table()

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

    def edit_gapji_row(self, row):
        """갑지 선택 시 을지로 이동 후 전등/전열 편집 상태 동기화."""
        if hasattr(self.parent_tab, "_navigate_to_eulji"):
            try:
                self.parent_tab._navigate_to_eulji(row)
            except Exception:
                pass

        self.edit_row(row)
