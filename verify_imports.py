# -*- coding: utf-8 -*-
import sys
import os
from PyQt6.QtWidgets import QApplication

# Mock QApplication for instantiation
app = QApplication(sys.argv)

try:
    print("Testing popups.calculation_unit_price_popup.CalculationUnitPricePopup...")
    from popups.calculation_unit_price_popup import CalculationUnitPricePopup
    # popup = CalculationUnitPricePopup() # This might need more setup (parent etc)
    print("Import successful.")
except Exception as e:
    print(f"Failed: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\nTesting ui.unit_price_panel.UnitPricePanel...")
    from ui.unit_price_panel import UnitPricePanel
    # panel = UnitPricePanel()
    print("Import successful.")
except Exception as e:
    print(f"Failed: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\nTesting lighting_power_manager.LightingPowerPopup...")
    from lighting_power_manager import LightingPowerPopup
    print("Import successful.")
except Exception as e:
    print(f"Failed: {e}")
    import traceback
    traceback.print_exc()

print("\nVerification finished.")
sys.exit(0)
