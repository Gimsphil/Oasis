# -*- coding: utf-8 -*-
from PyQt6.QtCore import Qt, QObject, QEvent, QTimer
from PyQt6.QtWidgets import QApplication, QTableWidget, QWidget, QTableWidgetItem


class TableEventFilter(QObject):
    """테이블 키 이벤트 필터"""

    _instance_count = 0  # 디버깅용 카운트
    FORMULA_MAX_BYTES = 40  # 산출수식 40byte 제한

    def __init__(self, parent_tab):
        super().__init__()
        self.parent_tab = parent_tab
        TableEventFilter._instance_count += 1
        self._log_file = "tab_debug.log"
        self._log(
            f"TableEventFilter initialized. Instance count: {TableEventFilter._instance_count}"
        )

        # [NEW] QApplication에 전용 필터 설치
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
            self._log("Event filter installed on QApplication")

    def _log(self, msg):
        """파일에 디버그 로그 기록"""
        try:
            import datetime

            with open(self._log_file, "a", encoding="utf-8") as f:
                ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                f.write(f"[{ts}] {msg}\n")
        except:
            pass

    def eventFilter(self, obj, event):
        try:
            # ShortcutOverride 및 KeyPress 모두에서 Tab/Backtab 가로채기
            if event.type() in [QEvent.Type.KeyPress, QEvent.Type.ShortcutOverride]:
                if not hasattr(event, "key"):
                    return False
                key = event.key()

                # Tab 키만 처리 (Shift+Tab은 제외하여 이전 셀 이동 허용)
                modifiers = event.modifiers() & (
                    Qt.KeyboardModifier.ShiftModifier
                    | Qt.KeyboardModifier.ControlModifier
                    | Qt.KeyboardModifier.AltModifier
                    | Qt.KeyboardModifier.MetaModifier
                )

                if (
                    key == Qt.Key.Key_Tab
                    and modifiers == Qt.KeyboardModifier.NoModifier
                ):
                    self._log(f"Tab Key Detected! Event type: {event.type()}")
                    target_table = None
                    # 현재 포커스 대상 위젯
                    focus_w = QApplication.focusWidget() or (
                        obj if isinstance(obj, QWidget) else None
                    )
                    # self._log(f"Focus widget: {focus_w}, type: {type(focus_w)}")

                    if focus_w:
                        # 을지 테이블 또는 그 하위 위젯(에디터/뷰포트 등)인지 확인
                        if (
                            hasattr(self.parent_tab, "eulji_table")
                            and self.parent_tab.eulji_table is not None
                        ):
                            t = self.parent_tab.eulji_table
                            # 에디터가 열려있을 경우 focus_w는 QLineEdit 등일 수 있음
                            if (
                                t == focus_w
                                or t.isAncestorOf(focus_w)
                                or focus_w == t.viewport()
                            ):
                                target_table = t
                                # self._log("Matched eulji_table!")

                        # 갑지 테이블 체크
                        if (
                            not target_table
                            and hasattr(self.parent_tab, "gapji_table")
                            and self.parent_tab.gapji_table is not None
                        ):
                            t = self.parent_tab.gapji_table
                            if (
                                t == focus_w
                                or t.isAncestorOf(focus_w)
                                or focus_w == t.viewport()
                            ):
                                target_table = t
                                # self._log("Matched gapji_table!")

                    if target_table:
                        # 현재 행/열 (에디터 상태여도 테이블의 currentCell은 유지됨)
                        current_row = target_table.currentRow()
                        current_col = target_table.currentColumn()
                        # self._log(f"Target Table Found! Row: {current_row}, Col: {current_col}")

                        # (A) 갑지에서의 탭 -> 을지로 네비게이션
                        if (
                            target_table == self.parent_tab.gapji_table
                            and current_col == self.parent_tab.GONGJONG_COL
                        ):
                            event.accept()
                            if event.type() == QEvent.Type.KeyPress:
                                # 실제 키가 눌렸을 때 로직 수행
                                if hasattr(self.parent_tab, "lighting_manager"):
                                    item = target_table.item(current_row, current_col)
                                    if item and item.data(Qt.ItemDataRole.UserRole):
                                        self.parent_tab.lighting_manager.edit_gapji_row(
                                            current_row
                                        )
                                        return True
                                self.parent_tab._navigate_to_eulji(current_row)
                            return True  # ShortcutOverride 차단

                        # (B) 을지(산출목록/수식)에서의 탭 -> 자료사전 호출
                        elif (
                            target_table == self.parent_tab.eulji_table
                            and current_col
                            in [
                                self.parent_tab.EULJI_COLS["ITEM"],
                                self.parent_tab.EULJI_COLS["FORMULA"],
                            ]
                        ):
                            self._log(
                                f"Tab in Eulji Item/Formula Column ({current_col})"
                            )
                            event.accept()
                            if event.type() == QEvent.Type.KeyPress:
                                # 팝업 호출 전 에디터 닫기 (데이터 커밋)
                                if focus_w != target_table:
                                    target_table.setFocus()

                                # 지연 호출로 윈도우 포커스 충돌 방지 및 에디터 정리 시간 확보
                                QTimer.singleShot(
                                    10,
                                    lambda: self.parent_tab._show_reference_popup(
                                        current_row, current_col
                                    ),
                                )
                            return True

            # 기타 단축키 로직 (KeyPress 전용)
            if event.type() == QEvent.Type.KeyPress:
                key = event.key()
                ctrl = event.modifiers() & Qt.KeyboardModifier.ControlModifier
                self._log(
                    f"KeyPress: key={key}, modifiers={event.modifiers()} (Ctrl={bool(ctrl)}) on {obj}"
                )

                # 테이블 객체 또는 뷰포트에서 발생한 경우
                target_table = None
                curr = obj
                while curr and isinstance(curr, QObject):
                    if isinstance(curr, QTableWidget):
                        target_table = curr
                        break
                    curr = curr.parent() if hasattr(curr, "parent") else None

                if target_table:
                    # [STABILIZED] Modifier 체크를 bitwise AND로 변경하여 NumLock/CapsLock 등에도 대응
                    if key == Qt.Key.Key_N and ctrl:
                        row = target_table.currentRow()
                        idx = max(0, row)
                        self.parent_tab.record_undo(target_table, "insert", idx)
                        target_table.insertRow(idx)
                        return True

                    if key == Qt.Key.Key_Y and ctrl:
                        row = target_table.currentRow()
                        if row >= 0:
                            item_texts = []
                            for c in range(target_table.columnCount()):
                                item = target_table.item(row, c)
                                item_texts.append(item.text() if item else "")
                            self.parent_tab.record_undo(
                                target_table, "delete", row, item_texts
                            )
                            target_table.removeRow(row)
                            # [NEW] 행 삭제 후 그리드 유지를 위해 마지막에 빈 행 추가
                            target_table.insertRow(target_table.rowCount())
                        return True

                    if key == Qt.Key.Key_Z and ctrl:
                        self.parent_tab.undo()
                        return True

                    # [Phase 1-3] Ctrl+C → 셀 복사
                    if key == Qt.Key.Key_C and ctrl:
                        self._handle_copy(target_table)
                        return True

                    # [Phase 1-3] Ctrl+V → 셀 붙이기
                    if key == Qt.Key.Key_V and ctrl:
                        self._handle_paste(target_table)
                        return True

                    # [Phase 1-3] Ctrl+X → 잘라내기
                    if key == Qt.Key.Key_X and ctrl:
                        self._handle_cut(target_table)
                        return True

                    # [Phase 1-4] F4 → 수량 없이 입력 (1@)
                    if key == Qt.Key.Key_F4:
                        if target_table == getattr(
                            self.parent_tab, "eulji_table", None
                        ):
                            self._handle_f4_no_quantity(target_table)
                            return True

                    # [NEW] F3 → 산출일위표 토글 (매뉴얼: 산출목록에서 F3으로 산출일위대가 표시/숨기기)
                    if key == Qt.Key.Key_F3 and target_table == getattr(
                        self.parent_tab, "eulji_table", None
                    ):
                        trigger = getattr(self.parent_tab, "unit_price_trigger", None)
                        if trigger and trigger.popup:
                            if trigger.popup.isVisible():
                                trigger.popup.hide_popup()
                            else:
                                current_row = target_table.currentRow()
                                current_col = target_table.currentColumn()
                                item_col = self.parent_tab.EULJI_COLS.get("ITEM", 5)
                                trigger.handle_cell_selection(current_row, item_col)
                        return True

                    # [NEW] Enter → 산출수식 컬럼에서 연속입력 (40byte 초과 시 다음 줄)
                    if key in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
                        if target_table == getattr(
                            self.parent_tab, "eulji_table", None
                        ):
                            current_row = target_table.currentRow()
                            current_col = target_table.currentColumn()
                            formula_col = self.parent_tab.EULJI_COLS.get("FORMULA", 6)

                            if current_col == formula_col:
                                # [Phase 1-2] 산출수식 Enter 연속입력 처리
                                self._handle_formula_enter(
                                    target_table, current_row, current_col
                                )
                                return True  # 이벤트 소비, 기본 Enter 동작 방지

                            item_col = self.parent_tab.EULJI_COLS.get("ITEM", 5)
                            if current_col == item_col:
                                trigger = getattr(
                                    self.parent_tab, "unit_price_trigger", None
                                )
                                if (
                                    trigger
                                    and trigger.popup
                                    and trigger.popup.isVisible()
                                ):
                                    # 산출일위표가 열려있으면 해당 팝업의 테이블에 포커스 이동
                                    trigger.popup.table.setFocus()
                                    if trigger.popup.table.rowCount() > 0:
                                        trigger.popup.table.setCurrentCell(
                                            0, trigger.popup.UNIT_PRICE_COLS["LIST"]
                                        )
                                    return True

                    if key == Qt.Key.Key_Escape:
                        if target_table == self.parent_tab.eulji_table:
                            self.parent_tab._switch_view(0)
                        return True

                    # [Phase 2-3] Ctrl+1~9 → 구간접속 자동 산출
                    for num in range(1, 10):
                        if key == getattr(Qt.Key, f"Key_{num}"):
                            if ctrl and target_table == getattr(
                                self.parent_tab, "eulji_table", None
                            ):
                                self._handle_ctrl_number(target_table, num)
                                return True
            return super().eventFilter(obj, event)
        except Exception as e:
            self._log(f"ERROR: TableEventFilter: {e}")
            return False

    def _handle_formula_enter(self, table, row, col):
        """[Phase 1-2] 산출수식 Enter 연속입력 처리"""
        try:
            from utils.formula_parser import calc_byte_length

            formula_item = table.item(row, col)
            if not formula_item:
                return

            current_text = formula_item.text().strip()

            # 현재 텍스트에서 숫자 추출하여 현재 값 확인
            from utils.formula_parser import parse_formula

            current_value = parse_formula(current_text)

            # "+" 추가하여 연속입력 준비
            new_text = current_text + "+" if current_text else ""
            new_byte_len = calc_byte_length(new_text)

            if new_byte_len > self.FORMULA_MAX_BYTES:
                # 40byte 초과: 다음 행으로 이동하여 이어서 입력
                next_row = row + 1

                # 다음 행이 없으면 추가
                if next_row >= table.rowCount():
                    table.insertRow(next_row)

                # 다음 행의 산출목록이 비어있으면 현재 행에서 복사
                item_col = self.parent_tab.EULJI_COLS.get("ITEM", 5)
                next_item = table.item(next_row, item_col)
                current_item = table.item(row, item_col)
                current_item_text = current_item.text().strip() if current_item else ""

                if not next_item or not next_item.text().strip():
                    if current_item_text:
                        # 새 행에 산출목록 복사
                        if not next_item:
                            next_item = QTableWidgetItem()
                            table.setItem(next_row, item_col, next_item)
                        next_item.setText(current_item_text)

                # 다음 행의 FORMULA 컬럼으로 포커스 이동
                table.setCurrentCell(next_row, col)
                table.editItem(table.item(next_row, col))

                # 다음 행에 "+"만 미리 입력 (사용자 입력을 기다림)
                # 실제 데이터는 사용자가 입력 후 Enter를 누를 때 처리
            else:
                # 40byte 이내: 같은 셀에 "+" 추가하고 계속 입력
                formula_item.setText(new_text)
                table.setCurrentCell(row, col)
                table.editItem(formula_item)  # 편집 상태 유지

        except Exception as e:
            self._log(f"ERROR: _handle_formula_enter: {e}")

    def _handle_copy(self, table):
        """[Phase 1-3] Ctrl+C - 셀/행 복사"""
        try:
            current_row = table.currentRow()
            current_col = table.currentColumn()
            num_col = self.parent_tab.EULJI_COLS.get("NUM", 0)

            # NUM 열에서 복사 → 행 전체 복사
            if current_col == num_col:
                row_data = []
                for col in range(table.columnCount()):
                    item = table.item(current_row, col)
                    row_data.append(item.text() if item else "")
                # 시스템 클립보드에 탭 구분 텍스트 복사
                clipboard_text = "\t".join(row_data)
                QApplication.clipboard().setText(clipboard_text)
                # 내부 클립보드에 행 복사 저장
                self.parent_tab._clipboard = {"type": "row", "data": row_data}
            else:
                # 다른 열 → 해당 셀만 복사
                item = table.item(current_row, current_col)
                text = item.text() if item else ""
                QApplication.clipboard().setText(text)
                # 내부 클립보드에 셀 복사 저장
                self.parent_tab._clipboard = {
                    "type": "cell",
                    "data": text,
                    "row": current_row,
                    "col": current_col,
                }

            self._log(f"복사 완료: {self.parent_tab._clipboard}")

        except Exception as e:
            self._log(f"ERROR: _handle_copy: {e}")

    def _handle_paste(self, table):
        """[Phase 1-3] Ctrl+V - 셀/행 붙이기"""
        try:
            clipboard = QApplication.clipboard()
            text = clipboard.text()

            current_row = table.currentRow()
            current_col = table.currentColumn()
            num_col = self.parent_tab.EULJI_COLS.get("NUM", 0)

            # 내부 클립보드 데이터가 있으면 우선 사용
            if hasattr(self.parent_tab, "_clipboard") and self.parent_tab._clipboard:
                clip = self.parent_tab._clipboard
                if clip.get("type") == "row":
                    # 행 복사 데이터 → 새 행 삽입 후 붙이기
                    self.parent_tab.record_undo(table, "insert", current_row)
                    table.insertRow(current_row)
                    table.setRowHeight(current_row, 22)  # 기본 행 높이
                    for col_idx, value in enumerate(clip.get("data", [])):
                        if col_idx < table.columnCount():
                            item = QTableWidgetItem(value)
                            table.setItem(current_row, col_idx, item)
                    self._log(f"행 붙이기 완료: {clip}")
                else:
                    # 셀 복사 데이터 → 현재 위치에 붙이기
                    if clip.get("data"):
                        self.parent_tab.record_undo(
                            table,
                            "edit",
                            current_row,
                            {
                                current_col: table.item(current_row, current_col).text()
                                if table.item(current_row, current_col)
                                else ""
                            },
                        )
                        item = QTableWidgetItem(str(clip.get("data")))
                        table.setItem(current_row, current_col, item)
                    self._log(f"셀 붙이기 완료: {clip}")
            elif text:
                # 시스템 클립보드 → 탭 구분 파싱
                values = text.split("\t")

                # NUM 열에서 붙여넣기 시도 → 행 복사로 처리
                if current_col == num_col and len(values) > 1:
                    self.parent_tab.record_undo(table, "insert", current_row)
                    table.insertRow(current_row)
                    table.setRowHeight(current_row, 22)
                    for col_idx, value in enumerate(values):
                        if col_idx < table.columnCount():
                            item = QTableWidgetItem(value)
                            table.setItem(current_row, col_idx, item)
                else:
                    # 일반 셀 붙이기
                    if values and current_row >= 0:
                        self.parent_tab.record_undo(
                            table,
                            "edit",
                            current_row,
                            {
                                current_col: table.item(current_row, current_col).text()
                                if table.item(current_row, current_col)
                                else ""
                            },
                        )
                        item = QTableWidgetItem(values[0] if values else "")
                        table.setItem(current_row, current_col, item)

        except Exception as e:
            self._log(f"ERROR: _handle_paste: {e}")

    def _handle_cut(self, table):
        """[Phase 1-3] Ctrl+X - 잘라내기"""
        try:
            # 먼저 복사
            self._handle_copy(table)
            # 然后 삭제 (행의 경우)
            current_col = table.currentColumn()
            num_col = self.parent_tab.EULJI_COLS.get("NUM", 0)
            if current_col == num_col:
                current_row = table.currentRow()
                if current_row >= 0:
                    item_texts = []
                    for col in range(table.columnCount()):
                        item = table.item(current_row, col)
                        item_texts.append(item.text() if item else "")
                    self.parent_tab.record_undo(
                        table, "delete", current_row, item_texts
                    )
                    table.removeRow(current_row)
                    table.insertRow(table.rowCount())
        except Exception as e:
            self._log(f"ERROR: _handle_cut: {e}")

    def _handle_f4_no_quantity(self, table):
        """[Phase 1-4] F4 - 수량 없이 입력 (1@)"""
        try:
            current_row = table.currentRow()
            formula_col = self.parent_tab.EULJI_COLS.get("FORMULA", 6)
            total_col = self.parent_tab.EULJI_COLS.get("TOTAL", 7)

            # 산출수식에 "1@" 입력
            self.parent_tab.record_undo(
                table,
                "edit",
                current_row,
                {
                    formula_col: table.item(current_row, formula_col).text()
                    if table.item(current_row, formula_col)
                    else ""
                },
            )
            formula_item = table.item(current_row, formula_col)
            if not formula_item:
                formula_item = QTableWidgetItem()
                table.setItem(current_row, formula_col, formula_item)
            formula_item.setText("1@")

            # 계(TOTAL)를 0으로 설정
            self.parent_tab.record_undo(
                table,
                "edit",
                current_row,
                {
                    total_col: table.item(current_row, total_col).text()
                    if table.item(current_row, total_col)
                    else ""
                },
            )
            total_item = table.item(current_row, total_col)
            if not total_item:
                total_item = QTableWidgetItem()
                table.setItem(current_row, total_col, total_item)
            total_item.setText("")

            # 다음 행으로 이동
            next_row = current_row + 1
            if next_row >= table.rowCount():
                table.insertRow(next_row)
            table.setCurrentCell(next_row, formula_col)

            self._log(f"F4 수량없이 입력 완료: 행 {current_row}")

        except Exception as e:
            self._log(f"ERROR: _handle_f4_no_quantity: {e}")

    def _handle_ctrl_number(self, table, num: int):
        """[Phase 2-3] Ctrl+N - 위로 N줄의 구간을 합산하여 접속선 산출"""
        try:
            from core.section_connection import (
                calculate_section_connection,
                create_connection_item,
            )

            current_row = table.currentRow()
            if current_row < 0:
                return

            # 위로 N줄의 행 번호 계산
            rows_to_sum = list(range(max(0, current_row - num), current_row))

            if not rows_to_sum:
                self._log(f"합산할 행이 없음: 현재행={current_row}, N={num}")
                return

            # 구간 계산
            total_sections = 0
            for row in rows_to_sum:
                formula_item = table.item(row, 6)  # FORMULA 컬럼
                if formula_item and formula_item.text().strip():
                    from utils.formula_parser import count_sections

                    sections = count_sections(formula_item.text())
                    total_sections += sections

            if total_sections == 0:
                self._log("합산된 구간이 없음")
                return

            # 접속선 계산
            conn_info = calculate_section_connection(f"0.2*2*{total_sections}")

            # 현재 행에 접속선 데이터 입력
            self.parent_tab.record_undo(table, "edit", current_row, {})
            table.blockSignals(True)

            # 산출목록
            item_col = self.parent_tab.EULJI_COLS.get("ITEM", 5)
            item = table.item(current_row, item_col)
            if not item:
                item = QTableWidgetItem()
                table.setItem(current_row, item_col, item)
            item.setText("접속선")

            # 산출수식
            formula_col = self.parent_tab.EULJI_COLS.get("FORMULA", 6)
            formula = table.item(current_row, formula_col)
            if not formula:
                formula = QTableWidgetItem()
                table.setItem(current_row, formula_col, formula)
            formula.setText(conn_info["formula"])

            # 계(TOTAL)
            total_col = self.parent_tab.EULJI_COLS.get("TOTAL", 7)
            total = table.item(current_row, total_col)
            if not total:
                total = QTableWidgetItem()
                table.setItem(current_row, total_col, total)
            total.setText(str(conn_info["total_length"]))

            # 단위
            unit_col = self.parent_tab.EULJI_COLS.get("UNIT", 8)
            unit = table.item(current_row, unit_col)
            if not unit:
                unit = QTableWidgetItem()
                table.setItem(current_row, unit_col, unit)
            unit.setText("m")

            table.blockSignals(False)

            self._log(
                f"Ctrl+{num} 접속선 산출 완료: {total_sections}구간, {conn_info['total_length']}m"
            )

        except Exception as e:
            self._log(f"ERROR: _handle_ctrl_number: {e}")

    def _show_popup_safe(self, table, row, col):
        """팝업 안전 호출 (부모 탭의 공통 메서드로 위임)"""
        try:
            self._log(f"_show_popup_safe called: row={row}, col={col}")
            self.parent_tab._show_reference_popup(row, col)
        except Exception as e:
            self._log(f"ERROR: _show_popup_safe: {e}")
