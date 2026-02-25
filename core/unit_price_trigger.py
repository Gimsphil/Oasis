# -*- coding: utf-8 -*-
from datetime import datetime
from PyQt6.QtCore import Qt

# 산출일위표 패널 호출에서 제외할 특수 산출목록 텍스트 목록
EXCLUDED_ITEM_TEXTS = [
    "전등수량(갯수)산출",
    "조명기구 Type산출",
    "분전반 산출",
]

class CalculationUnitPriceTrigger:
    """산출일위표 팝업 자동 트리거 관리
    
    산출목록(ITEM) 또는 산출수식(FORMULA) 컬럼 클릭 시 산출일위표 패널을 표시.
    단, EXCLUDED_ITEM_TEXTS에 해당하는 산출목록 텍스트가 있는 행은 제외.
    """
    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        self.popup = None
        self._is_handling = False  # 재진입 방지 가드
        # 절대 경로 로그 파일 설정
        import os
        self.debug_log = os.path.join(self.parent_tab.project_root, "debug_trigger.log")

    def handle_cell_selection(self, row, col):
        """특정 셀 선택 시 팝업 제어
        
        산출목록(ITEM) 또는 산출수식(FORMULA) 컬럼을 클릭하면 산출일위표 패널 표시.
        단, 해당 행의 산출목록 텍스트가 EXCLUDED_ITEM_TEXTS에 해당하면 표시하지 않음.
        """
        # 재진입 방지
        if self._is_handling:
            return
        self._is_handling = True
        
        try:
            item_col = self.parent_tab.EULJI_COLS["ITEM"]
            formula_col = self.parent_tab.EULJI_COLS["FORMULA"]
            
            # [DEBUG] 로그 파일에 기록
            try:
                with open(self.debug_log, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] Trigger: row={row}, col={col}, item_col={item_col}, formula_col={formula_col}\n")
            except: pass
            
            # 산출목록(ITEM) 컬럼인 경우에만 산출일위표 표시
            if col == item_col:
                # 해당 행의 산출목록 텍스트 확인 (제외 대상 필터링)
                item_text = ""
                if hasattr(self.parent_tab, "eulji_table"):
                    item = self.parent_tab.eulji_table.item(row, item_col)
                    if item:
                        item_text = item.text().strip()
                
                # 제외 대상인 경우 산출일위표 표시하지 않음
                if item_text in EXCLUDED_ITEM_TEXTS:
                    try:
                        with open(self.debug_log, "a", encoding="utf-8") as f:
                            f.write(f"[{datetime.now()}] Excluded item '{item_text}' - skipping popup\n")
                    except: pass
                    # 팝업이 표시 중이면 숨김
                    if self.popup and not self.popup.isHidden():
                        self.popup.hide_popup()
                    return
                
                # 팝업 인스턴스 생성 (최초 1회)
                if not self.popup:
                    try:
                        with open(self.debug_log, "a", encoding="utf-8") as f:
                            f.write(f"[{datetime.now()}] Creating new CalculationUnitPricePopup instance...\n")
                    except: pass
                    # 모듈화된 경로에서 임포트
                    from popups.calculation_unit_price_popup import CalculationUnitPricePopup
                    self.popup = CalculationUnitPricePopup(self.parent_tab.main_window)
                    
                # prepare_show는 항상 ITEM 컬럼 기준으로 호출
                self.popup.prepare_show(self.parent_tab, row, item_col)
                self.popup.show_popup()
                
                try:
                    with open(self.debug_log, "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now()}] Popup show requested for row {row} (clicked col={col})\n")
                except: pass
            else:
                # '산출목록' 외 컬럼 클릭 시 자동으로 팝업 숨기기
                if self.popup and not self.popup.isHidden():
                    self.popup.hide_popup()
                    try:
                        with open(self.debug_log, "a", encoding="utf-8") as f:
                            f.write(f"[{datetime.now()}] Popup hidden - focused on other column (col={col})\n")
                    except: pass
        except Exception as e:
            import traceback
            error_msg = f"[ERROR] handle_cell_selection failed: {e}\n{traceback.format_exc()}"
            try:
                with open(self.debug_log, "a", encoding="utf-8") as f:
                    f.write(error_msg + "\n")
            except: pass
            print(error_msg)
        finally:
            self._is_handling = False
