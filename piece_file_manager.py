# -*- coding: utf-8 -*-
"""
조각파일(Piece File) 매니저
==========================
산출일위표 데이터를 .piece 파일로 저장/불러오기합니다.
calculation_unit_price_popup.py에서 '조각파일저장' / '조각파일 불러오기' 기능에 사용.
"""

import os
import json
from PyQt6.QtWidgets import QFileDialog, QMessageBox


PIECE_FILE_EXT = ".piece"
PIECE_MAGIC = "OASIS_PIECE_V1"


class PieceFileManager:
    """산출일위표 조각파일 정적 유틸리티 클래스."""

    @staticmethod
    def save_piece_file(parent_widget, data: list, default_dir: str = "") -> bool:
        """
        list[dict] 형태의 산출일위표 데이터를 .piece 파일로 저장.

        Args:
            parent_widget: 파일 다이얼로그 부모 위젯
            data: [{'MARK': .., 'LIST': .., 'QTY': .., ...}, ...]
            default_dir: 기본 저장 폴더

        Returns:
            bool: 저장 성공 여부
        """
        if not data:
            QMessageBox.information(parent_widget, "조각파일저장", "저장할 데이터가 없습니다.")
            return False

        if not default_dir:
            default_dir = os.path.expanduser("~/Documents")

        file_path, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "조각파일 저장",
            default_dir,
            f"OASIS 조각파일 (*{PIECE_FILE_EXT});;모든 파일 (*)",
        )
        if not file_path:
            return False

        if not file_path.endswith(PIECE_FILE_EXT):
            file_path += PIECE_FILE_EXT

        payload = {
            "magic": PIECE_MAGIC,
            "count": len(data),
            "data": data,
        }
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            QMessageBox.warning(parent_widget, "오류", f"저장 실패:\n{e}")
            return False

    @staticmethod
    def load_piece_file(parent_widget, default_dir: str = "") -> list:
        """
        파일 다이얼로그로 .piece 파일 선택 후 데이터 반환.

        Args:
            parent_widget: 파일 다이얼로그 부모 위젯
            default_dir: 기본 탐색 폴더

        Returns:
            list[dict]: 데이터 리스트 (실패 시 빈 리스트)
        """
        if not default_dir:
            default_dir = os.path.expanduser("~/Documents")

        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget,
            "조각파일 불러오기",
            default_dir,
            f"OASIS 조각파일 (*{PIECE_FILE_EXT});;모든 파일 (*)",
        )
        if not file_path:
            return []
        return PieceFileManager.load_piece_file_from_path(file_path)

    @staticmethod
    def load_piece_file_from_path(file_path: str) -> list:
        """
        경로에서 직접 .piece 파일 로드.

        Returns:
            list[dict]: 데이터 리스트 (실패 시 빈 리스트)
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            # magic 확인 (없거나 다르면 경고 후 계속)
            magic = payload.get("magic", "")
            if magic != PIECE_MAGIC:
                print(f"[WARN] piece file magic mismatch: {magic}")
            return payload.get("data", [])
        except FileNotFoundError:
            print(f"[ERROR] piece file not found: {file_path}")
            return []
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[ERROR] piece file parse error: {e}")
            return []
        except Exception as e:
            print(f"[ERROR] load_piece_file_from_path: {e}")
            return []
