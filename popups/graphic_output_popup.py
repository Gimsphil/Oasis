# -*- coding: utf-8 -*-
"""
Graphic Output Popup (PDF 출력기)
================================
갑지(총괄표) 및 을지(산출내역) 데이터를 ReportLab을 이용해 PDF로 출력합니다.
"""

import os
import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# Windows 맑은 고딕 또는 굴림 폰트 경로 
KOREAN_FONT_PATHS = [
    "C:/Windows/Fonts/malgun.ttf",  # 맑은 고딕
    "C:/Windows/Fonts/gulim.ttc",   # 굴림
    "C:/Windows/Fonts/batang.ttc",  # 바탕
]

def register_korean_font():
    """사용 가능한 한글 폰트를 찾아 ReportLab에 등록합니다."""
    if not REPORTLAB_AVAILABLE:
        return ""
    
    font_name = ""
    for path in KOREAN_FONT_PATHS:
        if os.path.exists(path):
            font_name = "KoreanFont"
            try:
                pdfmetrics.registerFont(TTFont(font_name, path))
                break
            except Exception:
                continue
            
    return font_name


class PDFGeneratorThread(QThread):
    """PDF 생성을 백그라운드에서 처리하는 스레드"""
    progress = pyqtSignal(int)
    log_msg = pyqtSignal(str)
    finished_success = pyqtSignal(str)
    finished_error = pyqtSignal(str)

    def __init__(self, file_path, gapji_data, eulji_data_by_gongjong):
        super().__init__()
        self.file_path = file_path
        self.gapji_data = gapji_data
        self.eulji_data_by_gongjong = eulji_data_by_gongjong

    def run(self):
        try:
            if not REPORTLAB_AVAILABLE:
                raise ImportError("reportlab 모듈이 설치되어 있지 않습니다.")

            font_name = register_korean_font()
            if not font_name:
                self.log_msg.emit("경고: 한글 폰트를 찾을 수 없습니다. 글자가 깨질 수 있습니다.")
                font_name = "Helvetica" # Fallback

            doc = SimpleDocTemplate(
                self.file_path,
                pagesize=landscape(A4),
                rightMargin=30, leftMargin=30,
                topMargin=30, bottomMargin=30
            )

            elements = []
            styles = getSampleStyleSheet()
            
            # 사용자 정의 스타일 (한글 폰트 적용)
            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Heading1'],
                fontName=font_name,
                fontSize=16,
                alignment=1, # Center
                spaceAfter=20
            )
            
            header_style = ParagraphStyle(
                'HeaderStyle',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=12,
                spaceAfter=10
            )
            
            # 1. 갑지(총괄표) 렌더링
            self.progress.emit(10)
            self.log_msg.emit("갑지(총괄표) 생성 중...")
            
            elements.append(Paragraph("내 역 총 괄 표 (갑지)", title_style))
            
            # 갑지 테이블 생성
            gapji_table_data = []
            gapji_headers = ["#. ", "구분", "공종번호", "공종명", "단위", "층고", "천정고", "수량", "비고"]
            gapji_table_data.append(gapji_headers)
            
            for row in self.gapji_data:
                gapji_table_data.append([str(c) for c in row])
                
            if len(gapji_table_data) > 1:
                t = Table(gapji_table_data, repeatRows=1)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, 0), 8),
                ]))
                elements.append(t)
            else:
                elements.append(Paragraph("갑지 데이터가 없습니다.", header_style))

            self.progress.emit(40)
            elements.append(PageBreak())

            # 2. 을지(상세산출) 렌더링
            self.log_msg.emit("을지(산출내역) 생성 중...")
            total_gongjongs = len(self.eulji_data_by_gongjong)
            
            for idx, (gongjong, rows) in enumerate(self.eulji_data_by_gongjong.items(), 1):
                elements.append(Paragraph(f"산 출 내 역 서 (을지) - {gongjong}", title_style))
                
                eulji_table_data = []
                # output_detail_tab.EULJI_COL_NAMES 참조
                eulji_headers = ["#.", "구분", "FROM", "TO", "회로", "산출목록", "산출수식", "계", "단위", "비고"]
                eulji_table_data.append(eulji_headers)
                
                for row in rows:
                    eulji_table_data.append([str(c) for c in row])
                    
                if len(eulji_table_data) > 1:
                    # 열 너비 비율 대략적 조정 (landscape A4 너비 약 842pts)
                    col_widths = [25, 50, 40, 40, 45, 200, 250, 45, 40, 50]
                    t = Table(eulji_table_data, colWidths=col_widths, repeatRows=1)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e6f0fa')),
                        ('FONTNAME', (0, 0), (-1, -1), font_name),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('ALIGN', (5, 1), (6, -1), 'LEFT'), # 산출목록, 산출수식은 좌측정렬
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ]))
                    elements.append(t)
                else:
                    elements.append(Paragraph("을지 데이터가 없습니다.", header_style))

                elements.append(PageBreak())
                self.progress.emit(40 + int(50 * (idx / max(1, total_gongjongs))))

            self.log_msg.emit("PDF 파일 빌드 중...")
            doc.build(elements)
            self.progress.emit(100)
            self.finished_success.emit(self.file_path)

        except Exception as e:
            import traceback
            err_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.finished_error.emit(err_msg)


class GraphicOutputPopup(QDialog):
    """PDF 출력 제어 다이얼로그"""

    def __init__(self, parent_tab):
        super().__init__(parent_tab.main_window)
        self.parent_tab = parent_tab
        self.setWindowTitle("PDF 산출내역 출력")
        self.setFixedSize(400, 200)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.lbl_status = QLabel("산출내역(갑지 및 을지 전체)을 PDF로 출력합니다.")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-family: '새굴림'; font-size: 10pt; margin: 10px;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        self.btn_export = QPushButton("PDF 생성 및 저장")
        self.btn_export.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 6px;")
        self.btn_cancel = QPushButton("닫기")
        self.btn_cancel.setStyleSheet("padding: 6px;")

        self.btn_export.clicked.connect(self._on_export)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _on_export(self):
        if not REPORTLAB_AVAILABLE:
            QMessageBox.critical(self, "오류", "reportlab 모듈이 설치되어 있지 않습니다.\npip install reportlab 실행 후 다시 시도해주세요.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "PDF 저장", 
            os.path.expanduser(f"~/Documents/산출내역_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"), 
            "PDF 파일 (*.pdf)"
        )

        if not file_path:
            return

        # UI에서 데이터 수집
        # 갑지 데이터
        gapji_data = []
        if self.parent_tab.gapji_table:
            table = self.parent_tab.gapji_table
            for r in range(table.rowCount()):
                row_vals = []
                has_val = False
                for c in range(table.columnCount()):
                    it = table.item(r, c)
                    val = it.text() if it else ""
                    row_vals.append(val)
                    if val.strip(): has_val = True
                if has_val:
                    gapji_data.append(row_vals)

        # 을지 데이터 수집
        # project_manager의 수집 로직 차용
        pm = getattr(self.parent_tab, "project_manager", None)
        if pm:
            eulji_data_by_gongjong = pm._gather_eulji_by_gongjong()
        else:
            eulji_data_by_gongjong = getattr(self.parent_tab, "eulji_data", {})

        self.lbl_status.setText("데이터 추출 완료. PDF 생성을 시작합니다...")
        self.btn_export.setEnabled(False)
        self.btn_cancel.setEnabled(False)

        # 스레드 시작
        self.thread = PDFGeneratorThread(file_path, gapji_data, eulji_data_by_gongjong)
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.log_msg.connect(self.lbl_status.setText)
        self.thread.finished_success.connect(self._on_success)
        self.thread.finished_error.connect(self._on_error)
        self.thread.start()

    def _on_success(self, file_path):
        self.lbl_status.setText("PDF 생성이 완료되었습니다!")
        self.btn_export.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        QMessageBox.information(self, "완료", f"PDF 파일이 저장되었습니다:\n{file_path}")
        self.accept()
        
        # Windows에서 저장된 PDF 열기 시도
        try:
            os.startfile(file_path)
        except Exception:
            pass

    def _on_error(self, err_msg):
        self.lbl_status.setText("오류가 발생했습니다.")
        self.progress_bar.setValue(0)
        self.btn_export.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        QMessageBox.critical(self, "PDF 생성 오류", err_msg)

__all__ = ["GraphicOutputPopup"]
