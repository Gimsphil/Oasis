#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

# 1단계: 기본 임포트
try:
    from PyQt6.QtWidgets import QApplication
    print("OK: PyQt6")
except Exception as e:
    print(f"FAIL: PyQt6 - {e}")
    sys.exit(1)

# 2단계: 스타일 임포트
try:
    from app_style import register_fonts
    print("OK: app_style")
except Exception as e:
    print(f"FAIL: app_style - {e}")
    sys.exit(1)

# 3단계: lightning_power_manager 임포트
try:
    from lighting_power_manager import LightingPowerManager
    print("OK: lighting_power_manager")
except Exception as e:
    print(f"FAIL: lighting_power_manager - {e}")
    sys.exit(1)

# 4단계: output_detail_tab 임포트
try:
    from output_detail_tab import OutputDetailTab
    print("OK: output_detail_tab")
except Exception as e:
    print(f"FAIL: output_detail_tab - {e}")
    sys.exit(1)

print("\nAll imports successful! Starting GUI...")
sys.exit(0)
