import sys
import traceback

print("1. Start testing imports...")
try:
    print("2. Importing PyQt6...")
    from PyQt6.QtWidgets import QApplication
    print("   Success.")
except ImportError:
    print("   Failed.")
    traceback.print_exc()

try:
    print("3. Importing lighting_power_manager...")
    import lighting_power_manager
    print("   Success.")
except Exception:
    print("   Failed.")
    traceback.print_exc()

try:
    print("4. Importing output_detail_tab...")
    import output_detail_tab
    print("   Success.")
except Exception:
    print("   Failed.")
    traceback.print_exc()

print("5. All tests finished.")
