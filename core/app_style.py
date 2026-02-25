# -*- coding: utf-8 -*-
"""
Application Styling Module
==========================
Handles font registration and global stylesheet generation.
Part of the modular architecture.
"""

import os
from PyQt6.QtGui import QFontDatabase


def register_fonts(current_dir):
    """
    Register Google Sans Flex font if available, else return fallback.

    Args:
        current_dir (str): The root execution directory where assets are located.

    Returns:
        str: The name of the font family to use.
    """
    # 1순위: 새굴림 (gulim.ttc 내에 포함됨)
    font_path_gulim = os.path.join(current_dir, "assets", "fonts", "gulim.ttc")
    if os.path.exists(font_path_gulim):
        font_id = QFontDatabase.addApplicationFont(font_path_gulim)
        if font_id != -1:
            try:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    # '새굴림'을 최우선 검색
                    for f in families:
                        if "SaeGulim" in f or "새굴림" in f:
                            print(f"[DEBUG] Global Font (SaeGulim) Registered: {f}")
                            return f
                    # 없으면 굴림체 검색
                    for f in families:
                        if "GulimChe" in f or "굴림체" in f:
                            print(f"[DEBUG] Fallback Global Font (GulimChe) Registered: {f}")
                            return f
                    
                    # 없으면 첫 번째 리턴
                    print(f"[DEBUG] Global Font Registered: {families[0]}")
                    return families[0]
            except Exception as e:
                 print(f"[WARNING] Failed to load font families from {font_path_gulim}: {e}")

    # 2순위: Google Sans Flex (기존 로직 유지)
    font_path = os.path.join(current_dir, "assets", "fonts", "GoogleSansFlex.ttf")
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            family = QFontDatabase.applicationFontFamilies(font_id)[0]
            print(f"[DEBUG] Global Font Registered: {family}")
            return family
            
    print("[WARNING] Font file not found. Using system default '새굴림'.")
    return "새굴림"


def get_main_stylesheet(global_font):
    """
    Returns the global QSS stylesheet with the specified font inserted.

    Args:
        global_font (str): The font family name to use.
    """
    return f"""
            /* 전역 폰트 및 기본 스타일 */
            * {{ 
                font-family: '{global_font}'; 
                font-size: 10pt; 
                font-weight: normal;
            }}

            QTableView::item, QTableWidget::item {{
                padding: 0px;
                margin: 0px;
                border: none;
            }}
            
            /* [헤더] 평면 스타일 - 메뉴/헤더는 사용자의 요청으로 굴림체 제외 (굴림 적용) */
            QHeaderView::section {{
                background-color: #e1e1e1;
                color: black;
                padding: 3px;
                border: 1px solid #707070;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-bottom: 2px solid #606060;
                border-right: 2px solid #606060;
                font-family: '새굴림', '{global_font}';
                font-weight: normal;
                text-align: center;
            }}
            QTableCornerButton::section {{
                background-color: #f0f0f0;
                border: 1px solid #ccc;
            }}
            
            /* [탭] 평면 스타일 */
            QTabWidget::pane {{
                border: 1px solid #ccc;
                top: -1px;
                background-color: white;
            }}
            QTabBar::tab {{
                background: #f1f3f5;
                border: 1px solid #adb5bd;
                border-bottom: none;
                padding: 2px 12px;
                margin-right: 4px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                color: #495057;
                font-family: '{global_font}';
            }}
            QTabBar::tab:selected {{
                background: white;
                border: 1px solid #868e96;
                border-bottom: 3px solid #333333;
                color: #333333;
                font-weight: normal;
                padding-bottom: 5px;
            }}
            QTabBar::tab:hover {{
                background: #e9ecef;
                color: #212529;
            }}
            
            /* [버튼] 평면 스타일 */
            QPushButton {{
                background-color: #f8f8f8;
                border: 1px solid #bbb;
                padding: 2px 12px;
                border-radius: 0px;
                font-family: '{global_font}';
                font-weight: normal;
            }}
            QPushButton:hover {{
                background-color: #e8e8e8;
                border: 1px solid #999;
            }}
            QPushButton:pressed {{
                background-color: #ddd;
                border: 1px solid #888;
            }}
            
            /* [입력창] 평면 스타일 */
            QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox {{
                border: 1px solid #ccc;
                background-color: white;
                border-radius: 0px;
                padding: 2px;
                padding-left: 0px;
                font-family: '{global_font}';
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 1px solid #333333;
            }}
            
            /* [테이블] 그리드 및 배경 */
            QTableView {{
                gridline-color: #999999;
                background-color: white;
                selection-background-color: transparent;
                selection-color: inherit;
                outline: none;
                font-family: '{global_font}';
            }}
            
            /* [메뉴] 평면 스타일 - 메뉴도 굴림체 제외 (굴림 적용) */
            QMenuBar {{
                background-color: #f5f5f5;
                border-bottom: 1px solid #ccc;
                font-family: '새굴림', '{global_font}';
            }}
            QMenuBar::item {{
                background: transparent;
                padding: 4px 10px;
            }}
            QMenuBar::item:selected {{
                background: #e0e0e0;
            }}
            QMenu {{
                background-color: white;
                border: 1px solid #ccc;
                font-family: '새굴림', '{global_font}';
            }}
            QMenu::item {{
                padding: 4px 20px;
            }}
            QMenu::item:selected {{
                background-color: #f0f0f0;
            }}
        """
