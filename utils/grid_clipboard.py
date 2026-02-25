# -*- coding: utf-8 -*-
"""
그리드 클립보드 핸들러 모듈
Grid Clipboard Handler - 엑셀 스타일 복사/붙이기/끌기 복사 + F5/F6/F7/F8 블록 기능
"""

from PyQt6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QApplication,
    QAbstractItemView,
    QWidget,
    QStyleOptionViewItem,
    QTableWidgetSelectionRange,
)
from PyQt6.QtCore import Qt, QObject, QEvent, QRect, QPoint
from PyQt6.QtGui import QKeyEvent, QPainter, QColor, QPen, QCursor, QBrush


class GridClipboardHandler(QObject):
    """테이블 복사/붙이기/끌기 복사/편집/블록 모드 핸들러"""

    # 번호 열 인덱스 (기본값 0)
    NUMBER_COLUMN = 0

    def __init__(self, table: QTableWidget):
        super().__init__(table)
        self.table = table

        # 끌기 복사 상태
        self.is_fill_dragging = False
        self.fill_start_row = -1
        self.fill_start_col = -1
        self.fill_start_value = ""

        # ===== 블록 모드 상태 =====
        self.block_mode = False  # 블록 지정 모드 활성화
        self.block_first_press = False  # 첫 번째 F5 눌림 여부
        self.block_start_row = -1
        self.block_start_col = -1
        self.block_end_row = -1
        self.block_end_col = -1
        self.block_confirmed = False  # 블록 범위 확정 여부

        # 채우기 핸들 오버레이 (작은 검정 사각형)
        self.fill_handle_widget = QWidget(table.viewport())
        self.fill_handle_widget.setFixedSize(8, 8)
        self.fill_handle_widget.setStyleSheet(
            "background-color: #000000; border: 1px solid #ffffff;"
        )
        self.fill_handle_widget.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.fill_handle_widget.hide()

        # 이벤트 필터 설치
        self.table.viewport().installEventFilter(self)
        self.table.installEventFilter(self)
        self.fill_handle_widget.installEventFilter(self)

        # 셀 선택 변경 시 핸들 위치 업데이트
        self.table.currentCellChanged.connect(self._update_fill_handle_position)
        self.table.horizontalScrollBar().valueChanged.connect(
            self._update_fill_handle_position
        )
        self.table.verticalScrollBar().valueChanged.connect(
            self._update_fill_handle_position
        )

        # 행 헤더(번호 열 왼쪽 버튼) 클릭 시 블록 지정
        header = self.table.verticalHeader()
        if header:
            header.sectionClicked.connect(self._on_row_header_clicked)

    def _update_fill_handle_position(self):
        """선택된 셀의 오른쪽 하단에 채우기 핸들 위치 업데이트"""
        try:
            current_row = self.table.currentRow()
            current_col = self.table.currentColumn()

            if current_row < 0 or current_col < 0:
                self.fill_handle_widget.hide()
                return

            current_item = self.table.item(current_row, current_col)
            if not current_item:
                # 아이템이 없어도 셀 위치는 계산 가능
                pass

            # 셀 영역 계산
            cell_rect = self.table.visualRect(
                self.table.model().index(current_row, current_col)
            )

            if cell_rect.isValid():
                # 오른쪽 하단 모서리에 위치
                handle_x = cell_rect.right() - 4
                handle_y = cell_rect.bottom() - 4

                self.fill_handle_widget.move(handle_x, handle_y)
                self.fill_handle_widget.show()
                self.fill_handle_widget.raise_()
            else:
                self.fill_handle_widget.hide()
        except Exception:
            self.fill_handle_widget.hide()

    def eventFilter(self, obj, event):
        """이벤트 필터 - 키보드 및 마우스 이벤트 처리"""

        # 키보드 이벤트
        if event.type() == QEvent.Type.KeyPress:
            return self._handle_key_press(event)

        # 채우기 핸들 위젯 마우스 이벤트
        try:
            if obj == self.fill_handle_widget:
                if event.type() == QEvent.Type.MouseButtonPress:
                    if event.button() == Qt.MouseButton.LeftButton:
                        # 드래그 시작
                        current_item = self.table.currentItem()
                        if current_item:
                            self.is_fill_dragging = True
                            self.fill_start_row = self.table.currentRow()
                            self.fill_start_col = self.table.currentColumn()
                            self.fill_start_value = current_item.text()
                            self.table.viewport().setCursor(
                                QCursor(Qt.CursorShape.CrossCursor)
                            )
                            return True
                elif event.type() == QEvent.Type.MouseMove:
                    if self.is_fill_dragging:
                        # 드래그 중 - 테이블 좌표로 변환
                        global_pos = self.fill_handle_widget.mapToGlobal(event.pos())
                        viewport_pos = self.table.viewport().mapFromGlobal(global_pos)
                        return self._handle_mouse_move_drag(viewport_pos)
                elif event.type() == QEvent.Type.MouseButtonRelease:
                    if self.is_fill_dragging:
                        global_pos = self.fill_handle_widget.mapToGlobal(event.pos())
                        viewport_pos = self.table.viewport().mapFromGlobal(global_pos)
                        return self._handle_mouse_release_drag(viewport_pos)
        except RuntimeError:
            pass

        # 뷰포트 마우스 이벤트 (끌기 복사용)
        try:
            if obj == self.table.viewport():
                if event.type() == QEvent.Type.MouseButtonPress:
                    return self._handle_mouse_press(event)
                elif event.type() == QEvent.Type.MouseMove:
                    if self.is_fill_dragging:
                        return self._handle_mouse_move_drag(event.pos())
                    return self._handle_mouse_move(event)
                elif event.type() == QEvent.Type.MouseButtonRelease:
                    if self.is_fill_dragging:
                        return self._handle_mouse_release_drag(event.pos())
                    return self._handle_mouse_release(event)
        except RuntimeError:
            # 위젯이 삭제된 경우 무시
            return False

        return False

    def _handle_key_press(self, event: QKeyEvent) -> bool:
        """키보드 이벤트 처리"""
        key = event.key()
        modifiers = event.modifiers()

        # ===== F5: 블록 지정 모드 =====
        if key == Qt.Key.Key_F5:
            self._toggle_block_mode()
            return True

        # ===== F6: 복사 (블록 모드에서) =====
        if key == Qt.Key.Key_F6:
            self._copy_block()
            return True

        # ===== F7: 이동 (블록 모드에서) =====
        if key == Qt.Key.Key_F7:
            self._move_block()
            return True

        # ===== F8 또는 Esc: 블록 해제 =====
        if key in (Qt.Key.Key_F8, Qt.Key.Key_Escape):
            self._cancel_block()
            return True

        # F2 또는 Insert → 편집 모드
        if key in (Qt.Key.Key_F2, Qt.Key.Key_Insert):
            current_item = self.table.currentItem()
            if current_item:
                self.table.editItem(current_item)
            else:
                row = self.table.currentRow()
                col = self.table.currentColumn()
                if row >= 0 and col >= 0:
                    new_item = QTableWidgetItem("")
                    self.table.setItem(row, col, new_item)
                    self.table.editItem(new_item)
            return True

        # Ctrl+C → 복사
        if key == Qt.Key.Key_C and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.copy_selection()
            return True

        # Ctrl+V → 붙여넣기
        if key == Qt.Key.Key_V and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.paste_clipboard()
            return True

        # Ctrl+X → 잘라내기
        if key == Qt.Key.Key_X and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.cut_selection()
            return True

        # Delete → 선택 영역 삭제
        if key == Qt.Key.Key_Delete:
            self.delete_selection()
            return True

        # Ctrl+A → 전체 선택
        if key == Qt.Key.Key_A and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.table.selectAll()
            return True

        return False

    # ========== F5/F6/F7/F8 블록 기능 ==========

    def _toggle_block_mode(self):
        """F5: 블록 지정 모드 토글"""
        current_row = self.table.currentRow()
        current_col = self.table.currentColumn()

        if current_row < 0 or current_col < 0:
            return

        if not self.block_first_press:
            # 첫 번째 F5: 블록 시작점 설정
            self.block_mode = True
            self.block_first_press = True
            self.block_start_row = current_row
            self.block_start_col = current_col
            self.block_end_row = current_row
            self.block_end_col = current_col
            self.block_confirmed = False

            # 시작점 하이라이트
            self._highlight_block()
        else:
            # 두 번째 F5: 블록 끝점 확정
            self.block_end_row = current_row
            self.block_end_col = current_col
            self.block_confirmed = True
            self.block_first_press = False

            # 블록 범위 정렬 (시작 < 끝)
            if self.block_start_row > self.block_end_row:
                self.block_start_row, self.block_end_row = (
                    self.block_end_row,
                    self.block_start_row,
                )
            if self.block_start_col > self.block_end_col:
                self.block_start_col, self.block_end_col = (
                    self.block_end_col,
                    self.block_start_col,
                )

            # 블록 범위 하이라이트
            self._highlight_block()

    def _highlight_block(self):
        """블록 범위 하이라이트 표시"""
        if not self.block_mode:
            return

        # 테이블 선택 범위 설정
        self.table.clearSelection()
        selection_range = QTableWidgetSelectionRange(
            self.block_start_row,
            self.block_start_col,
            self.block_end_row,
            self.block_end_col,
        )
        self.table.setRangeSelected(selection_range, True)

    def _cancel_block(self):
        """F8/Esc: 블록 해제"""
        self.block_mode = False
        self.block_first_press = False
        self.block_confirmed = False
        self.block_start_row = -1
        self.block_start_col = -1
        self.block_end_row = -1
        self.block_end_col = -1

        # 선택 해제
        self.table.clearSelection()

    def _copy_block(self):
        """F6: 블록 복사"""
        if not self.block_confirmed:
            # 블록이 지정되지 않은 상태
            return

        current_row = self.table.currentRow()
        current_col = self.table.currentColumn()

        if current_row < 0 or current_col < 0:
            return

        self.table.blockSignals(True)

        # 커서가 번호 열에 있으면 행 전체 복사, 아니면 현재 열만 복사
        is_row_copy = self.block_start_col == self.NUMBER_COLUMN

        row_count = self.block_end_row - self.block_start_row + 1

        for r_offset in range(row_count):
            src_row = self.block_start_row + r_offset
            dst_row = current_row + r_offset

            # 행 확장
            if dst_row >= self.table.rowCount():
                self.table.setRowCount(dst_row + 100)

            if is_row_copy:
                # 행 전체 복사 (모든 열)
                for col in range(self.table.columnCount()):
                    src_item = self.table.item(src_row, col)
                    src_text = src_item.text() if src_item else ""

                    dst_item = self.table.item(dst_row, col)
                    if not dst_item:
                        dst_item = QTableWidgetItem()
                        self.table.setItem(dst_row, col, dst_item)
                    dst_item.setText(src_text)
            else:
                # 현재 열만 복사
                for c_offset in range(self.block_end_col - self.block_start_col + 1):
                    src_col = self.block_start_col + c_offset
                    dst_col = current_col + c_offset

                    if dst_col >= self.table.columnCount():
                        continue

                    src_item = self.table.item(src_row, src_col)
                    src_text = src_item.text() if src_item else ""

                    dst_item = self.table.item(dst_row, dst_col)
                    if not dst_item:
                        dst_item = QTableWidgetItem()
                        self.table.setItem(dst_row, dst_col, dst_item)
                    dst_item.setText(src_text)

        self.table.blockSignals(False)

        # 블록 해제
        self._cancel_block()

    def _move_block(self):
        """F7: 블록 이동 (잘라내기 + 삽입)"""
        if not self.block_confirmed:
            return

        current_row = self.table.currentRow()
        current_col = self.table.currentColumn()

        if current_row < 0 or current_col < 0:
            return

        # 자기 자신 영역으로 이동 방지
        if (
            self.block_start_row <= current_row <= self.block_end_row
            and self.block_start_col <= current_col <= self.block_end_col
        ):
            self._cancel_block()
            return

        self.table.blockSignals(True)

        # 커서가 번호 열에 있으면 행 이동
        is_row_move = self.block_start_col == self.NUMBER_COLUMN

        row_count = self.block_end_row - self.block_start_row + 1

        # 1. 원본 데이터 저장
        saved_data = []
        for r_offset in range(row_count):
            src_row = self.block_start_row + r_offset
            row_data = []

            if is_row_move:
                # 행 전체 저장
                for col in range(self.table.columnCount()):
                    item = self.table.item(src_row, col)
                    row_data.append(item.text() if item else "")
            else:
                # 선택 열만 저장
                for c_offset in range(self.block_end_col - self.block_start_col + 1):
                    src_col = self.block_start_col + c_offset
                    item = self.table.item(src_row, src_col)
                    row_data.append(item.text() if item else "")

            saved_data.append(row_data)

        # 2. 원본 삭제 (행 이동인 경우 행 삭제, 아니면 셀 클리어)
        if is_row_move:
            # 행 삭제 (뒤에서부터)
            for r in range(self.block_end_row, self.block_start_row - 1, -1):
                self.table.removeRow(r)

            # 삭제 후 목적 위치 조정
            if current_row > self.block_start_row:
                current_row -= row_count
        else:
            # 셀 내용 삭제
            for r_offset in range(row_count):
                src_row = self.block_start_row + r_offset
                for c_offset in range(self.block_end_col - self.block_start_col + 1):
                    src_col = self.block_start_col + c_offset
                    item = self.table.item(src_row, src_col)
                    if item:
                        item.setText("")

        # 3. 목적 위치에 삽입
        if is_row_move:
            # 행 삽입
            for r_offset in range(row_count):
                dst_row = current_row + r_offset
                self.table.insertRow(dst_row)

                for col, value in enumerate(saved_data[r_offset]):
                    item = QTableWidgetItem(value)
                    self.table.setItem(dst_row, col, item)
        else:
            # 셀에 데이터 복사
            for r_offset in range(row_count):
                dst_row = current_row + r_offset

                if dst_row >= self.table.rowCount():
                    self.table.setRowCount(dst_row + 100)

                for c_offset, value in enumerate(saved_data[r_offset]):
                    dst_col = current_col + c_offset
                    if dst_col >= self.table.columnCount():
                        continue

                    item = self.table.item(dst_row, dst_col)
                    if not item:
                        item = QTableWidgetItem()
                        self.table.setItem(dst_row, dst_col, item)
                    item.setText(value)

        self.table.blockSignals(False)

        # 블록 해제
        self._cancel_block()

    def _on_row_header_clicked(self, row: int):
        """행 헤더(번호 왼쪽 버튼) 클릭 시 블록 지정"""
        if not self.block_mode:
            # 블록 모드 시작
            self.block_mode = True
            self.block_first_press = True
            self.block_start_row = row
            self.block_start_col = 0  # 번호 열부터
            self.block_end_row = row
            self.block_end_col = self.table.columnCount() - 1  # 마지막 열까지
            self.block_confirmed = True  # 바로 확정

            self._highlight_block()
        else:
            # 이미 블록 모드면 범위 확장
            self.block_end_row = row
            self.block_confirmed = True

            # 범위 정렬
            if self.block_start_row > self.block_end_row:
                self.block_start_row, self.block_end_row = (
                    self.block_end_row,
                    self.block_start_row,
                )

            self._highlight_block()

    # ========== 기존 Ctrl+C/V 복사/붙이기 ==========

    def copy_selection(self):
        """선택된 셀들을 클립보드에 복사 (OS 클립보드 연동)"""
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            return

        min_row = min(r.topRow() for r in selected_ranges)
        max_row = max(r.bottomRow() for r in selected_ranges)
        min_col = min(r.leftColumn() for r in selected_ranges)
        max_col = max(r.rightColumn() for r in selected_ranges)

        selected_cells = set()
        for r in selected_ranges:
            for row in range(r.topRow(), r.bottomRow() + 1):
                for col in range(r.leftColumn(), r.rightColumn() + 1):
                    selected_cells.add((row, col))

        rows_text = []
        for row in range(min_row, max_row + 1):
            row_data = []
            for col in range(min_col, max_col + 1):
                if (row, col) in selected_cells:
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                else:
                    row_data.append("")
            rows_text.append("\t".join(row_data))

        clipboard_text = "\n".join(rows_text)
        clipboard = QApplication.clipboard()
        clipboard.setText(clipboard_text)

    def paste_clipboard(self):
        """클립보드 내용을 현재 셀부터 붙여넣기"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()

        if not text:
            return

        current_row = self.table.currentRow()
        current_col = self.table.currentColumn()

        if current_row < 0 or current_col < 0:
            return

        self.table.blockSignals(True)

        rows = text.split("\n")
        for r_offset, row_text in enumerate(rows):
            if not row_text:
                continue

            cols = row_text.split("\t")
            for c_offset, cell_value in enumerate(cols):
                target_row = current_row + r_offset
                target_col = current_col + c_offset

                if target_row >= self.table.rowCount():
                    self.table.setRowCount(target_row + 100)
                if target_col >= self.table.columnCount():
                    continue

                item = self.table.item(target_row, target_col)
                if not item:
                    item = QTableWidgetItem()
                    self.table.setItem(target_row, target_col, item)
                item.setText(cell_value)

        self.table.blockSignals(False)

    def cut_selection(self):
        """선택된 셀들을 잘라내기"""
        self.copy_selection()
        self.delete_selection()

    def delete_selection(self):
        """선택된 셀들의 내용 삭제"""
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            return

        self.table.blockSignals(True)

        for r in selected_ranges:
            for row in range(r.topRow(), r.bottomRow() + 1):
                for col in range(r.leftColumn(), r.rightColumn() + 1):
                    item = self.table.item(row, col)
                    if item:
                        item.setText("")

        self.table.blockSignals(False)

    # ========== 끌기 복사 (Fill Handle) ==========

    def _is_in_fill_handle(self, pos: QPoint) -> bool:
        """마우스 위치가 끌기 핸들 영역인지 확인 (셀 오른쪽 하단 모서리)"""
        current_item = self.table.currentItem()
        if not current_item:
            return False

        cell_rect = self.table.visualItemRect(current_item)
        # 핸들 영역을 8x8 픽셀로 확대하여 클릭하기 쉽게
        handle_rect = QRect(cell_rect.right() - 8, cell_rect.bottom() - 8, 10, 10)

        return handle_rect.contains(pos)

    def _handle_mouse_press(self, event) -> bool:
        """마우스 클릭 - 끌기 복사 시작"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_in_fill_handle(event.pos()):
                current_item = self.table.currentItem()
                if current_item:
                    self.is_fill_dragging = True
                    self.fill_start_row = self.table.currentRow()
                    self.fill_start_col = self.table.currentColumn()
                    self.fill_start_value = current_item.text()
                    return True
        return False

    def _handle_mouse_move(self, event) -> bool:
        """마우스 이동 - 커서 변경 및 끌기 복사 중 표시"""
        if self.is_fill_dragging:
            # 끌기 중일 때는 십자 커서
            self.table.viewport().setCursor(QCursor(Qt.CursorShape.CrossCursor))
            return True
        else:
            if self._is_in_fill_handle(event.pos()):
                # 채우기 핸들 위: 십자 커서
                self.table.viewport().setCursor(QCursor(Qt.CursorShape.CrossCursor))
            else:
                # 일반 셀 위: 흰색 십자 또는 기본 커서
                index = self.table.indexAt(event.pos())
                if index.isValid():
                    # 셀 위에서는 화살표 커서 (엑셀 스타일)
                    self.table.viewport().setCursor(QCursor(Qt.CursorShape.ArrowCursor))
                else:
                    self.table.viewport().unsetCursor()
        return False

    def _handle_mouse_move_drag(self, pos: QPoint) -> bool:
        """드래그 중 마우스 이동 - 선택 범위 하이라이트"""
        if self.is_fill_dragging:
            self.table.viewport().setCursor(QCursor(Qt.CursorShape.CrossCursor))

            # 드래그 중 현재 위치 셀 하이라이트 (선택 범위 표시)
            index = self.table.indexAt(pos)
            if index.isValid():
                end_row = index.row()
                end_col = index.column()

                # 같은 열 또는 같은 행만 선택 범위로 하이라이트
                self.table.clearSelection()
                if end_col == self.fill_start_col:
                    # 수직 범위
                    start = min(self.fill_start_row, end_row)
                    end = max(self.fill_start_row, end_row)
                    selection = QTableWidgetSelectionRange(
                        start, self.fill_start_col, end, self.fill_start_col
                    )
                    self.table.setRangeSelected(selection, True)
                elif end_row == self.fill_start_row:
                    # 수평 범위
                    start = min(self.fill_start_col, end_col)
                    end = max(self.fill_start_col, end_col)
                    selection = QTableWidgetSelectionRange(
                        self.fill_start_row, start, self.fill_start_row, end
                    )
                    self.table.setRangeSelected(selection, True)

            return True
        return False

    def _handle_mouse_release_drag(self, pos: QPoint) -> bool:
        """드래그 종료 - 채우기 실행"""
        if self.is_fill_dragging:
            self.is_fill_dragging = False
            self.table.viewport().unsetCursor()

            index = self.table.indexAt(pos)

            if index.isValid():
                end_row = index.row()
                end_col = index.column()

                if end_col == self.fill_start_col and end_row > self.fill_start_row:
                    self._fill_down(self.fill_start_row, end_row, self.fill_start_col)
                elif end_col == self.fill_start_col and end_row < self.fill_start_row:
                    self._fill_up(end_row, self.fill_start_row, self.fill_start_col)
                elif end_row == self.fill_start_row and end_col > self.fill_start_col:
                    self._fill_right(self.fill_start_row, self.fill_start_col, end_col)
                elif end_row == self.fill_start_row and end_col < self.fill_start_col:
                    self._fill_left(self.fill_start_row, end_col, self.fill_start_col)

            # 선택 해제 및 원래 셀로 복귀
            self.table.clearSelection()
            self.table.setCurrentCell(self.fill_start_row, self.fill_start_col)
            self._update_fill_handle_position()

            return True
        return False

    def _fill_up(self, start_row: int, end_row: int, col: int):
        """위 방향으로 값 채우기"""
        self.table.blockSignals(True)

        for row in range(start_row, end_row):
            item = self.table.item(row, col)
            if not item:
                item = QTableWidgetItem()
                self.table.setItem(row, col, item)
            item.setText(self.fill_start_value)

        self.table.blockSignals(False)

    def _fill_left(self, row: int, start_col: int, end_col: int):
        """왼쪽 방향으로 값 채우기"""
        self.table.blockSignals(True)

        for col in range(start_col, end_col):
            item = self.table.item(row, col)
            if not item:
                item = QTableWidgetItem()
                self.table.setItem(row, col, item)
            item.setText(self.fill_start_value)

        self.table.blockSignals(False)

    def _handle_mouse_release(self, event) -> bool:
        """마우스 릴리즈 - 끌기 복사 완료"""
        if self.is_fill_dragging:
            self.is_fill_dragging = False
            self.table.viewport().unsetCursor()

            pos = event.pos()
            index = self.table.indexAt(pos)

            if index.isValid():
                end_row = index.row()
                end_col = index.column()

                if end_col == self.fill_start_col and end_row > self.fill_start_row:
                    self._fill_down(self.fill_start_row, end_row, self.fill_start_col)
                elif end_row == self.fill_start_row and end_col > self.fill_start_col:
                    self._fill_right(self.fill_start_row, self.fill_start_col, end_col)

            return True
        return False

    def _fill_down(self, start_row: int, end_row: int, col: int):
        """아래 방향으로 값 채우기"""
        self.table.blockSignals(True)

        for row in range(start_row + 1, end_row + 1):
            if row >= self.table.rowCount():
                self.table.setRowCount(row + 100)

            item = self.table.item(row, col)
            if not item:
                item = QTableWidgetItem()
                self.table.setItem(row, col, item)
            item.setText(self.fill_start_value)

        self.table.blockSignals(False)

    def _fill_right(self, row: int, start_col: int, end_col: int):
        """오른쪽 방향으로 값 채우기"""
        self.table.blockSignals(True)

        for col in range(start_col + 1, end_col + 1):
            if col >= self.table.columnCount():
                continue

            item = self.table.item(row, col)
            if not item:
                item = QTableWidgetItem()
                self.table.setItem(row, col, item)
            item.setText(self.fill_start_value)

        self.table.blockSignals(False)


def setup_clipboard_handler(table: QTableWidget) -> GridClipboardHandler:
    """테이블에 클립보드 핸들러 설정"""
    handler = GridClipboardHandler(table)
    table._clipboard_handler = handler
    return handler
