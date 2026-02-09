"""
공통 컬럼 설정 모듈
Common Column Settings - 모든 탭에서 사용하는 공통 컬럼 규격
"""

from PyQt6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QStyledItemDelegate,
    QLineEdit,
    QHeaderView,
    QStyle,
    QStyleOptionViewItem,
)
from PyQt6.QtCore import Qt, QRectF, QTimer
from PyQt6.QtGui import QIntValidator, QDoubleValidator, QFont, QTextOption, QPalette, QColor
import locale

# 로케일 설정 (천단위 표시용)
try:
    locale.setlocale(locale.LC_ALL, "ko_KR.UTF-8")
except:
    try:
        locale.setlocale(locale.LC_ALL, "")
    except:
        pass


# ============================================================================
# 스타일 상수
# ============================================================================

DEFAULT_ROWS = 500  # 기본 행 수 (엑셀 스타일 무한 그리드)
DEFAULT_ROW_HEIGHT = 18  # 24 -> 18 (상하 1px 여백 최적화)
UNIT_PRICE_ROW_HEIGHT = 22  # 산출일위표 전용 (헤더와 조화되는 높이)
DEFAULT_FONT_SIZE = 11
HEADER_FONT_SIZE = 11

# Placeholder 텍스트 (빈 셀에 표시)
PLACEHOLDER_GONGJONG = "새로운 공사명을 등록하세요."


# ============================================================================
# 컬럼 상수 정의
# ============================================================================

# 12개 공통 컬럼 (갑지용) - 구분을 공종순서 앞으로 이동
COMMON_COLUMNS = [
    "#.",
    "구분",
    "공종순서",
    "공 종 명 (산출공종)",
    "단위",
    "층고(m)",
    "천정(m)",
    "수량",
    "비고",
]

# 컬럼 너비 (픽셀)
COLUMN_WIDTHS = {
    "#.": 28,
    "공종순서": 72,  # Increased by 15% (62 -> 72)
    "구분": 100,
    "공 종 명 (산출공종)": 375,
    "단위": 55,  # Increased by 20px (35 -> 55)
    "층고(m)": 80,
    "천정(m)": 80,
    "수량": 50,
    "비고": 200,
}

# 컬럼 최대 길이 (문자 수)
COLUMN_MAX_LENGTH = {
    "#.": 4,
    "공종순서": 10,
    "구분": 8,
    "공 종 명 (산출공종)": 50,
    "단위": 6,
    "층고(m)": 6,
    "천정(m)": 6,
    "수량": 11,
    "비고": 50,
}

# 숫자 컬럼 목록 (천단위 표시 적용)
NUMERIC_COLUMNS = ["수량", "층고(m)", "천정(m)", "계"]

# 가운데 정렬 컬럼 목록
CENTER_COLUMNS = ["단위", "#.", "구분", "FROM", "TO", "회로"]

# 을지(내역서) 컬럼 - 규격, 대표목록 제거
EULJI_COLUMNS = [
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

EULJI_COLUMN_WIDTHS = {
    "#.": 28,
    "구분": 100,
    "FROM": 60,
    "TO": 60,
    "회로": 72,
    "산출목록": 400, # 800 -> 400 (50자 이내 텍스트 기준, 1/2 축소 요청 반영)
    "산출수식": 432,
    "계": 50,
    "단위": 50,
    "비고": 75,
}

# [NEW] 산출일위표 컬럼 정의
UNIT_PRICE_COLS = {
    "MARK": 0,    # "#." (상태 마커)
    "LIST": 1,    # "산출일위목록"
    "UNIT_QTY": 2, # "단위수량"
    "UNIT_TOTAL": 3, # "단위계"
}
UNIT_PRICE_COL_NAMES = ["#.", "산출일위목록", "단위수량", "단위계"]
UNIT_PRICE_COL_WIDTHS = {
    "MARK": 35,
    "산출일위목록": 325, # ID 너비를 조금 흡수
    "단위수량": 100,
    "단위계": 75,
}

# 기초작업 을지 컬럼 (이미지 기반) - #. 및 대표목록 추가
# 기초작업 을지 컬럼 (이미지 기반) - #. 및 대표목록 추가, 검색 컬럼 삭제, 산출수량->산출수식
BASIC_WORK_COLUMNS = [
    "#.",
    "구분",
    "대표목록",
    "품목",
    "규격",
    "단위",
    "수량",
    "산출수식",
    "비고",
]

BASIC_WORK_COLUMN_WIDTHS = {
    "#.": 28,
    "구분": 100,
    "대표목록": 100,
    "품목": 180,
    "규격": 100,  # 150 -> 100 (약 30% 축소)
    "단위": 40,
    "수량": 50,
    "산출수식": 150,  # 120 -> 150 (20% 확대: 144 -> 150)
    "비고": 100,
}


# ============================================================================
# 숫자 포맷 함수
# ============================================================================


def format_number(value) -> str:
    """숫자를 천단위 구분 형식으로 변환"""
    try:
        if value is None or value == "":
            return ""

        if isinstance(value, str):
            value = value.replace(",", "").strip()
            if not value:
                return ""

        num = float(value)

        if num == int(num):
            return f"{int(num):,}"
        else:
            # 5자리까지, 소수점 사용 (trailing zero 제거)
            formatted = f"{num:,.5f}"
            return formatted.rstrip("0").rstrip(".")
    except (ValueError, TypeError):
        return str(value) if value else ""


def parse_number(text: str) -> float:
    """천단위 구분된 문자열을 숫자로 변환"""
    try:
        if not text:
            return 0
        clean = text.replace(",", "").strip()
        return float(clean)
    except (ValueError, TypeError):
        return 0


# ============================================================================
# 테이블 설정 함수
# ============================================================================


def setup_common_table(table: QTableWidget, columns: list = None, widths: dict = None):
    """공통 테이블 설정 적용 - 엑셀 스타일 무한 그리드, 컴팩트 행"""
    if columns is None:
        columns = COMMON_COLUMNS
    if widths is None:
        widths = COLUMN_WIDTHS

    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels(columns)

    # 컬럼 너비 설정
    for i, col_name in enumerate(columns):
        if col_name in widths:
            table.setColumnWidth(i, widths[col_name])

    # 기본 행 수 (무한 그리드 느낌)
    if table.rowCount() == 0:
        table.setRowCount(DEFAULT_ROWS)

    # 행 높이 설정
    header = table.verticalHeader()
    # 세로 헤더 중앙 정렬 설정
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
    # 일위대가 테이블 여부에 따라 높이 조절
    is_unit_price = False
    if columns and ("자재목록" in columns or "품목" in columns or "산출일위목록" in columns):
        is_unit_price = True

    height = UNIT_PRICE_ROW_HEIGHT if is_unit_price else DEFAULT_ROW_HEIGHT
    header.setDefaultSectionSize(height)
    header.setMinimumSectionSize(height)
    # 행 높이 고정 (사용자 조정 불가)
    header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
    
    # 세로 헤더 너비 고정 (갑지/을지 통일)
    header.setFixedWidth(45)

    # 세로 헤더 폰트 설정 (헤더는 굴림 적용)
    v_font = QFont("굴림", HEADER_FONT_SIZE)
    v_font.setStretch(100)
    header.setFont(v_font)

    # 행 번호 헤더 스타일 (헤더와 동일한 깔끔한 테두리)
    header.setStyleSheet(f"""
        QHeaderView::section {{
            background-color: #e1e1e1;
            color: black;
            padding: 2px;
            border: 1px solid #707070;
            border-top: 1px solid #ffffff;
            border-left: 1px solid #ffffff;
            border-bottom: 2px solid #606060;
            border-right: 2px solid #606060;
            border-radius: 0px;
            font-family: '굴림';
            font-size: {HEADER_FONT_SIZE}pt;
            text-align: center;
        }}
        QHeaderView::section:checked {{
            background-color: #d1d1d1;
            font-weight: normal;
        }}
    """)

    # 헤더 행 높이는 글자 크기에 맞춰 충분히 확보 (30px)
    h_header = table.horizontalHeader()
    h_header.setFixedHeight(30)
    # 가로 헤더 폰트 설정 (헤더는 굴림 적용)
    h_font = QFont("굴림", HEADER_FONT_SIZE)
    h_font.setStretch(100)
    h_header.setFont(h_font)
    # 컬럼 넓이 고정 (사용자 조정 불가)
    h_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

    # 그리드 데이터용 폰트 설정 (굴림체 적용)
    font = QFont("굴림체", int(DEFAULT_FONT_SIZE))
    font.setStretch(100)  # 장평 100%
    table.setFont(font)

    # 행 전체 선택 모드 (빨간 테두리가 행 전체에 적용)
    from PyQt6.QtWidgets import QAbstractItemView

    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)

    # 스타일 (헤더는 볼록한 블록 스타일, 폰트 0.5pt 감소)
    table.setAlternatingRowColors(False)
    table.setStyleSheet(f"""
        QTableWidget {{
            background-color: #ffffff;
            gridline-color: #999999;
            font-family: '굴림체';
            font-size: {DEFAULT_FONT_SIZE}pt;
            selection-background-color: transparent;
            outline: none;
            border: 1px solid #707070;
        }}
        QTableWidget::item {{
            background-color: transparent;
            font-family: '굴림체';
            font-size: {DEFAULT_FONT_SIZE}pt;
            padding: 2px;
            padding-left: 0px;
            margin: 0px;
            border: none;
            outline: none;
        }}
        QTableWidget::item:selected {{
            background-color: transparent;
            color: black;
            outline: none;
        }}
        QTableWidget::item:focus {{
            background-color: transparent;
            outline: none;
        }}
        QLineEdit {{
            background-color: white;
            border: 1px solid #999999;
            padding: 1px;
            padding-left: 0px;
            margin: 0px;
            height: 100%;
            font-family: '굴림체';
            font-size: {DEFAULT_FONT_SIZE}pt;
        }}
        QHeaderView::section {{
            background-color: #e1e1e1;
            color: black;
            padding: 3px;
            border: 1px solid #707070;
            border-top: 1px solid #ffffff;
            border-left: 1px solid #ffffff;
            border-bottom: 2px solid #606060;
            border-right: 2px solid #606060;
            border-radius: 0px;
            font-family: '굴림';
            font-size: {HEADER_FONT_SIZE}pt;
            font-weight: normal;
            text-align: center;
        }}
        QHeaderView::section:first {{
            border-left: 1px solid #ffffff;
        }}
    """)

    # [NEW] 파란색 잔상 원천 차단: 팔레트 하이라이트 색상을 투명화 (모든 상태 그룹 적용)
    palette = table.palette()
    transparent_color = QColor(Qt.GlobalColor.transparent)
    
    # Active, Inactive, Disabled 모든 그룹에 투명 하이라이트 적용
    for group in [QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled]:
        palette.setColor(group, QPalette.ColorRole.Highlight, transparent_color)
        palette.setColor(group, QPalette.ColorRole.HighlightedText, palette.color(group, QPalette.ColorRole.Text))
    
    table.setPalette(palette)

    # [NEW] 기본 데리게이트 설정 (전체 컬럼 파란색 잔상 방지)
    table.setItemDelegate(CleanStyleDelegate(table))

    # 포커스 테두리 완전 제거
    table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # 클립보드 핸들러 설정
    from utils.grid_clipboard import setup_clipboard_handler
    table.setMouseTracking(True)
    table.viewport().setMouseTracking(True)
    setup_clipboard_handler(table)

    # 엔터키 다음 행 이동 및 선택 하이라이트 설정
    _setup_enter_key_handler(table)
    _setup_selection_highlight(table)

    # 델리게이트 적용 (포커스 차단 로직 포함)
    setup_delegates_for_table(table, columns)


def setup_delegates_for_table(table: QTableWidget, columns: list):
    """테이블의 각 컬럼에 맞는 델리게이트 적용"""
    # 숫자 컬럼
    numeric_indices = [i for i, col in enumerate(columns) if col in NUMERIC_COLUMNS]
    if numeric_indices:
        delegate = NumericDelegate(table, numeric_indices)
        table.setItemDelegate(delegate)
        table._numeric_delegate = delegate

    # 가운데 정렬
    center_indices = [i for i, col in enumerate(columns) if col in CENTER_COLUMNS]
    if center_indices:
        c_delegate = CenterAlignmentDelegate(table, center_indices)
        for idx in center_indices:
            table.setItemDelegateForColumn(idx, c_delegate)
        table._center_delegate = c_delegate

    # 양쪽 맞춤 (요청에 따라 "구분" 컬럼에 양쪽 맞춤 적용)
    gubun_indices = [i for i, col in enumerate(columns) if col == "구분"]
    if gubun_indices:
        justified_delegate = JustifiedDelegate(table)
        for idx in gubun_indices:
            table.setItemDelegateForColumn(idx, justified_delegate)
        table._justified_delegate = justified_delegate

    # 들여쓰기 제거 (요청사항: 모든 셀 첫글자 들여쓰기 없음)
    # gongjong_indices = [i for i, col in enumerate(columns) if any(k in col for k in ["공 종 명", "공종명", "산출목록"])]
    # if gongjong_indices:
    #     padding_korean_delegate = PaddingDelegate(table, gongjong_indices, padding_left=7)
    #     for idx in gongjong_indices:
    #         table.setItemDelegateForColumn(idx, padding_korean_delegate)
    #     table._padding_korean_delegate = padding_korean_delegate

    # 일반 한글 입력
    extra_korean_indices = [i for i, col in enumerate(columns) if col == "비고"]
    if extra_korean_indices:
        korean_delegate = KoreanInputDelegate(table)
        for idx in extra_korean_indices:
            table.setItemDelegateForColumn(idx, korean_delegate)
        table._extra_korean_delegate = korean_delegate


def _setup_enter_key_handler(table: QTableWidget):
    from PyQt6.QtCore import QObject, QEvent
    class EnterKeyFilter(QObject):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                    current_row = table.currentRow()
                    current_col = table.currentColumn()
                    next_row = current_row + 1
                    if next_row >= table.rowCount():
                        table.setRowCount(next_row + 50)
                    table.setCurrentCell(next_row, current_col)
                    return True
            return super().eventFilter(obj, event)
    enter_filter = EnterKeyFilter(table)
    table.installEventFilter(enter_filter)
    table._enter_filter = enter_filter


def _setup_selection_highlight(table: QTableWidget):
    def on_selection_changed():
        v_header = table.verticalHeader()
        current_row = table.currentRow()
        if current_row >= 0 and v_header:
            v_header.setStyleSheet(f"""
                QHeaderView::section {{
                    background-color: #e1e1e1;
                    color: black;
                    padding: 2px;
                    border: 1px solid #707070;
                    border-top: 1px solid #ffffff;
                    border-left: 1px solid #ffffff;
                    border-bottom: 2px solid #606060;
                    border-right: 2px solid #606060;
                    font-family: '굴림';
                    font-size: {HEADER_FONT_SIZE}pt;
                    text-align: center;
                }}
                QHeaderView::section:checked {{
                    background-color: #d1d1d1;
                    color: black;
                    font-weight: bold;
                }}
            """)
    table.currentCellChanged.connect(on_selection_changed)
    table._selection_handler = on_selection_changed


def auto_expand_rows(table: QTableWidget, current_row: int, expansion_size: int = 100):
    if current_row >= table.rowCount() - 20:
        table.setRowCount(table.rowCount() + expansion_size)


def setup_eulji_table(table: QTableWidget):
    setup_common_table(table, EULJI_COLUMNS, EULJI_COLUMN_WIDTHS)


def set_cell_with_format(table: QTableWidget, row: int, col: int, value, columns: list = None):
    if columns is None: columns = COMMON_COLUMNS
    col_name = columns[col] if col < len(columns) else ""
    if col_name in NUMERIC_COLUMNS:
        item = QTableWidgetItem(format_number(value))
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    elif col_name == "단위":
        item = QTableWidgetItem(str(value) if value else "")
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    else:
        item = QTableWidgetItem(str(value) if value else "")
    table.setItem(row, col, item)


# ============================================================================
# 델리게이트 클래스 (파란색 잔상 제거 및 정밀 렌더링)
# ============================================================================

class BaseTableDelegate(QStyledItemDelegate):
    """모든 테이블 델리게이트의 기본 클래스 - 파란색 잔상 제거 및 빨간 테두리 직접 구현"""
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        # 1. 시스템의 모든 선택/포커스 상태를 제거하여 기본 렌더링 무력화
        option.state &= ~(QStyle.StateFlag.State_Selected | 
                         QStyle.StateFlag.State_HasFocus | 
                         QStyle.StateFlag.State_Active)
        
        # [NEW] 셀 내부 여백(Padding)을 강제로 제거하여 텍스트가 꽉 차도록 유도
        option.displayAlignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        # [FIX] 텍스트가 칸에 꽉 차도록 폰트 장평 유지 및 여백 제거 유도
        font = QFont(option.font)
        font.setStretch(100)
        option.font = font

    def paint(self, painter, option, index):
        # [NEW] Excel 스타일 고도화 선택 렌더링
        painter.save()
        
        # 1. 상태 판단
        is_selected = option.state & QStyle.StateFlag.State_Selected
        view = option.widget
        is_current = (view and index == view.currentIndex())
        
        # 2. 배경 처리
        if is_selected:
            if is_current:
                # 활성 셀은 흰색 (입력 대기 상태 강조)
                painter.fillRect(option.rect, QColor("#FFFFFF"))
            else:
                # 나머지 선택 셀은 연한 회색 (Excel 스타일)
                painter.fillRect(option.rect, QColor("#E0E0E0"))
        else:
            painter.fillRect(option.rect, option.palette.base())
            
        # 3. 기본 내용(텍스트 등) 그리기
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        super().paint(painter, opt, index)
        
        # 4. Excel 스타일 단일 영역 테두리 그리기 (#107C41 진한 녹색)
        if is_selected:
            selection_model = view.selectionModel()
            selected_indexes = selection_model.selectedIndexes()
            
            if selected_indexes:
                rows = [idx.row() for idx in selected_indexes]
                cols = [idx.column() for idx in selected_indexes]
                min_r, max_r = min(rows), max(rows)
                min_c, max_c = min(cols), max(cols)
                
                border_color = QColor("#107C41")
                
                # 상단 테두리 (2px)
                if index.row() == min_r:
                    # top()과 top()+1 픽셀 채움
                    painter.fillRect(option.rect.left(), option.rect.top(), option.rect.width(), 2, border_color)
                # 하단 테두리 (2px)
                if index.row() == max_r:
                    # bottom()-1과 bottom() 픽셀 채움
                    painter.fillRect(option.rect.left(), option.rect.bottom() - 1, option.rect.width(), 2, border_color)
                # 좌측 테두리 (2px)
                if index.column() == min_c:
                    # left()와 left()+1 픽셀 채움
                    painter.fillRect(option.rect.left(), option.rect.top(), 2, option.rect.height(), border_color)
                # 우측 테두리 (2px)
                if index.column() == max_c:
                    # right()-1과 right() 픽셀 채움
                    painter.fillRect(option.rect.right() - 1, option.rect.top(), 2, option.rect.height(), border_color)
                    
                # 5. 핸들 포인트 (우측 하단 작은 사각형)
                if index.row() == max_r and index.column() == max_c:
                    handle_size = 4
                    handle_rect = QRectF(option.rect.right() - handle_size, option.rect.bottom() - handle_size, handle_size, handle_size)
                    painter.setBrush(QColor("#107C41"))
                    painter.drawRect(handle_rect)
        
        # 6. 현재 셀(Current) 단독 선택 시 테두리 (다중 선택이 아닐 때만)
        elif is_current:
            pen = painter.pen()
            pen.setColor(QColor("#107C41"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(option.rect.adjusted(0, 0, -1, -1))

        painter.restore()


class NumericDelegate(BaseTableDelegate):
    def __init__(self, parent=None, numeric_columns: list = None):
        super().__init__(parent)
        self.numeric_column_indices = numeric_columns or []

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if option.state & QStyle.StateFlag.State_HasFocus:
            option.state &= ~QStyle.StateFlag.State_HasFocus

    def displayText(self, value, locale_):
        return format_number(value)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        if index.column() in self.numeric_column_indices:
            validator = QDoubleValidator()
            validator.setDecimals(5)
            validator.setNotation(QDoubleValidator.Notation.StandardNotation)
            editor.setValidator(validator)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.ItemDataRole.EditRole)
        if value: editor.setText(str(value).replace(",", ""))

    def setModelData(self, editor, model, index):
        value = editor.text()
        if index.column() in self.numeric_column_indices:
            model.setData(index, format_number(value), Qt.ItemDataRole.EditRole)
        else:
            model.setData(index, value, Qt.ItemDataRole.EditRole)


class PaddingDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, columns: list = None, padding_left: int = 15):
        super().__init__(parent)
        self.column_indices = columns or []
        self.padding_left = padding_left

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if option.state & QStyle.StateFlag.State_HasFocus:
            option.state &= ~QStyle.StateFlag.State_HasFocus

    def paint(self, painter, option, index):
        if option.state & QStyle.StateFlag.State_HasFocus:
            option.state &= ~QStyle.StateFlag.State_HasFocus
        if index.column() in self.column_indices:
            option.rect.setLeft(option.rect.left() + self.padding_left)
        super().paint(painter, option, index)

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setStyleSheet(f"padding-left: {self.padding_left-2}px; border: none;")
            QTimer.singleShot(0, lambda: set_korean_input_mode(editor))
        return editor


class CenterAlignmentDelegate(BaseTableDelegate):
    def __init__(self, parent=None, columns: list = None):
        super().__init__(parent)
        self.column_indices = columns or []

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if option.state & QStyle.StateFlag.State_HasFocus:
            option.state &= ~QStyle.StateFlag.State_HasFocus
        if index.column() in self.column_indices:
            option.displayAlignment = Qt.AlignmentFlag.AlignCenter

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return editor


class NoStretchDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if option.state & QStyle.StateFlag.State_HasFocus:
            option.state &= ~QStyle.StateFlag.State_HasFocus
        font = QFont(option.font)
        font.setStretch(100)
        option.font = font


class KoreanInputDelegate(BaseTableDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if option.state & QStyle.StateFlag.State_HasFocus:
            option.state &= ~QStyle.StateFlag.State_HasFocus

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            QTimer.singleShot(0, lambda: set_korean_input_mode(editor))
        return editor


def set_korean_input_mode(widget):
    widget.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
    import sys
    if sys.platform == "win32":
        try:
            import ctypes
            hwnd = widget.winId()
            if hwnd:
                imm = ctypes.WinDLL("imm32.dll")
                himc = imm.ImmGetContext(hwnd)
                if himc:
                    imm.ImmSetConversionStatus(himc, 0x0001, 0)
                    imm.ImmReleaseContext(hwnd, himc)
        except: pass


class JustifiedDelegate(BaseTableDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if option.state & QStyle.StateFlag.State_HasFocus:
            option.state &= ~QStyle.StateFlag.State_HasFocus

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            QTimer.singleShot(0, lambda: set_korean_input_mode(editor))
        return editor

    def paint(self, painter, option, index):
        # [FIX] 모든 커스텀 페인팅 로직을 제거하고 표준 렌더링으로 복구
        # 이를 통해 자간 벌어짐 문제를 해결하고 시스템 표준 서식을 보장함
        super().paint(painter, option, index)



class CleanStyleDelegate(BaseTableDelegate):
    """파란색 잔상 방지를 위해 포커스 상태를 제거하는 기본 델리게이트"""
    pass # BaseTableDelegate에서 모든 기능 구현됨
