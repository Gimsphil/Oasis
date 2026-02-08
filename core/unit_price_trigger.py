# -*- coding: utf-8 -*-
from datetime import datetime
from PyQt6.QtCore import Qt

class CalculationUnitPriceTrigger:
    """산출일위표 팝업 자동 트리거 관리"""
    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        self.popup = None
        # 절대 경로 로그 파일 설정
        import os
        self.debug_log = os.path.join(self.parent_tab.project_root, "debug_trigger.log")

    def handle_cell_selection(self, row, col):
        """특정 셀 선택 시 팝업 제어"""
        try:
            target_col = self.parent_tab.EULJI_COLS["ITEM"]
            
            # [DEBUG] 로그 파일에 기록
            try:
                with open(self.debug_log, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] Trigger: row={row}, col={col}, target={target_col}\n")
            except: pass
            
            if col == target_col:
                if not self.popup:
                    try:
                        with open(self.debug_log, "a", encoding="utf-8") as f:
                            f.write(f"[{datetime.now()}] Creating new CalculationUnitPricePopup instance...\n")
                    except: pass
                    # 모듈화된 경로에서 임포트
                    from popups.calculation_unit_price_popup import CalculationUnitPricePopup
                    self.popup = CalculationUnitPricePopup(self.parent_tab.main_window)
                    
                self.popup.prepare_show(self.parent_tab, row, col)
                self.popup.show_popup()
                
                try:
                    with open(self.debug_log, "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now()}] Popup show requested for row {row}\n")
                except: pass
            else:
                if self.popup and not self.popup.isHidden():
                    self.popup.hide_popup()
                    try:
                        with open(self.debug_log, "a", encoding="utf-8") as f:
                            f.write(f"[{datetime.now()}] Popup hidden - focused on other column\n")
                    except: pass
        except Exception as e:
            import traceback
            error_msg = f"[ERROR] handle_cell_selection failed: {e}\n{traceback.format_exc()}"
            try:
                with open(self.debug_log, "a", encoding="utf-8") as f:
                    f.write(error_msg + "\n")
            except: pass
            print(error_msg)
