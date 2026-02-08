# -*- coding: utf-8 -*-
"""
조각파일 매니저 (Piece File Manager)
산출일위의 선택된 데이터를 파일로 저장하고 다시 불러오는 기능을 담당함.
"""

import json
import os
from PyQt6.QtWidgets import QTableWidgetItem, QFileDialog
from PyQt6.QtCore import Qt

class PieceFileManager:
    """조각파일(.piece) 저장 및 로드 관리자"""

    @staticmethod
    def extract_selected_rows(table, columns_info):
        """
        테이블에서 선택된 행들의 데이터를 추출함.
        
        Args:
            table: QTableWidget 인스턴스
            columns_info: {필드명: 인덱스} 매핑 딕셔너리
        
        Returns:
            list: 추출된 행 데이터 리스트
        """
        selected_ranges = table.selectedRanges()
        if not selected_ranges:
            return []
        
        # 중복 방지를 위해 set 사용
        selected_rows = set()
        for r in selected_ranges:
            for row in range(r.topRow(), r.bottomRow() + 1):
                selected_rows.add(row)
        
        data = []
        for row in sorted(list(selected_rows)):
            row_dict = {}
            for field, col_idx in columns_info.items():
                item = table.item(row, col_idx)
                row_dict[field] = item.text() if item else ""
            data.append(row_dict)
            
        return data

    @staticmethod
    def save_piece_file(parent_widget, data):
        """
        추출된 데이터를 .piece 파일(JSON)로 저장함.
        """
        if not data:
            return False
            
        file_path, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "조각파일 저장 (Save Piece File)",
            os.path.expanduser("~/Documents"),
            "Piece Files (*.piece);;All Files (*)"
        )
        
        if not file_path:
            return False
            
        if not file_path.endswith('.piece'):
            file_path += '.piece'
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save piece file: {e}")
            return False

    @staticmethod
    def load_piece_file_from_path(file_path):
        """
        파일 경로에서 조각파일 데이터를 로드함.
        
        Args:
            file_path: 파일 절대 경로
            
        Returns:
            list: 데이터 리스트 또는 None (실패 시)
        """
        try:
            if not os.path.exists(file_path):
                return None
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load piece file: {e}")
            return None

    @staticmethod
    def insert_piece_data(table, data, start_row, columns_info):
        """
        조각파일 데이터를 테이블에 삽입함.
        """
        if not data:
            return False
            
        table.blockSignals(True)
        
        # 삽입할 위치 확보 (데이터 수만큼 행 추가)
        for i in range(len(data)):
            table.insertRow(start_row + i)
            
        # 데이터 입력
        for i, row_dict in enumerate(data):
            current_row = start_row + i
            for field, col_idx in columns_info.items():
                val = row_dict.get(field, "")
                item = QTableWidgetItem(str(val))
                if col_idx in [0, 1, 4]: # W, CODE, 계 중앙 정렬
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(current_row, col_idx, item)
                
        table.blockSignals(False)
        return True