# -*- coding: utf-8 -*-
"""
분전반 산출 매니저 (복구용 최소 구현)
"""


class DistributionBoardManager:
    """OutputDetailTab과 연결되는 분전반 매니저."""

    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        self._current_row = None

    def edit_row(self, row):
        """선택한 을지 행을 분전반 편집 대상으로 지정."""
        self._current_row = row

        table = getattr(self.parent_tab, "eulji_table", None)
        item_col = self.parent_tab.EULJI_COLS.get("ITEM", 5)
        if table is not None and row >= 0:
            table.setCurrentCell(row, item_col)

        print(f"[INFO] DistributionBoardManager.edit_row called: row={row}")
