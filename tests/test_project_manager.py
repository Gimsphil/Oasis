# -*- coding: utf-8 -*-
"""project_manager 단위 테스트 (UI 없는 로직 레이어 검증)"""
import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest


# ProjectManager는 UI (QTableWidget) 의존성이 있으므로
# 논리 단위만 분리하여 테스트

class FakeTable:
    """QTableWidget 최소 스텁"""
    def __init__(self, rows, cols):
        self._data = [['' for _ in range(cols)] for _ in range(rows)]
    def rowCount(self): return len(self._data)
    def columnCount(self): return len(self._data[0]) if self._data else 0
    def item(self, r, c):
        class _Item:
            def __init__(self, t): self.t = t
            def text(self): return self.t
        return _Item(self._data[r][c]) if self._data[r][c] else None
    def clearContents(self): pass
    def setRowCount(self, n): self._data = [[''] * self.columnCount() for _ in range(n)]

class FakeTab:
    def __init__(self):
        # UI 없는 테스트를 위해 column_settings 임포트(PyQt6 의존성) 제거
        self.gapji_table = FakeTable(10, 9)
        self.eulji_table = FakeTable(10, 10)
        self.eulji_data = {}
        self.current_gongjong = ""
        self.project_root = os.path.dirname(os.path.dirname(__file__))
        self.EULJI_COLS = {"NUM": 0, "ITEM": 5, "FORMULA": 6, "TOTAL": 7, "UNIT": 8}
        self.main_window = None
    def reset_internal_data(self):
        self.eulji_data = {}
        self.current_gongjong = ""
    def _cleanup_unsaved_chunks(self): pass


class TestProjectManagerSerialization:
    def setup_method(self):
        from core.project_manager import ProjectManager
        self.tab = FakeTab()
        self.pm = ProjectManager(self.tab)

    def test_gather_returns_required_keys(self):
        data = self.pm._gather_all_data()
        assert "version" in data
        assert "gapji" in data
        assert "eulji" in data
        assert "gongjong_list" in data
        assert "unit_price_chunks" in data

    def test_save_and_load_roundtrip(self):
        """save → load 왕복 테스트"""
        self.tab.eulji_data = {"공종A": [["1", "A", "", "", "", "전선", "3+2", "5", "m", ""]]}
        with tempfile.NamedTemporaryFile(suffix=".oasis", delete=False, mode="w") as f:
            tmp = f.name
        try:
            result = self.pm.save_project(tmp)
            assert result is True
            assert os.path.exists(tmp)
            with open(tmp, encoding="utf-8") as f:
                data = json.load(f)
            assert data["eulji"]["공종A"][0][5] == "전선"
        finally:
            os.unlink(tmp)

    def test_load_nonexistent_file(self):
        result = self.pm.load_project("/nonexistent/path/project.oasis")
        assert result is False
