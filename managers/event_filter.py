# -*- coding: utf-8 -*-
from PyQt6.QtCore import Qt, QObject, QEvent, QTimer
from PyQt6.QtWidgets import QApplication, QTableWidget, QWidget

class TableEventFilter(QObject):
    """테이블 키 이벤트 필터"""

    _instance_count = 0 # 디버깅용 카운트

    def __init__(self, parent_tab):
        super().__init__()
        self.parent_tab = parent_tab
        TableEventFilter._instance_count += 1
        self._log_file = "tab_debug.log"
        self._log(f"TableEventFilter initialized. Instance count: {TableEventFilter._instance_count}")
        
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
                if not hasattr(event, "key"): return False
                key = event.key()
                
                # Tab 키만 처리 (Shift+Tab은 제외하여 이전 셀 이동 허용)
                modifiers = event.modifiers() & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier)
                
                if key == Qt.Key.Key_Tab and modifiers == Qt.KeyboardModifier.NoModifier:
                    self._log(f"Tab Key Detected! Event type: {event.type()}")
                    target_table = None
                    # 현재 포커스 대상 위젯
                    focus_w = QApplication.focusWidget() or (obj if isinstance(obj, QWidget) else None)
                    # self._log(f"Focus widget: {focus_w}, type: {type(focus_w)}")
                    
                    if focus_w:
                        # 을지 테이블 또는 그 하위 위젯(에디터/뷰포트 등)인지 확인
                        if hasattr(self.parent_tab, "eulji_table") and self.parent_tab.eulji_table is not None:
                            t = self.parent_tab.eulji_table
                            # 에디터가 열려있을 경우 focus_w는 QLineEdit 등일 수 있음
                            if t == focus_w or t.isAncestorOf(focus_w) or focus_w == t.viewport():
                                target_table = t
                                # self._log("Matched eulji_table!")
                        
                        # 갑지 테이블 체크
                        if not target_table and hasattr(self.parent_tab, "gapji_table") and self.parent_tab.gapji_table is not None:
                            t = self.parent_tab.gapji_table
                            if t == focus_w or t.isAncestorOf(focus_w) or focus_w == t.viewport():
                                target_table = t
                                # self._log("Matched gapji_table!")
                    
                    if target_table:
                        # 현재 행/열 (에디터 상태여도 테이블의 currentCell은 유지됨)
                        current_row = target_table.currentRow()
                        current_col = target_table.currentColumn()
                        # self._log(f"Target Table Found! Row: {current_row}, Col: {current_col}")
                        
                        # (A) 갑지에서의 탭 -> 을지로 네비게이션
                        if target_table == self.parent_tab.gapji_table and current_col == self.parent_tab.GONGJONG_COL:
                            event.accept()
                            if event.type() == QEvent.Type.KeyPress:
                                # 실제 키가 눌렸을 때 로직 수행
                                if hasattr(self.parent_tab, "lighting_manager"):
                                    item = target_table.item(current_row, current_col)
                                    if item and item.data(Qt.ItemDataRole.UserRole):
                                        self.parent_tab.lighting_manager.edit_gapji_row(current_row)
                                        return True
                                self.parent_tab._navigate_to_eulji(current_row)
                            return True # ShortcutOverride 차단
                        
                        # (B) 을지(산출목록/수식)에서의 탭 -> 자료사전 호출
                        elif target_table == self.parent_tab.eulji_table and current_col in [self.parent_tab.EULJI_COLS["ITEM"], self.parent_tab.EULJI_COLS["FORMULA"]]:
                            self._log(f"Tab in Eulji Item/Formula Column ({current_col})")
                            event.accept()
                            if event.type() == QEvent.Type.KeyPress:
                                # 팝업 호출 전 에디터 닫기 (데이터 커밋)
                                if focus_w != target_table:
                                    target_table.setFocus()
                                
                                # 지연 호출로 윈도우 포커스 충돌 방지 및 에디터 정리 시간 확보
                                QTimer.singleShot(10, lambda: self.parent_tab._show_reference_popup(current_row, current_col))
                            return True
                
            # 기타 단축키 로직 (KeyPress 전용)
            if event.type() == QEvent.Type.KeyPress:
                key = event.key()
                ctrl = event.modifiers() & Qt.KeyboardModifier.ControlModifier
                self._log(f"KeyPress: key={key}, modifiers={event.modifiers()} (Ctrl={bool(ctrl)}) on {obj}")
                
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
                            self.parent_tab.record_undo(target_table, "delete", row, item_texts)
                            target_table.removeRow(row)
                            # [NEW] 행 삭제 후 그리드 유지를 위해 마지막에 빈 행 추가
                            target_table.insertRow(target_table.rowCount())
                        return True

                    if key == Qt.Key.Key_Z and ctrl:
                        self.parent_tab.undo()
                        return True

                    # [NEW] F3 → 산출일위표 토글 (매뉴얼: 산출목록에서 F3으로 산출일위대가 표시/숨기기)
                    if key == Qt.Key.Key_F3 and target_table == getattr(self.parent_tab, 'eulji_table', None):
                        trigger = getattr(self.parent_tab, 'unit_price_trigger', None)
                        if trigger and trigger.popup:
                            if trigger.popup.isVisible():
                                trigger.popup.hide_popup()
                            else:
                                current_row = target_table.currentRow()
                                current_col = target_table.currentColumn()
                                item_col = self.parent_tab.EULJI_COLS.get("ITEM", 5)
                                trigger.handle_cell_selection(current_row, item_col)
                        return True

                    # [NEW] Enter → 산출목록 컬럼에서 Enter 시 산출일위표에 포커스 이동
                    if key in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
                        if target_table == getattr(self.parent_tab, 'eulji_table', None):
                            current_col = target_table.currentColumn()
                            item_col = self.parent_tab.EULJI_COLS.get("ITEM", 5)
                            if current_col == item_col:
                                trigger = getattr(self.parent_tab, 'unit_price_trigger', None)
                                if trigger and trigger.popup and trigger.popup.isVisible():
                                    # 산출일위표가 열려있으면 해당 팝업의 테이블에 포커스 이동
                                    trigger.popup.table.setFocus()
                                    if trigger.popup.table.rowCount() > 0:
                                        trigger.popup.table.setCurrentCell(0, trigger.popup.UNIT_PRICE_COLS["LIST"])
                                    return True
                            # 산출목록 컬럼이 아니면 기본 Enter 동작(다음 행 이동)은 column_settings에서 처리

                    if key == Qt.Key.Key_Escape:
                        if target_table == self.parent_tab.eulji_table:
                            self.parent_tab._switch_view(0)
                        return True
            return super().eventFilter(obj, event)
        except Exception as e:
            self._log(f"ERROR: TableEventFilter: {e}")
            return False

    def _show_popup_safe(self, table, row, col):
        """팝업 안전 호출 (부모 탭의 공통 메서드로 위임)"""
        try:
            self._log(f"_show_popup_safe called: row={row}, col={col}")
            self.parent_tab._show_reference_popup(row, col)
        except Exception as e:
            self._log(f"ERROR: _show_popup_safe: {e}")
