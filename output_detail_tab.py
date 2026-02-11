# -*- coding: utf-8 -*-
"""
산출내역 탭 - 독립 실행 버전
Output Detail Tab (Standalone)
갑지(총괄표)와 을지(상세산출)를 포함한 산출내역 관리
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QStackedWidget,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QFrame,
    QSizePolicy,
    QDialog,
    QTreeWidget,
    QTreeWidgetItem as QTreeItem,
    QGridLayout,
    QMessageBox,
    QFileDialog,
    QLineEdit,
    QHeaderView,
    QComboBox,
    QAbstractItemView,
    QMainWindow,
)
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QFontDatabase
from PyQt6.QtCore import Qt, QObject, QEvent, QTimer
from datetime import datetime
import re
import os
import sqlite3
import sys


# 내부 모듈 임포트
from utils.column_settings import (
    COMMON_COLUMNS,
    COLUMN_WIDTHS,
    NUMERIC_COLUMNS,
    EULJI_COLUMNS,
    EULJI_COLUMN_WIDTHS,
    setup_common_table,
    setup_eulji_table,
    format_number,
    parse_number,
    auto_expand_rows,
)
from utils.grid_clipboard import setup_clipboard_handler
# from lighting_power_manager import LightingPowerManager # Removed to prevent circular import, imported locally in __init__

from ui.eulji_table import EuljiTableWidget
from ui.gapji_table import GapjiTableWidget
from ui.side_panel import GongjongListPanel
from ui.eulji_menu import EuljiCategoryMenu
from core.unit_price_trigger import CalculationUnitPriceTrigger
from managers.event_filter import TableEventFilter

# [DEBUG] Module-level log to confirm import
try:
    with open("tab_debug.log", "a", encoding="utf-8") as _f:
        import datetime as _dt

        _f.write(
            f"[{_dt.datetime.now().strftime('%H:%M:%S')}] output_detail_tab.py module loaded with new modular structure\n"
        )
except:
    pass


class OutputDetailTab:
    """산출내역 탭 - 갑지(총괄표)와 을지(상세산출) 통합"""

    # 갑지 컬럼 인덱스
    NUM_COL = 0
    GUBUN_COL = 1
    GONGJONG_NUM_COL = 2
    GONGJONG_COL = 3
    UNIT_COL = 4
    HEIGHT_COL = 5
    CEILING_COL = 6
    QTY_COL = 7
    REMARK_COL = 8

    # 을지 컬럼 정의
    EULJI_COLS = {
        "NUM": 0,
        "GUBUN": 1,
        "FROM": 2,
        "TO": 3,
        "CIRCUIT": 4,
        "ITEM": 5,
        "FORMULA": 6,
        "TOTAL": 7,
        "UNIT": 8,
        "REMARK": 9,
    }
    EULJI_COL_NAMES = [
        "#.",
        "구분",
        "FROM",
        "TO",
        "회로",
        "산출목록",
        "산출수식",
        "계",
        "단위",
        "비고",
    ]
    EULJI_COL_WIDTHS = [28, 84, 60, 60, 72, 400, 432, 50, 50, 75]

    GONGJONG_FILENAME = "공종명입력.txt"

    def __init__(self, parent_window):
        self.main_window = parent_window
        self.stacked_widget = None
        self.gapji_table = None
        self.eulji_table = None
        self.eulji_splitter = None
        self.event_filter = None

        # 엑셀 시트 스타일
        self.sheet_active_style = """
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #999999;
                border-bottom: none;
                color: #000000;
                font-weight: bold;
                padding: 5px 20px;
                font-family: '새굴림';
                font-size: 11pt;
                margin-top: 2px;
            }
        """
        self.sheet_inactive_style = """
            QPushButton {
                background-color: #e1e1e1;
                border: 1px solid #999999;
                color: #666666;
                padding: 5px 20px;
                font-family: '새굴림';
                font-size: 11pt;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """

        self.current_gongjong = ""
        self.current_row = -1

        # UI 요소
        self.gongjong_list = None
        self.gongjong_items = []
        self.gongjong_category = "전기"

        # 파일 경로 계산
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = base_dir

        # [NEW] 자료사전 DB 경로 설정
        self.ref_db_path = r"D:\오아시스\data\자료사전.db"

        # 공종 폴더 경로
        self.gongjong_folder_path = os.path.join(self.project_root, "gongjong")
        self.gongjong_file_path = os.path.join(
            self.gongjong_folder_path, self.GONGJONG_FILENAME
        )

        # 데이터 저장소
        self.eulji_data = {}
        self.eulji_results = {}
        self.eulji_row_details = {}

        # 실행 취소(Undo) 스택
        self.undo_stack = []

        # [Phase 1-3] 클립보드 (Ctrl+C/V/X용)
        self._clipboard = None

        # [NEW] 산출일위표 트리거 초기화
        self.unit_price_trigger = CalculationUnitPriceTrigger(self)

        # [NEW] 지연 저장용 타이머 (성능 최적화)
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._on_save_timer_timeout)

        # [NEW] 팝업 인스턴스 캐싱
        self.reference_popup = None

        # 전등/전열 매니저 초기화 (create_tab 이전에 수행해야 패널 등록 가능)
        from lighting_power_manager import LightingPowerManager

        self.lighting_manager = LightingPowerManager(self)

        # [NEW] 미저장 데이터 초기화 (사용자 요청: 새로 프로그램을 시작하면 행당 데이터 초기화)
        self._cleanup_unsaved_chunks()

        print(
            f"[DEBUG] OutputDetailTab Init. Path exists: {os.path.exists(self.gongjong_file_path)}"
        )
        self._log_system_event(
            "Application initialized with Unit Price Sync and Data Dict special commands."
        )

    def _cleanup_unsaved_chunks(self):
        """미저장(Unsaved) 세션의 일위표 데이터 초기화"""
        try:
            import shutil

            root_path = os.path.dirname(os.path.abspath(__file__))
            unsaved_dir = os.path.join(
                root_path, "data", "unit_price_chunks", "_unsaved_session_"
            )
            if os.path.exists(unsaved_dir):
                print(f"[DEBUG] Cleaning up unsaved chunks: {unsaved_dir}")
                shutil.rmtree(unsaved_dir)
                os.makedirs(unsaved_dir, exist_ok=True)
        except Exception as e:
            print(f"[WARN] Failed to cleanup unsaved chunks: {e}")

    def reset_internal_data(self):
        """새로운 공종(시트) 로드 시 내부 데이터 초기화"""
        print(f"[DEBUG] OutputDetailTab: Resetting internal data...")
        self.eulji_data = {}
        self.eulji_results = {}
        self.eulji_row_details = {}
        self.current_row = -1
        self.current_gongjong = ""
        self.undo_stack = []
        # [NEW] 산출일위표 트리거 초기화
        self.unit_price_trigger = CalculationUnitPriceTrigger(self)

    def load_basic_work_template(self):
        """[Phase 2-4] 기초작업 템플릿 로드"""
        import json

        template_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data",
            "templates",
            "basic_work.json",
        )

        if not os.path.exists(template_path):
            print(f"[WARN] 기초작업 템플릿 없음: {template_path}")
            return

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template = json.load(f)

            # 갑지 기본값 설정
            if "gapji_defaults" in template:
                defaults = template["gapji_defaults"]
                # TODO: 갑지 테이블의 $H, $L 컬럼에 기본값 설정

            # 을지 데이터 로드
            if "eulji_items" in template:
                for item in template["eulji_items"]:
                    gongjong = template.get("gongjong", "000. 기초작업")
                    if gongjong not in self.eulji_data:
                        self.eulji_data[gongjong] = []

                    # 행 데이터 구성
                    row_data = {
                        "num": item.get("num", ""),
                        "gubun": item.get("gubun", ""),
                        "from": item.get("from", ""),
                        "to": item.get("to", ""),
                        "circuit": item.get("circuit", ""),
                        "item": item.get("item", ""),
                        "formula": item.get("formula", ""),
                        "total": item.get("total", ""),
                        "unit": item.get("unit", ""),
                        "remark": item.get("remark", ""),
                    }
                    self.eulji_data[gongjong].append(row_data)

                    # 일위대가 데이터 저장
                    if item.get("unit_price", {}).get("enabled", False):
                        unit_items = item.get("unit_price", {}).get("items", [])
                        row_idx = len(self.eulji_data[gongjong]) - 1
                        chunk_file = os.path.join(
                            "data", "unit_price_chunks", f"{gongjong}_{row_idx}.json"
                        )
                        # JSON 파일로 저장 (단위계 계산 포함)
                        self._save_unit_price_chunk(chunk_file, unit_items)

            print(
                f"[INFO] 기초작업 템플릿 로드 완료: {len(template.get('eulji_items', []))}개 항목"
            )

        except Exception as e:
            print(f"[ERROR] 기초작업 템플릿 로드 실패: {e}")

    def _save_unit_price_chunk(self, file_path: str, items: list):
        """일위대가 데이터를 JSON 파일로 저장"""
        import json

        try:
            # 단위계 계산
            total = 0.0
            calculated_items = []
            for item in items:
                qty_str = item.get("qty", "0")
                try:
                    from utils.formula_parser import parse_formula

                    qty = parse_formula(qty_str)
                except:
                    qty = 0.0
                total += qty
                calculated_items.append(
                    {
                        "name": item.get("name", ""),
                        "qty": qty_str,
                        "unit_total": qty,
                    }
                )

            data = {
                "items": calculated_items,
                "total": total,
            }

            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"[WARN] 일위대가 저장 실패: {file_path} - {e}")

    def record_undo(self, table, action, row_index, data=None):
        """작업 기록 (Undo용)"""
        self.undo_stack.append(
            {"table": table, "action": action, "row": row_index, "data": data}
        )
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)

    def undo(self):
        """마지막 작업 취소"""
        if not self.undo_stack:
            return

        record = self.undo_stack.pop()
        table = record["table"]
        action = record["action"]
        row = record["row"]
        data = record["data"]

        table.blockSignals(True)
        try:
            if action == "insert":
                if row < table.rowCount():
                    table.removeRow(row)
            elif action == "delete":
                table.insertRow(row)
                if data:
                    for col, text in enumerate(data):
                        table.setItem(row, col, QTableWidgetItem(text))

            table.setCurrentCell(
                row, table.currentColumn() if table.currentColumn() >= 0 else 0
            )
        finally:
            table.blockSignals(False)

        if hasattr(self.main_window, "statusBar"):
            self.main_window.statusBar().showMessage("실행 취소되었습니다.", 2000)

    def create_tab(self):
        """탭 위젯 생성 및 반환"""
        self.main_container = QWidget()
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. 상단 정보 바
        self.header_frame = QFrame()
        self.header_frame.setFixedHeight(75)  # 메뉴(26) + 툴바(45) + 여유
        self.header_frame.setStyleSheet(
            "background-color: #f8f9fa; border-bottom: 2px solid #dee2e6;"
        )
        # 상단 통합 레이아웃 (QVBoxLayout)
        header_main_layout = QVBoxLayout(self.header_frame)
        header_main_layout.setContentsMargins(10, 3, 10, 3)
        header_main_layout.setSpacing(2)

        # 0행: 일반 메뉴
        menu_area = QWidget()
        menu_area.setFixedHeight(24)  # 메뉴 행 높이
        menu_layout = QHBoxLayout(menu_area)
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_layout.setSpacing(8)

        menu_btn_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                color: #333;
                font-family: '새굴림';
                font-size: 11pt;
                padding: 2px 5px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-radius: 2px;
            }
        """

        for menu_name, shortcut_key, callback_name in [
            ("파일(F)", "F", None),
            ("편집(E)", "E", None),
            ("보기(V)", "V", None),
            ("도구(T)", "T", None),
            ("모듈(M)", "M", "_show_modules_menu"),
            ("시스템로그(L)", "L", "_show_system_log"),
            ("도움말(H)", "H", "_show_about_dialog"),
        ]:
            btn = QPushButton(menu_name)
            btn.setStyleSheet(menu_btn_style)
            if callback_name and hasattr(self, callback_name):
                btn.clicked.connect(getattr(self, callback_name))
            menu_layout.addWidget(btn)

        menu_layout.addStretch()
        header_main_layout.addWidget(menu_area)

        # 0-1행: 모듈 툴바 (새로 추가)
        toolbar_area = QWidget()
        toolbar_area.setFixedHeight(42)  # 툴바 높이 증가
        toolbar_area.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar_area)
        toolbar_layout.setContentsMargins(3, 1, 3, 1)
        toolbar_layout.setSpacing(3)

        # 툴바 버튼 스타일 (더 컴팩트하게)
        toolbar_btn_style = """
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #ced4da;
                border-radius: 3px;
                padding: 2px 6px;
                font-family: '새굴림';
                font-size: 9pt;
                min-width: 68px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """

        # Phase별 툴바 버튼 구성
        toolbar_buttons = [
            # Phase 3: 집계/관리
            ("소요자재", "material_summary", "material_summary_popup"),
            ("일괄변경", "batch_tools", "batch_tools_popup"),
            None,  # 구분선
            # Phase 4: 출력/변환
            ("견적변환", "estimate_convert", "estimate_options_popup"),
            ("엑셀출력", "excel_export", "excel_exporter"),
            ("산식검사", "formula_check", "formula_check_popup"),
            None,  # 구분선
            # Phase 5: 고급 기능
            ("산출판", "output_board", "output_board_popup"),
            ("간선산출", "cable_routing", "cable_routing_popup"),
            ("설계변경", "design_change", "design_change_popup"),
            None,  # 구분선
            # Phase 6: 전문 기능
            ("그림산출", "graphic_output", "graphic_output_popup"),
            ("CAD연동", "cad_integration", "cad_integration"),
        ]

        for item in toolbar_buttons:
            if item is None:
                # 구분선
                separator = QFrame()
                separator.setFrameShape(QFrame.Shape.VLine)
                separator.setFrameShadow(QFrame.Shadow.Sunken)
                separator.setStyleSheet("color: #ced4da;")
                toolbar_layout.addWidget(separator)
            else:
                btn_label, btn_name, module_name = item
                btn = QPushButton(btn_label)
                btn.setStyleSheet(toolbar_btn_style)
                btn.setToolTip(f"{btn_label} 모듈 실행")
                # 클릭 이벤트 연결
                btn.clicked.connect(
                    lambda checked, n=btn_name: self._on_toolbar_clicked(n)
                )
                toolbar_layout.addWidget(btn)

        toolbar_layout.addStretch()
        header_main_layout.addWidget(toolbar_area)

        # 1행: 현장명 (Project) + 우측에 공종 카테고리
        project_row_widget = QWidget()
        project_row_widget.setFixedHeight(26)  # 프로젝트 행 높이 고정
        project_row_layout = QHBoxLayout(project_row_widget)
        project_row_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_project_name = QLabel("Project: -")
        self.lbl_project_name.setStyleSheet(
            "font-weight: bold; color: #333; font-size: 11pt; font-family: '새굴림';"
        )
        project_row_layout.addWidget(self.lbl_project_name)

        project_row_layout.addSpacing(20)

        # 산출공종 라벨을 프로젝트명 행으로 이동 (사용자 요청)
        self.current_gongjong_label = QLabel("산출공종: -")
        self.current_gongjong_label.setStyleSheet(
            "color: #666; font-size: 11pt; font-family: '새굴림';"
        )
        project_row_layout.addWidget(self.current_gongjong_label)

        project_row_layout.addStretch()

        # 공종 카테고리 콤보박스 (우측 이동)
        self.gongjong_category_combo = QComboBox()
        self.gongjong_category_combo.setStyleSheet("font-family: '새굴림';")
        self.gongjong_category_combo.setFixedWidth(120)
        self.gongjong_category_combo.setFixedWidth(120)
        self.gongjong_category_combo.addItems(["공통", "전기", "설비", "건축"])
        self.gongjong_category_combo.setCurrentText("전기")  # 기본값 전기 설정
        self.gongjong_category_combo.currentTextChanged.connect(
            self._on_category_changed
        )
        project_row_layout.addWidget(self.gongjong_category_combo)

        header_main_layout.addWidget(project_row_widget)

        # 2행: 을지 전용 카테고리 메뉴 - 산출공종이 1행으로 이동하면서 한 칸 위로 배치 (사용자 요청)
        self.eulji_category_menu_widget = EuljiCategoryMenu(self)
        self.eulji_category_menu_widget.hide()
        header_main_layout.addWidget(self.eulji_category_menu_widget)

        main_layout.addWidget(self.header_frame)

        # 2. 시트 탭 (상단으로 이동)
        self.tab_frame = QFrame()
        self.tab_frame.setFixedHeight(35)
        self.tab_frame.setStyleSheet("""
            QFrame {
                background-color: #efefef;
                border-bottom: 1px solid #999999;
            }
        """)
        tab_layout = QHBoxLayout(self.tab_frame)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        # 시트 컨트롤 (좌측 화살표)
        scroll_controls = QLabel(" ◀ ◀ ▷ ▷ ")
        scroll_controls.setStyleSheet("color: #666; font-size: 12pt; padding: 0 10px;")
        tab_layout.addWidget(scroll_controls)

        # 실제 시트 버튼
        self.btn_gapji = QPushButton("산출총괄표")
        self.btn_gapji.setStyleSheet(self.sheet_active_style)
        self.btn_gapji.clicked.connect(lambda: self._switch_view(0))
        tab_layout.addWidget(self.btn_gapji)

        self.btn_eulji = QPushButton("산출내역서")
        self.btn_eulji.setStyleSheet(self.sheet_inactive_style)
        self.btn_eulji.clicked.connect(lambda: self._switch_view(1))
        tab_layout.addWidget(self.btn_eulji)

        tab_layout.addStretch()

        main_layout.addWidget(self.tab_frame)

        # 3. 스택 위젯 (중앙)
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # --- [갑지 화면] ---
        self.gapji_widget = QWidget()
        gapji_layout = QVBoxLayout(self.gapji_widget)  # 메인 레이아웃은 VBox로 변경
        gapji_layout.setContentsMargins(0, 0, 0, 0)
        gapji_layout.setSpacing(0)

        # [NEW] 갑지용 스플리터 도입 (경계 구분 명확화 및 리사이징 지원)
        self.gapji_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.gapji_splitter.setHandleWidth(8)  # 핸들 폭 확대 (사용자 요청)
        self.gapji_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #dee2e6;
                border: 1px solid #ced4da;
            }
            QSplitter::handle:hover {
                background-color: #adb5bd;
            }
        """)

        # 중앙: 갑지 테이블
        self.gapji_table = GapjiTableWidget(self)
        # 2행 공종순서 칸에 '번호정리' 버튼 배치 (사용자 요청)
        self.gapji_table.set_reorder_button(
            1, self.GONGJONG_NUM_COL, self._create_reorder_button()
        )
        self.gapji_splitter.addWidget(self.gapji_table)

        # 우측: 공종 리스트 패널
        self.side_panel_widget = GongjongListPanel(self)
        self.gongjong_list = self.side_panel_widget.list_widget  # 하위 호환성 유지
        self.gapji_splitter.addWidget(self.side_panel_widget)

        # 초기 비율 설정 (전체 창 크기에 맞게 8:2 배분)
        self.gapji_splitter.setSizes([1150, 250])

        gapji_layout.addWidget(self.gapji_splitter)

        self.stacked_widget.addWidget(self.gapji_widget)

        # --- [을지 화면] ---
        self.eulji_widget = QWidget()
        eulji_main_layout = QVBoxLayout(self.eulji_widget)
        eulji_main_layout.setContentsMargins(0, 0, 0, 0)
        eulji_main_layout.setSpacing(0)

        # 스플리터
        self.eulji_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.eulji_splitter.setHandleWidth(8)  # 핸들 폭 확대 (Gapji와 통일)
        self.eulji_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #dee2e6;
                border: 1px solid #ced4da;
            }
            QSplitter::handle:hover {
                background-color: #adb5bd;
            }
        """)

        # 을지 테이블 - Tab 키로 자료사전 팝업 호출을 위해 커스텀 위젯 사용
        self.eulji_table = EuljiTableWidget(self)
        setup_eulji_table(self.eulji_table)
        # [FORCE] 산출목록(ITEM) 컬럼 너비를 400px로 강제 설정 (사용자 요청 1/2 축소 반영)
        self.eulji_table.setColumnWidth(self.EULJI_COLS["ITEM"], 400)

        self.eulji_table.cellChanged.connect(self.on_eulji_cell_changed)
        self.eulji_table.cellClicked.connect(self.on_eulji_cell_clicked)
        self.eulji_table.cellPressed.connect(
            self.on_eulji_cell_clicked
        )  # [NEW] 누름 이벤트에도 연결하여 반응성 향상

        # [NEW] 키보드 이동 대응: 선택 영역 변경 시 팝업 연동
        self.eulji_table.selectionModel().selectionChanged.connect(
            self._on_eulji_selection_changed
        )
        # [NEW] 더블 클릭 연결
        self.eulji_table.cellDoubleClicked.connect(self._on_eulji_double_clicked)
        self.eulji_splitter.addWidget(self.eulji_table)

        # 전등/전열 산출공종 우측 패널 추가
        if hasattr(self, "lighting_manager"):
            self.eulji_splitter.addWidget(self.lighting_manager.create_side_panel())
        # 우측 산출공종 패널 삭제 (사용자 요청)
        # self._create_output_gongjong_panel(self.eulji_splitter)

        eulji_main_layout.addWidget(self.eulji_splitter)
        self.stacked_widget.addWidget(self.eulji_widget)

        # 갑지 테이블도 Tab 이동 차단
        # self.gapji_table.setTabKeyNavigation(False) # [FIX] 존재하지 않는 메서드 제거

        # 이벤트 필터 설치
        self.event_filter = TableEventFilter(self)
        self.gapji_table.installEventFilter(self.event_filter)
        self.eulji_table.installEventFilter(self.event_filter)

        # 초기화
        self._safe_load_gongjong()

        return self.main_container

    def _switch_view(self, index):
        """갑지/을지 화면 전환 (엑셀 시트 스타일)"""
        # 을지에서 갑지로 전환 시 현재 데이터 저장 및 마커 업데이트
        if self.stacked_widget.currentIndex() == 1 and index == 0:
            if hasattr(self, "current_gongjong") and self.current_gongjong:
                self._save_eulji_data(self.current_gongjong)
                self._update_gapji_marker(self.current_gongjong)

        self.stacked_widget.setCurrentIndex(index)
        if index == 0:
            self.btn_gapji.setStyleSheet(self.sheet_active_style)
            self.btn_eulji.setStyleSheet(self.sheet_inactive_style)
            # 갑지: 공종 카테고리 메뉴 표시, 을지 메뉴 숨김
            self.gongjong_category_combo.show()
            self.eulji_category_menu_widget.hide()
            self.header_frame.setFixedHeight(95)  # 갑지: 메뉴+툴바+프로젝트 행
        else:
            self.btn_gapji.setStyleSheet(self.sheet_inactive_style)
            self.btn_eulji.setStyleSheet(self.sheet_active_style)
            # 을지: 공종 카테고리 메뉴 숨김, 을지 메뉴 표시
            self.gongjong_category_combo.hide()
            self.eulji_category_menu_widget.show()
            self.header_frame.setFixedHeight(125)  # 을지: 메뉴+툴바+프로젝트+을지메뉴

    def _on_lighting_power_clicked(self):
        """전등/전열 버튼 클릭 시 호출"""
        print("[DEBUG] Lighting/Power button clicked")
        if hasattr(self, "lighting_manager"):
            self.lighting_manager.toggle_panel()

    def _on_eulji_category_clicked(self, category):
        """을지 상단 카테고리 버튼 클릭 핸들러"""
        print(f"[DEBUG] Eulji category clicked: {category}")
        if category == "전등/전열":
            self._on_lighting_power_clicked()
        else:
            # 다른 카테고리에 대한 공종 리스트 로드 (필요시 구현)
            self._load_gongjong_list_from_file(category)

    def _create_gongjong_panel(self, parent_layout):
        """공종 패널 생성 (삭제됨)"""
        # 사용자 요청으로 공종 입력/추가/삭제 메뉴가 제거되었습니다.
        # 기존 레이아웃 구성을 유지하기 위해 빈 프레임 또는 리스트만 남길 수 있습니다.
        pass

    def _create_output_gongjong_panel(self, parent_layout):
        """을지용 산출공종 패널 생성"""
        panel = QFrame()
        panel.setFixedWidth(200)
        panel.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa; 
                border: none;
                border-right: 1px solid #dee2e6;
            }
        """)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        # 헤더
        header = QWidget()
        header.setFixedHeight(30)
        header.setStyleSheet("""
            background-color: #e1e1e1;
            border: 1px solid #707070;
            border-top: 1px solid #ffffff;
            border-left: 1px solid #ffffff;
            border-bottom: 2px solid #606060;
            border-right: 2px solid #606060;
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(10, 0, 10, 0)

        title = QLabel("산출공종")
        title.setStyleSheet("font-weight: bold; color: #495057;")
        h_layout.addWidget(title)

        panel_layout.addWidget(header)

        # 리스트 위젯
        self.output_gongjong_list = QListWidget()

        # 폰트 설정 (굴림체 적용)
        out_font = QFont("굴림체", 11)
        out_font.setStretch(100)
        self.output_gongjong_list.setFont(out_font)

        self.output_gongjong_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: white;
                font-family: '새굴림';
                font-size: 11pt;
            }
            QListWidget::item {
                height: 22px;
                padding-left: 0px;
                border-bottom: 1px solid #f1f3f5;
            }
            QListWidget::item:hover { background-color: #f8f9fa; }
            QListWidget::item:selected { background-color: #e1e1e1; color: black; border: 1px solid #707070; font-weight: normal; }
        """)
        self.output_gongjong_list.itemDoubleClicked.connect(
            self._on_output_gongjong_item_double_clicked
        )
        panel_layout.addWidget(self.output_gongjong_list)

        parent_layout.addWidget(panel)

    def _safe_load_gongjong(self):
        """공종 파일 안전하게 로드"""
        try:
            if os.path.exists(self.gongjong_file_path):
                with open(self.gongjong_file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                self.gongjong_items = [line.strip() for line in lines if line.strip()]
            else:
                # 기본 공종 목록
                self.gongjong_items = [
                    "1. 전기공사",
                    "1-1. 간선공사",
                    "1-2. 분전반공사",
                    "1-3. 배선공사",
                    "1-4. 조명공사",
                    "1-5. 콘센트공사",
                    "1-6. 접지공사",
                    "1-7. 기타공사",
                ]

            self._refresh_gongjong_list()
            self._refresh_output_gongjong_list()

            # [NEW] 동적 공종 리스트 초기 로딩 (공통)
            current_category = self.gongjong_category_combo.currentText()
            if current_category:
                self._load_gongjong_list_from_file(current_category)

        except Exception as e:
            print(f"[ERROR] Failed to load gongjong: {e}")

    def _on_category_changed(self, category):
        """카테고리 변경 시 호출"""
        print(f"Category changed to: {category}")
        self._load_gongjong_list_from_file(category)

    def _load_gongjong_list_from_file(self, category):
        """파일에서 공종 리스트 로드"""
        # 경로: D:\이지맥스\사용자목록\공종리스트\{category}.txt
        # category가 '공통'인 경우 '공통.txt' 로딩

        base_path = r"D:\이지맥스\사용자목록\공종리스트"
        file_path = os.path.join(base_path, f"{category}.txt")

        self.gongjong_list.clear()  # Clear existing items

        # Debug: Show what we are trying to load
        # self.gongjong_list.addItem(f"Loading: {category}...") # Temporary debug

        if not os.path.exists(file_path):
            self.gongjong_list.addItem(f"파일 없음: {file_path}")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:  # utf-8 시도
                lines = f.readlines()
        except UnicodeDecodeError:
            try:
                with open(
                    file_path, "r", encoding="cp949"
                ) as f:  # cp949 시도 (한글 윈도우)
                    lines = f.readlines()
            except Exception as e:
                self.gongjong_list.addItem(f"Encoding Fail: {e}")
                return
        except Exception as e:
            self.gongjong_list.addItem(f"Read Error: {e}")
            return

        if not lines:
            self.gongjong_list.addItem("(내용 없음)")

        for line in lines:
            # 텍스트 정규화: 탭이나 여러 공백을 단일 공백으로 치환
            line = re.sub(r"\s+", " ", line).strip()
            if line:
                self.gongjong_list.addItem(line)

    def _refresh_gongjong_list(self):
        """공종 리스트 새로고침"""
        self.gongjong_list.clear()
        for item in self.gongjong_items:
            list_item = QListWidgetItem(item)
            self.gongjong_list.addItem(list_item)

    def _refresh_output_gongjong_list(self):
        """을지용 산출공종 리스트 새로고침"""
        if hasattr(self, "output_gongjong_list"):
            self.output_gongjong_list.clear()
            for item in self.gongjong_items:
                list_item = QListWidgetItem(item)
                self.output_gongjong_list.addItem(list_item)

    def _on_gapji_item_changed(self, item):
        """갑지 아이템 변경 시 처리 (프로젝트명 동기화 등)"""
        # 0행 공종명(산출공종) 변경 시 프로젝트명 업데이트
        if item.row() == 0 and item.column() == self.GONGJONG_COL:
            text = item.text()
            # 안내 텍스트가 아니면 프로젝트명에 반영하고 글자색 검정으로 변경
            if text and text != "새로운 공사명을 등록하세요.":
                self.lbl_project_name.setText(f"Project: {text}")
                if item.foreground().color() != QColor(0, 0, 0):
                    self.gapji_table.blockSignals(True)
                    item.setForeground(QColor(0, 0, 0))

                    # 2행(Index 1) 공종명에 "공통작업" 및 번호 "0" 자동 입력 (사용자 요청)
                    # 1. 공종순서 컬럼 (2번 컬럼)
                    seq_item = self.gapji_table.item(1, self.GONGJONG_NUM_COL)
                    if not seq_item:
                        seq_item = QTableWidgetItem()
                        seq_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.gapji_table.setItem(1, self.GONGJONG_NUM_COL, seq_item)
                    seq_item.setText("0")

                    # 2. 공종명 컬럼 (3번 컬럼)
                    common_item = self.gapji_table.item(1, self.GONGJONG_COL)
                    if not common_item or not common_item.text().strip():
                        if not common_item:
                            common_item = QTableWidgetItem()
                            self.gapji_table.setItem(1, self.GONGJONG_COL, common_item)

    def _on_gapji_item_changed(self, item):
        """갑지 아이템 변경 시 처리 (프로젝트명 동기화 등)"""
        # (기존 로직은 on_gapji_cell_changed로 대부분 이동됨)
        if item.row() == 0 and item.column() == self.GONGJONG_COL:
            text = item.text()
            if text == "새로운 공사명을 등록하세요.":
                if item.foreground().color() != QColor(150, 150, 150):
                    self.gapji_table.blockSignals(True)
                    item.setForeground(QColor(150, 150, 150))
                    self.gapji_table.blockSignals(False)
            else:
                if item.foreground().color() != QColor(0, 0, 0):
                    self.gapji_table.blockSignals(True)
                    item.setForeground(QColor(0, 0, 0))
                    self.gapji_table.blockSignals(False)

    def _on_gongjong_item_clicked(self, item):
        """공종 아이템 클릭 시 (우측 패널)"""
        text = item.text()
        if "파일 없음" in text or "오류" in text:
            return

        # 1-2행(Index 0,1)은 프로젝트명 및 공통 정보이므로 보호.
        # 현재 선택된 행과 무관하게 항상 3행(Index 2)부터 첫 빈칸을 찾아 입력함.
        target_row = 2

        # 빈 행 찾기 (또는 항목이 있는 경우 다음 행)
        # 만약 현재 선택된 행의 공종명이 비어있지 않다면, 그 이후의 빈 행을 찾음
        while target_row < self.gapji_table.rowCount():
            cell_item = self.gapji_table.item(target_row, self.GONGJONG_COL)
            if not cell_item or not cell_item.text().strip():
                break
            target_row += 1

        # 화면 끝이면 확장
        if target_row >= self.gapji_table.rowCount():
            self.gapji_table.setRowCount(target_row + 10)

        self.gapji_table.blockSignals(True)

        # 1. 공종명 보정: 소스 리스트의 번호는 무시하고 항상 순차 번호 부여
        # 앞부분의 숫자. 또는 숫자-숫자. 패턴 제거하여 순수 명칭만 추출
        clean_name = re.sub(r"^[\d\.-]+\s*", "", text).strip()

        # 이전 행들 중 공종명 컬럼의 마지막 정수 번호 찾기 (순차적 번호 부여)
        next_num = 1
        for r in range(target_row - 1, 1, -1):  # 2행(index 1)까지 검색
            prev_item = self.gapji_table.item(r, self.GONGJONG_COL)
            if prev_item:
                prev_text = prev_item.text()
                match = re.match(r"^(\d+)", prev_text)
                if match:
                    next_num = int(match.group(1)) + 1
                    break

        final_num = str(next_num)

        # 공종순서 컬럼에 번호 출력 (계층형이 아닌 순차적 정수)
        num_item = QTableWidgetItem(final_num)
        num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gapji_table.setItem(target_row, self.GONGJONG_NUM_COL, num_item)

        # 공종명 컬럼 (번호. 명칭 형태로 입력)
        self.gapji_table.setItem(
            target_row,
            self.GONGJONG_COL,
            QTableWidgetItem(f"{final_num}. {clean_name}"),
        )

        # 2. 구분 자동 입력 (산출공종 버튼)
        self._set_gubun_button(target_row)

        self.gapji_table.blockSignals(False)
        self.gapji_table.setCurrentCell(target_row, self.GONGJONG_COL)

    def _on_output_gongjong_item_double_clicked(self, item):
        """을지 공종 더블클릭 시"""
        gongjong_text = item.text()
        current_row = self.eulji_table.currentRow()
        if current_row >= 0:
            self.eulji_table.setItem(current_row, 1, QTableWidgetItem(gongjong_text))

    def _add_gongjong(self):
        """공종 추가"""
        text = self.gongjong_input.text().strip()
        if text:
            self.gongjong_items.append(text)
            self._refresh_gongjong_list()
            self._refresh_output_gongjong_list()
            self.gongjong_input.clear()

    def _delete_gongjong(self):
        """공종 삭제"""
        current_item = self.gongjong_list.currentItem()
        if current_item:
            text = current_item.text()
            if text in self.gongjong_items:
                self.gongjong_items.remove(text)
                self._refresh_gongjong_list()
                self._refresh_output_gongjong_list()

    def _save_gongjong_list(self):
        """공종 목록 저장"""
        try:
            # 폴더 생성
            os.makedirs(self.gongjong_folder_path, exist_ok=True)

            with open(self.gongjong_file_path, "w", encoding="utf-8") as f:
                for item in self.gongjong_items:
                    f.write(item + "\n")

            # 카테고리별 파일도 저장
            category_file = os.path.join(
                self.gongjong_folder_path, f"{self.gongjong_category}.txt"
            )
            with open(category_file, "w", encoding="utf-8") as f:
                for item in self.gongjong_items:
                    f.write(item + "\n")

            QMessageBox.information(
                self.main_window, "저장 완료", "공종 목록이 저장되었습니다."
            )
        except Exception as e:
            QMessageBox.critical(
                self.main_window, "저장 오류", f"공종 목록 저장 실패: {e}"
            )

    def on_gapji_cell_changed(self, row, column):
        """갑지 테이블 셀 변경 시"""
        if column == self.GONGJONG_COL:
            item = self.gapji_table.item(row, column)
            if not item:
                return
            text = item.text().strip()

            # 1. 공사명(0행) 입력 시 -> 2행(Index 1)에 "공통" 및 자동 정보 설정
            if row == 0:
                if text and text != "새로운 공사명을 등록하세요.":
                    self.gapji_table.blockSignals(True)
                    # 프로젝트명 동기화
                    if hasattr(self, "lbl_project_name"):
                        self.lbl_project_name.setText(f"Project: {text}")

                    # 2행(Index 1) "구분" 컬럼에 "공  통" 입력 (사용자 요청)
                    gubun_item = self.gapji_table.item(1, self.GUBUN_COL)
                    if not gubun_item:
                        gubun_item = QTableWidgetItem("공  통")
                        gubun_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.gapji_table.setItem(1, self.GUBUN_COL, gubun_item)
                    else:
                        gubun_item.setText("공  통")

                    # 2행 "공종명" 컬럼에 "0. 공통작업" 입력
                    common_name = "0. 공통작업"
                    common_item = self.gapji_table.item(1, self.GONGJONG_COL)
                    if not common_item or not common_item.text().strip():
                        if not common_item:
                            common_item = QTableWidgetItem(common_name)
                            self.gapji_table.setItem(1, self.GONGJONG_COL, common_item)
                        else:
                            common_item.setText(common_name)

                    # 2행 "공종순서" 컬럼 번호 "0" 설정 (기존 버튼 유지)
                    seq_item = self.gapji_table.item(1, self.GONGJONG_NUM_COL)
                    if not seq_item:
                        seq_item = QTableWidgetItem("0")
                        seq_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.gapji_table.setItem(1, self.GONGJONG_NUM_COL, seq_item)
                    else:
                        # setItem을 하면 버튼 위젯이 삭제되므로, 위젯이 없는 경우에만 setItem/setText 시도
                        if not self.gapji_table.cellWidget(1, self.GONGJONG_NUM_COL):
                            seq_item.setText("0")

                    self.gapji_table.blockSignals(False)

            # 2. 산출공종(2행 이상) 입력 시 -> 버튼 설치
            elif row >= 2:
                if text:
                    self.gapji_table.blockSignals(True)
                    # 공종 패턴(번호) 확인
                    num_match = re.match(r"^([\d\.-]+)\s*", text)
                    if num_match:
                        gong_num = num_match.group(1).strip().rstrip(".")
                        # 배경색 설정
                        item.setBackground(QColor(255, 255, 200))
                        # 번호 텍스트도 설정 (버튼이 없으면 보이도록, 버튼이 있으면 가려짐)
                        seq_item = self.gapji_table.item(row, self.GONGJONG_NUM_COL)
                        if not seq_item:
                            seq_item = QTableWidgetItem(gong_num)
                            seq_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            self.gapji_table.setItem(
                                row, self.GONGJONG_NUM_COL, seq_item
                            )
                        else:
                            if not self.gapji_table.cellWidget(
                                row, self.GONGJONG_NUM_COL
                            ):
                                seq_item.setText(gong_num)

                    # 산출공종 버튼 및 번호정리 버튼 배치 (항상 수행 또는 버튼이 없을 때만 수행)
                    if not self.gapji_table.cellWidget(row, self.GUBUN_COL):
                        self._set_gubun_button(row)

                    self.gapji_table.blockSignals(False)

    def on_gapji_cell_clicked(self, row, column):
        """갑지 테이블 셀 클릭 시"""
        pass

    def on_eulji_cell_clicked(self, row, column):
        """을지 테이블 셀 클릭 시"""
        print(f"[DEBUG] CELL CLICKED: row={row}, col={column}")
        try:
            from datetime import datetime

            log_path = os.path.join(self.project_root, "debug_trigger.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(
                    f"[{datetime.now()}] on_eulji_cell_clicked: row={row}, col={column}\n"
                )
        except:
            pass

        # [REMOVED] 클릭 시 자료사전 호출 로직 제거 (사용자 재요청: 클릭 시에는 '산출일위표'가 떠야 함)
        # Tab 키 입력 시에는 TableEventFilter를 통해 여전히 '자료사전'이 호출됩니다.

        # [NEW] 산출일위표 연동: 산출목록 컬럼이면 팝업 노출, 아니면 숨김
        if hasattr(self, "unit_price_trigger") and self.unit_price_trigger:
            self.unit_price_trigger.handle_cell_selection(row, column)
        else:
            print("[ERROR] unit_price_trigger not found in OutputDetailTab!")

    def _show_reference_popup(self, row, col):
        """자료사전 DB 팝업 통합 호출 및 인스턴스 관리"""
        try:
            # 1. 인스턴스 생성 또는 재사용
            if self.reference_popup is None:
                from popups.database_reference_popup import DatabaseReferencePopup

                self.reference_popup = DatabaseReferencePopup(
                    self
                )  # parent_popup으로 self 전달

            # 2. 테이블 포커스/셀 설정 및 대상 테이블 감지
            target_table = None
            if hasattr(self, "eulji_table"):
                if (
                    self.eulji_table.hasFocus()
                    or self.eulji_table.viewport().hasFocus()
                ):
                    target_table = self.eulji_table
                self.eulji_table.setCurrentCell(row, col)

            from PyQt6.QtWidgets import QApplication

            focus_w = QApplication.focusWidget()
            if not target_table and focus_w:
                # 포커스된 위젯이 테이블이거나 테이블의 자식인 경우 탐색
                from PyQt6.QtWidgets import QTableWidget

                curr = focus_w
                while curr:
                    if isinstance(curr, QTableWidget):
                        target_table = curr
                        break
                    curr = curr.parent()

            # 3. 팝업 표시 (대상 테이블 명시적 전달)
            self.reference_popup.prepare_show(row, col, target_table)
            self.reference_popup.exec()

        except Exception as e:
            with open("tab_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[ERROR] _show_reference_popup failed: {e}\n")
            QMessageBox.critical(
                self.main_window, "오류", f"자료사전을 열 수 없습니다: {e}"
            )

    def _on_eulji_selection_changed(self, selected, deselected):
        """키보드 등으로 선택 영역 변경 시"""
        current_row = self.eulji_table.currentRow()
        current_col = self.eulji_table.currentColumn()
        if current_row >= 0 and current_col >= 0:
            if hasattr(self, "unit_price_trigger"):
                self.unit_price_trigger.handle_cell_selection(current_row, current_col)

    def on_eulji_cell_changed(self, row, column):
        """을지 테이블 셀 변경 시"""
        try:
            if column == self.EULJI_COLS["FORMULA"]:
                # 산출수식 변경 시 계산 (새로운 파서 사용)
                formula_item = self.eulji_table.item(row, column)
                if formula_item:
                    formula = formula_item.text().strip()
                    try:
                        # [Phase 1-1] 새로운 파서 사용: 문자 포함 수식 지원
                        from utils.formula_parser import parse_formula

                        result = parse_formula(formula)

                        self.eulji_table.blockSignals(True)
                        total_item = self.eulji_table.item(
                            row, self.EULJI_COLS["TOTAL"]
                        )
                        if not total_item:
                            total_item = QTableWidgetItem()
                            self.eulji_table.setItem(
                                row, self.EULJI_COLS["TOTAL"], total_item
                            )

                        # 결과가 0이 아니거나 수식이 있으면 표시
                        if result != 0 or formula.strip():
                            # 소수점 정리 (불필요한 .0 제거)
                            if result == int(result):
                                total_item.setText(str(int(result)))
                            else:
                                total_item.setText(str(result))
                        else:
                            total_item.setText("")
                        self.eulji_table.blockSignals(False)
                    except Exception as e:
                        print(f"[WARN] 수식 계산 실패: {formula} -> {e}")
                        self._clear_eulji_total(row)

            # [성능 최적화] 즉시 저장 대신 타이머 시작 (300ms 후 실행)
            if hasattr(self, "save_timer"):
                self.save_timer.start(300)

        except Exception as e:
            print(f"[ERROR] on_eulji_cell_changed: {e}")

    def _clear_eulji_total(self, row):
        """계 컬럼 비우기"""
        self.eulji_table.blockSignals(True)
        total_item = self.eulji_table.item(row, self.EULJI_COLS["TOTAL"])
        if total_item:
            total_item.setText("")
        self.eulji_table.blockSignals(False)

    def _on_save_timer_timeout(self):
        """지연된 데이터 저장 및 마커 업데이트 실행"""
        if hasattr(self, "current_gongjong") and self.current_gongjong:
            self._save_eulji_data(self.current_gongjong)
            self._update_gapji_marker(self.current_gongjong)

    def _on_eulji_double_clicked(self, row, column):
        """을지 테이블 더블 클릭 시 - 전등/전열 팝업 재진입"""
        item = self.eulji_table.item(row, self.EULJI_COLS["ITEM"])
        if not item:
            return

        # 산출목록이 "전등수량(갯수)산출"인 경우 팝업 호출
        if item.text() == "전등수량(갯수)산출":
            if hasattr(self, "lighting_manager"):
                # 현재 행의 상세 데이터 로드하여 팝업 열기
                self.lighting_manager.edit_row(row)

    def _set_gubun_button(self, row):
        """특정 행의 구분 컬럼에 산출공종 버튼 배치"""
        btn = QPushButton("산출공종")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #fff9c4;
                border: 1px solid #707070;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-bottom: 2px solid #505050;
                border-right: 2px solid #505050;
                border-radius: 2px;
                font-family: '새굴림';
                font-size: 10pt;
                padding: 1px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #fff176;
                border-bottom: 2px solid #303030;
                border-right: 2px solid #303030;
            }
            QPushButton:pressed {
                background-color: #fbc02d;
                border: 1px solid #707070;
                border-top: 2px solid #505050;
                border-left: 2px solid #505050;
                border-bottom: 1px solid #ffffff;
                border-right: 1px solid #ffffff;
                padding-top: 2px;
                padding-left: 2px;
            }
        """)
        btn.clicked.connect(lambda: self._navigate_to_eulji(row))
        self.gapji_table.setCellWidget(row, self.GUBUN_COL, btn)

        # [제거] 공종순서 컬럼에 '번호정리' 버튼 배치 (사용자 요청: 2행에만 필요함)
        # self.gapji_table.setCellWidget(row, self.GONGJONG_NUM_COL, self._create_reorder_button())

    def _create_reorder_button(self):
        """'번호정리' 버튼 위젯 생성"""
        btn = QPushButton("번호정리")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #e3f2fd;
                border: 1px solid #707070;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-bottom: 2px solid #505050;
                border-right: 2px solid #505050;
                border-radius: 2px;
                font-family: '새굴림';
                font-size: 9pt;
                padding: 1px;
                color: #0d47a1;
            }
            QPushButton:hover {
                background-color: #bbdefb;
            }
            QPushButton:pressed {
                background-color: #90caf9;
                border-top: 2px solid #505050;
                border-left: 2px solid #505050;
                border-bottom: 1px solid #ffffff;
                border-right: 1px solid #ffffff;
            }
        """)
        btn.clicked.connect(self._reorder_gongjong_numbers)
        return btn

    def _navigate_to_eulji(self, row):
        """특정 공종의 을지(내역서)로 이동 및 정보 연동"""
        item = self.gapji_table.item(row, self.GONGJONG_COL)
        if item:
            new_gongjong_name = item.text().strip()

            # 1. 이전 공종 데이터 저장
            if self.current_gongjong and self.current_gongjong != new_gongjong_name:
                self._save_eulji_data(self.current_gongjong)
                self._update_gapji_marker(self.current_gongjong)

            # 2. 새 공종 정보 업데이트
            self.current_gongjong = new_gongjong_name
            self.current_gongjong_label.setText(f"산출공종: {new_gongjong_name}")

            # 3. 새 공종 데이터 로드
            self._load_eulji_data(new_gongjong_name)

            # 4. 화면 전환
            self._switch_view(1)
            print(f"[DEBUG] Navigating to Eulji for: {new_gongjong_name}")
        else:
            QMessageBox.warning(
                self.main_window, "알림", "공종명이 입력되지 않았습니다."
            )

    def _save_eulji_data(self, gongjong_name):
        """현재 을지 테이블의 데이터를 메모리에 저장 (임시 캐시)"""
        if not gongjong_name:
            return

        data = []
        for r in range(self.eulji_table.rowCount()):
            row_data = {}
            has_content = False
            # 모든 컬럼 순회하며 데이터 추출
            for col_idx in range(self.eulji_table.columnCount()):
                item = self.eulji_table.item(r, col_idx)
                if item and item.text().strip():
                    row_data[col_idx] = item.text()
                    has_content = True
            if has_content:
                data.append(row_data)

        self.eulji_data[gongjong_name] = data

    def _load_eulji_data(self, gongjong_name):
        """메모리에서 특정 공종의 을지 데이터를 불러와 테이블에 표시"""
        self.eulji_table.blockSignals(True)
        self.eulji_table.clearContents()

        data = self.eulji_data.get(gongjong_name, [])
        for r, row_data in enumerate(data):
            # 필요시 행 추가
            if r >= self.eulji_table.rowCount():
                self.eulji_table.setRowCount(r + 10)

            for col_idx, text in row_data.items():
                self.eulji_table.setItem(r, col_idx, QTableWidgetItem(text))

        self.eulji_table.blockSignals(False)

    def _update_gapji_marker(self, gongjong_name):
        """갑지 테이블의 #. 컬럼에 데이터 유무(*) 표시 (사용자 요청)"""
        if not gongjong_name:
            return

        # 데이터 유무 확인 (비어있지 않은 행이 하나라도 있는지)
        data = self.eulji_data.get(gongjong_name, [])
        has_data = len(data) > 0

        # 갑지에서 해당 공종 행 찾기
        for r in range(self.gapji_table.rowCount()):
            item = self.gapji_table.item(r, self.GONGJONG_COL)
            if item and item.text().strip() == gongjong_name:
                self.gapji_table.blockSignals(True)
                marker = "*" if has_data else ""
                marker_item = QTableWidgetItem(marker)
                marker_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.gapji_table.setItem(r, self.NUM_COL, marker_item)
                self.gapji_table.blockSignals(False)
                break

    def _reorder_gongjong_numbers(self):
        """갑지 테이블의 공종 번호를 순차적/계층적으로 재정리 (사용자 요청)"""
        self.gapji_table.blockSignals(True)

        last_old_base = None
        new_base_counter = 0

        # 3행(Index 2)부터 시작
        for r in range(2, self.gapji_table.rowCount()):
            item = self.gapji_table.item(r, self.GONGJONG_COL)
            if not item or not item.text().strip():
                # 빈 행은 순번도 비움
                self.gapji_table.setItem(r, self.GONGJONG_NUM_COL, QTableWidgetItem(""))
                continue

            text = item.text().strip()
            # 1.1.2 등 계층형 패턴 추출
            match = re.match(r"^([\d\.-]+)\s*(.*)", text)

            if match:
                old_full_prefix = match.group(1).strip().rstrip(".")
                name = match.group(2).strip()

                # 메인 번호(앞쪽 정수) 추출
                base_match = re.match(r"^(\d+)", old_full_prefix)
                if base_match:
                    old_base = base_match.group(1)
                    suffix = old_full_prefix[len(old_base) :]  # ".1" 등

                    if old_base != last_old_base:
                        new_base_counter += 1
                        last_old_base = old_base

                    new_full_prefix = f"{new_base_counter}{suffix}"

                    # 1. 공종순서 업데이트 (버튼 위젯이 없는 경우에만 업데이트하여 버튼 유지)
                    if not self.gapji_table.cellWidget(r, self.GONGJONG_NUM_COL):
                        seq_item = QTableWidgetItem(new_full_prefix)
                        seq_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.gapji_table.setItem(r, self.GONGJONG_NUM_COL, seq_item)

                    # 2. 공종명 업데이트 (번호. 명칭)
                    item.setText(f"{new_full_prefix}. {name}")
                else:
                    # 숫자로 시작하지 않는 경우 (예: "특수공종")
                    new_base_counter += 1
                    last_old_base = None
                    new_prefix = str(new_base_counter)

                    seq_item = QTableWidgetItem(new_prefix)
                    seq_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.gapji_table.setItem(r, self.GONGJONG_NUM_COL, seq_item)
                    item.setText(f"{new_prefix}. {text}")
            else:
                # 번호가 아예 없는 경우 순차 번호 부여
                new_base_counter += 1
                last_old_base = None
                new_prefix = str(new_base_counter)

                seq_item = QTableWidgetItem(new_prefix)
                seq_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.gapji_table.setItem(r, self.GONGJONG_NUM_COL, seq_item)
                item.setText(f"{new_prefix}. {text}")

        self.gapji_table.blockSignals(False)
        print("[INFO] 공종 번호 재정리 완료")  # 콘솔 로그로 대체

    def _update_project_name(self, name):
        """프로젝트명 업데이트"""
        self.lbl_project_name.setText(f"Project: {name}")

    def _show_about_dialog(self):
        """[NEW] 도움말 - 프로그램 정보 표시"""
        from PyQt6.QtGui import QPixmap, QIcon
        from PyQt6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QLabel,
            QHBoxLayout,
            QPushButton,
        )

        dlg = QDialog(self.main_window)
        dlg.setWindowTitle("프로그램 정보 (About)")
        dlg.setFixedSize(400, 320)
        dlg.setStyleSheet("background-color: white; font-family: '새굴림';")

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)

        # 1. 아이콘 & 제목
        header_layout = QHBoxLayout()
        icon_label = QLabel()
        # [수정] 사용자 지정 로고 경로 적용
        icon_path = r"D:\오아시스\SANCHUL_Sheet_1\assets\icons\오아시스_로고01.png"
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(
                80,
                80,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pixmap)
        header_layout.addWidget(icon_label)

        title_layout = QVBoxLayout()
        title_label = QLabel("오아시스 (OASIS)")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #004080;")
        ver_label = QLabel("Version 1.1.0")
        ver_label.setStyleSheet("font-size: 10pt; color: #666;")
        title_layout.addWidget(title_label)
        title_layout.addWidget(ver_label)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #dee2e6;")
        layout.addWidget(line)

        # 2. 상세 정보 (사용자 요청 정보로 수정)
        info_text = """
        <table style='width: 100%; font-size: 11pt; color: #333;'>
            <tr><td style='width: 80px;'><b>개발</b></td><td>전기견적.산출 자동화 시스템</td></tr>
            <tr><td><b>개발자</b></td><td>KIM PHIL JUNG</td></tr>
            <tr><td><b>H/P</b></td><td>+62 812-8094-3179</td></tr>
            <tr><td><b>연락처</b></td><td>kacang@nate.com</td></tr>
        </table>
        """
        info_label = QLabel(info_text)
        info_label.setStyleSheet("font-family: '새굴림';")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        layout.addStretch()

        # 3. 닫기 버튼
        close_btn = QPushButton("확인")
        close_btn.setFixedSize(80, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #ced4da;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #e9ecef; }
        """)
        close_btn.clicked.connect(dlg.accept)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dlg.exec()

    def _show_system_log(self):
        """[NEW] 시스템 로그 및 메뉴얼 파일(SYSTEM_LOG.md) 열기"""
        log_path = os.path.join(self.project_root, "SYSTEM_LOG.md")
        if os.path.exists(log_path):
            try:
                # Windows 기본 텍스트 편집기(메모장 등)로 열기
                os.startfile(log_path)
            except Exception as e:
                QMessageBox.warning(
                    self.main_window, "오류", f"시스템 로그를 열 수 없습니다: {e}"
                )
        else:
            QMessageBox.information(
                self.main_window, "알림", "시스템 로그 파일이 존재하지 않습니다."
            )

    def _show_modules_menu(self):
        """모듈 메뉴 버튼 클릭 - 드롭다운 메뉴 표시"""
        # 간단한 메시지로 모듈 사용법 안내
        QMessageBox.information(
            self.main_window,
            "모듈 메뉴",
            "상단 툴바의 버튼을 사용하여 각 모듈을 실행하세요.\n\n"
            "■ Phase 3: 집계/관리\n"
            "  - 소요자재: 전체 공종 자재 집계\n"
            "  - 일괄변경: 수량/재질 일괄 수정\n\n"
            "■ Phase 4: 출력/변환\n"
            "  - 견적변환: 산출 → 견적 내역서\n"
            "  - 엑셀출력: 엑셀 파일 내보내기\n"
            "  - 산식검사: 산출수식 오류 검사\n\n"
            "■ Phase 5: 고급 기능\n"
            "  - 산출판: 시각적 판서 형식\n"
            "  - 간선산출: 케이블 경로별 관리\n"
            "  - 설계변경: 수량/규격 변경 이력\n\n"
            "■ Phase 6: 전문 기능\n"
            "  - 그림산출: 도면에서 산출 선택\n"
            "  - CAD연동: DXF/DWG 파일 연동",
        )

    def _on_toolbar_clicked(self, button_name):
        """[Phase 1-6] 툴바 버튼 클릭 핸들러"""
        print(f"[TOOLBAR] 버튼 클릭: {button_name}")

        # �업 모듈 딕셔너리
        popup_modules = {
            # Phase 3: 집계/관리
            "material_summary": {
                "class": "MaterialSummaryPopup",
                "module": "popups.material_summary_popup",
                "title": "소요자재 집계",
            },
            "batch_tools": {
                "class": "BatchToolsPopup",
                "module": "popups.batch_tools_popup",
                "title": "일괄 변경 도구",
            },
            # Phase 4: 출력/변환
            "estimate_convert": {
                "class": "EstimateOptionsPopup",
                "module": "popups.estimate_options_popup",
                "title": "견적 변환 옵션",
            },
            "excel_export": {
                "class": None,
                "module": "core.excel_exporter",
                "function": "show_export_dialog",
                "title": "엑셀 출력",
            },
            "formula_check": {
                "class": "FormulaCheckPopup",
                "module": "popups.formula_check_popup",
                "title": "산식 오류 검사",
            },
            # Phase 5: 고급 기능
            "output_board": {
                "class": "OutputBoardPopup",
                "module": "popups.output_board_popup",
                "title": "산출판",
            },
            "cable_routing": {
                "class": "CableRoutingPopup",
                "module": "popups.cable_routing_popup",
                "title": "간선 산출판",
            },
            "design_change": {
                "class": "DesignChangePopup",
                "module": "popups.design_change_popup",
                "title": "설계변경 관리",
            },
            # Phase 6: 전문 기능
            "graphic_output": {
                "class": "GraphicOutputPopup",
                "module": "popups.graphic_output_popup",
                "title": "그림산출",
            },
            "cad_integration": {
                "class": None,
                "module": "core.cad_integration",
                "function": "show_cad_import_dialog",
                "title": "CAD 파일 가져오기",
            },
            "cad_integration": {
                "class": None,
                "module": "core.cad_integration",
                "function": "show_cad_import_dialog",
                "title": "CAD 파일 가져오기",
            },
        }

        if button_name not in popup_modules:
            QMessageBox.warning(
                self.main_window, "오류", f"알 수 없는 버튼: {button_name}"
            )
            return

        module_info = popup_modules[button_name]
        module_name = module_info["module"]
        class_name = module_info.get("class")
        func_name = module_info.get("function")
        title = module_info["title"]

        try:
            # 모듈 임포트
            if "." in module_name:
                parts = module_name.rsplit(".", 1)
                module = __import__(parts[0], fromlist=[parts[1]])
                submodule = getattr(module, parts[1])
            else:
                submodule = __import__(module_name)

            # 함수 또는 클래스 실행
            if func_name:
                # 함수인 경우 (모달ess 실행)
                if hasattr(submodule, func_name):
                    func = getattr(submodule, func_name)
                    func(parent=self.main_window, eulji_data=self.eulji_data)
                else:
                    QMessageBox.warning(
                        self.main_window,
                        "오류",
                        f"함수를 찾을 수 없습니다: {func_name}",
                    )
            elif class_name:
                # 클래스인 경우 (모달ダイア로그)
                if hasattr(submodule, class_name):
                    dlg_class = getattr(submodule, class_name)
                    dlg = dlg_class(self.main_window, self.eulji_data)
                    dlg.setWindowTitle(title)
                    dlg.exec()
                else:
                    QMessageBox.warning(
                        self.main_window,
                        "오류",
                        f"클래스를 찾을 수 없습니다: {class_name}",
                    )
            else:
                QMessageBox.information(
                    self.main_window, "알림", f"{title} 모듈이 준비중입니다."
                )

        except ImportError as e:
            QMessageBox.warning(
                self.main_window,
                "모듈 오류",
                f"{title} 모듈을 로드할 수 없습니다.\n\n오류: {e}\n\nrequirements.txt의 의존성을 확인하세요.",
            )
        except Exception as e:
            QMessageBox.critical(
                self.main_window, "실행 오류", f"{title} 실행 중 오류 발생:\n\n{str(e)}"
            )

    def _log_system_event(self, msg):
        """시스템 이벤트를 디버그 로그에 기록 (나중에 SYSTEM_LOG.md 업데이트 참고용)"""
        try:
            log_file = os.path.join(self.project_root, "debug_trigger.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] [SYSTEM_EVENT] {msg}\n")
        except:
            pass


# 테스트용 진입점
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 메인 윈도우 생성
    main_window = QMainWindow()
    main_window.setWindowTitle("산출내역 테스트")
    main_window.setGeometry(100, 100, 1400, 900)

    # 산출내역 탭 생성
    tab = OutputDetailTab(main_window)
    widget = tab.create_tab()

    main_window.setCentralWidget(widget)
    main_window.show()

    sys.exit(app.exec())
