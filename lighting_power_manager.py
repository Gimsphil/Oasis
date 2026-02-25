# -*- coding: utf-8 -*-
"""
전등/전열 산출 매니저 (복구용 최소 구현)
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout


class LightingPowerManager:
    """OutputDetailTab과 연결되는 전등/전열 매니저."""

    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        self._side_panel = None
        self._current_row = None

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

        layout.addStretch(1)

        panel.hide()
        self._side_panel = panel
        return panel

    def toggle_panel(self):
        """우측 패널 표시/숨김 토글."""
        panel = self.create_side_panel()
        panel.setVisible(not panel.isVisible())

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
        panel.show()

    def edit_gapji_row(self, row):
        """갑지 선택 시 을지로 이동 후 전등/전열 편집 상태 동기화."""
        if hasattr(self.parent_tab, "_navigate_to_eulji"):
            try:
                self.parent_tab._navigate_to_eulji(row)
            except Exception:
                pass

        self.edit_row(row)
