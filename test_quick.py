#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
빠른 진단 스크립트
"""

import sys
import os
import traceback

print("=" * 60)
print("🔍 QUICK DIAGNOSTIC TEST")
print("=" * 60)

# 1. Python 버전
print(f"\n1️⃣  Python Version: {sys.version}")
print(f"   Executable: {sys.executable}")

# 2. 경로
current_dir = os.path.dirname(os.path.abspath(__file__))
print(f"\n2️⃣  Current Dir: {current_dir}")
print(f"   Working Dir: {os.getcwd()}")

# 3. PyQt6 임포트 테스트
print(f"\n3️⃣  PyQt6 Import Test:")
try:
    from PyQt6.QtWidgets import QApplication, QMainWindow
    print("   ✅ PyQt6.QtWidgets: OK")
except Exception as e:
    print(f"   ❌ PyQt6.QtWidgets FAILED: {e}")

try:
    from PyQt6.QtCore import Qt, QMimeData
    print("   ✅ PyQt6.QtCore (Qt, QMimeData): OK")
except Exception as e:
    print(f"   ❌ PyQt6.QtCore FAILED: {e}")

try:
    from PyQt6.QtGui import QFont, QColor
    print("   ✅ PyQt6.QtGui (QFont, QColor): OK")
except Exception as e:
    print(f"   ❌ PyQt6.QtGui FAILED: {e}")

# 4. 커스텀 모듈 임포트 테스트
print(f"\n4️⃣  Custom Modules Import Test:")

sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, "core"))
sys.path.insert(0, os.path.join(current_dir, "utils"))
sys.path.insert(0, os.path.join(current_dir, "ui"))
sys.path.insert(0, os.path.join(current_dir, "managers"))
sys.path.insert(0, os.path.join(current_dir, "popups"))

try:
    import app_style
    print(f"   ✅ app_style: OK ({app_style.__file__})")
except Exception as e:
    print(f"   ❌ app_style FAILED: {e}")
    traceback.print_exc()

try:
    from output_detail_tab import OutputDetailTab
    print("   ✅ OutputDetailTab: OK")
except Exception as e:
    print(f"   ❌ OutputDetailTab FAILED: {e}")
    traceback.print_exc()

# 5. 최종 메시지
print(f"\n" + "=" * 60)
print("✅ All tests completed!")
print("=" * 60)
