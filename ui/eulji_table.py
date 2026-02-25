# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QTableWidget

class EuljiTableWidget(QTableWidget):
    """을지 테이블 위젯 - Tab 키로 자료사전 팝업 호출 등 테이블 전용 로직 관리"""
    
    def __init__(self, parent_tab=None):
        super().__init__()
        self.parent_tab = parent_tab
        self._log_file = "tab_debug.log"
        self._log("EuljiTableWidget initialized")
    
    def set_parent_tab(self, parent_tab):
        """부모 탭 설정 (테이블 생성 후 설정)"""
        self.parent_tab = parent_tab
        self._log(f"parent_tab set: {parent_tab}")
    
    def _log(self, msg):
        """파일에 디버그 로그 기록"""
        try:
            import datetime
            with open(self._log_file, "a", encoding="utf-8") as f:
                ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                f.write(f"[{ts}] EuljiTable: {msg}\n")
        except:
            pass
    
    def focusNextPrevChild(self, next):
        """TAB 키 가로채기: TableEventFilter에서 중앙 집중 처리하므로 기본 동작 수행"""
        # [REFACTORED] 로직을 TableEventFilter로 통합하여 중복 방지
        return super().focusNextPrevChild(next)
    
    def _show_reference_db_popup(self, row, col):
        """자료사전 DB 팝업 호출 (TableEventFilter._show_popup_safe와 통합 권장)"""
        if self.parent_tab:
            # 부모 탭의 통합 호출 메서드 사용
            if hasattr(self.parent_tab, "_show_reference_popup"):
                self.parent_tab._show_reference_popup(row, col)
