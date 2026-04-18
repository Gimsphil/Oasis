# -*- coding: utf-8 -*-
"""
프로젝트 저장/열기 매니저
=========================
산출내역 데이터 전체(갑지, 을지, 공종, 산출일위표)를 단일 .oasis JSON 파일로
직렬화/역직렬화합니다.

사용법:
    from core.project_manager import ProjectManager
    pm = ProjectManager(tab)            # tab = OutputDetailTab 인스턴스
    pm.save_project(file_path)          # 저장
    pm.load_project(file_path)          # 열기
    pm.new_project()                    # 초기화
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional


VERSION = "1.0"  # .oasis 포맷 버전


class ProjectManager:
    """
    OASIS 프로젝트 단위 저장/불러오기를 담당하는 매니저 클래스.

    직렬화 대상:
    - 갑지(총괄표) 테이블 데이터
    - 을지(산출내역서) 테이블 데이터 (공종별)
    - 공종 목록
    - 산출일위표(unit_price_chunks) 조각 파일 데이터
    """

    def __init__(self, parent_tab):
        """
        Args:
            parent_tab: OutputDetailTab 인스턴스
        """
        self.tab = parent_tab
        self.current_file: Optional[str] = None  # 현재 열려 있는 파일 경로

    # ─────────────────────────────────────────
    # 공개 API
    # ─────────────────────────────────────────

    def new_project(self) -> None:
        """새 프로젝트: 갑지/을지 테이블 초기화 + 공종 목록 비우기."""
        tab = self.tab

        # 갑지 테이블 초기화
        if tab.gapji_table:
            tab.gapji_table.clearContents()
            tab.gapji_table.setRowCount(500)

        # 을지 테이블 초기화
        if tab.eulji_table:
            tab.eulji_table.clearContents()
            tab.eulji_table.setRowCount(500)

        # 내부 데이터 초기화
        tab.reset_internal_data()

        # 산출일위표 조각파일 세션 초기화
        tab._cleanup_unsaved_chunks()

        # 현재 파일 경로 초기화
        self.current_file = None

        # 창 제목 업데이트
        self._update_title("새 프로젝트")

    def save_project(self, file_path: str) -> bool:
        """
        현재 상태를 .oasis JSON 파일로 저장.

        Returns:
            bool: 성공 여부
        """
        try:
            data = self._gather_all_data()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.current_file = file_path
            self._update_title(Path(file_path).name)
            return True
        except Exception as e:
            print(f"[ERROR] ProjectManager.save_project: {e}")
            return False

    def load_project(self, file_path: str) -> bool:
        """
        .oasis JSON 파일에서 프로젝트 로드.

        Returns:
            bool: 성공 여부
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 포맷 버전 확인
            fmt_ver = data.get("version", "unknown")
            if fmt_ver != VERSION:
                print(f"[WARN] .oasis version mismatch: file={fmt_ver}, app={VERSION}")

            # 데이터 복원
            self._restore_all_data(data)
            self.current_file = file_path
            self._update_title(Path(file_path).name)
            return True
        except FileNotFoundError:
            print(f"[ERROR] File not found: {file_path}")
            return False
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[ERROR] ProjectManager.load_project parse error: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] ProjectManager.load_project: {e}")
            return False

    # ─────────────────────────────────────────
    # 데이터 수집 (직렬화)
    # ─────────────────────────────────────────

    def _gather_all_data(self) -> dict:
        """모든 데이터를 dict로 수집."""
        return {
            "version": VERSION,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "gongjong_list": self._gather_gongjong_list(),
            "current_gongjong": getattr(self.tab, "current_gongjong", ""),
            "gapji": self._gather_table_data(self.tab.gapji_table),
            "eulji": self._gather_eulji_by_gongjong(),
            "unit_price_chunks": self._gather_unit_price_chunks(),
        }

    def _gather_gongjong_list(self) -> list:
        """사이드 패널의 공종 목록 텍스트 리스트 반환."""
        result = []
        try:
            panel = getattr(self.tab, "gongjong_panel", None)
            if panel and hasattr(panel, "list_widget"):
                lw = panel.list_widget
                for i in range(lw.count()):
                    item = lw.item(i)
                    if item:
                        result.append(item.text())
        except Exception as e:
            print(f"[WARN] _gather_gongjong_list: {e}")
        return result

    def _gather_table_data(self, table) -> list:
        """
        QTableWidget 전체 데이터를 list[list[str]] 형태로 직렬화.
        빈 행(모든 셀이 공백)은 끝에서 제거.
        """
        if table is None:
            return []
        rows = []
        for r in range(table.rowCount()):
            row_data = []
            has_data = False
            for c in range(table.columnCount()):
                item = table.item(r, c)
                text = item.text() if item else ""
                row_data.append(text)
                if text.strip():
                    has_data = True
            if has_data:
                rows.append(row_data)
        return rows

    def _gather_eulji_by_gongjong(self) -> dict:
        """
        현재 공종과 내부 eulji_data dict를 이용해 공종별 을지 데이터 수집.
        현재 열려 있는 을지 테이블의 내용도 포함.
        """
        result = {}
        try:
            # 내부 캐시된 공종별 데이터 복사
            cached = getattr(self.tab, "eulji_data", {})
            for gongjong, rows in cached.items():
                if isinstance(rows, list):
                    result[gongjong] = rows

            # 현재 열려 있는 공종의 을지 테이블 데이터로 덮어쓰기
            current = getattr(self.tab, "current_gongjong", "")
            if current and self.tab.eulji_table:
                result[current] = self._gather_table_data(self.tab.eulji_table)
        except Exception as e:
            print(f"[WARN] _gather_eulji_by_gongjong: {e}")
        return result

    def _gather_unit_price_chunks(self) -> dict:
        """
        data/unit_price_chunks/ 폴더의 JSON 조각파일을 메모리에 병합.
        구조: {chunk_key: chunk_data_dict}
        """
        chunks = {}
        try:
            chunk_dir = os.path.join(self.tab.project_root, "data", "unit_price_chunks")
            if not os.path.isdir(chunk_dir):
                return chunks
            for dirpath, _, filenames in os.walk(chunk_dir):
                for fname in filenames:
                    if not fname.endswith(".json"):
                        continue
                    fpath = os.path.join(dirpath, fname)
                    rel = os.path.relpath(fpath, chunk_dir).replace("\\", "/")
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            chunks[rel] = json.load(f)
                    except Exception:
                        pass
        except Exception as e:
            print(f"[WARN] _gather_unit_price_chunks: {e}")
        return chunks

    # ─────────────────────────────────────────
    # 데이터 복원 (역직렬화)
    # ─────────────────────────────────────────

    def _restore_all_data(self, data: dict) -> None:
        """수집된 dict로부터 전체 데이터 복원."""
        tab = self.tab

        # 1. 내부 데이터 먼저 초기화
        tab.reset_internal_data()
        tab._cleanup_unsaved_chunks()

        # 2. 공종 목록 복원
        gongjong_list = data.get("gongjong_list", [])
        self._restore_gongjong_list(gongjong_list)

        # 3. 을지 공종별 데이터 내부 캐시에 저장
        eulji_data = data.get("eulji", {})
        tab.eulji_data = eulji_data

        # 4. 갑지 데이터 복원
        gapji_rows = data.get("gapji", [])
        self._restore_table_data(tab.gapji_table, gapji_rows)

        # 5. 산출일위표 조각파일 복원
        unit_price_chunks = data.get("unit_price_chunks", {})
        self._restore_unit_price_chunks(unit_price_chunks)

        # 6. 마지막 공종으로 전환 (을지 데이터 화면 반영)
        last_gongjong = data.get("current_gongjong", "")
        if last_gongjong and gongjong_list:
            try:
                tab._navigate_to_eulji_by_gongjong(last_gongjong)
            except AttributeError:
                # 공종 전환 메서드가 없을 경우 첫 번째 공종으로
                if gongjong_list:
                    self._activate_first_gongjong(gongjong_list)
        elif gongjong_list:
            self._activate_first_gongjong(gongjong_list)

    def _restore_gongjong_list(self, gongjong_list: list) -> None:
        """사이드 패널 공종 목록 복원."""
        try:
            panel = getattr(self.tab, "gongjong_panel", None)
            if panel and hasattr(panel, "list_widget"):
                lw = panel.list_widget
                lw.clear()
                for name in gongjong_list:
                    from PyQt6.QtWidgets import QListWidgetItem
                    lw.addItem(QListWidgetItem(name))
        except Exception as e:
            print(f"[WARN] _restore_gongjong_list: {e}")

    def _restore_table_data(self, table, rows: list) -> None:
        """list[list[str]] → QTableWidget 복원."""
        if table is None or not rows:
            return
        try:
            from PyQt6.QtWidgets import QTableWidgetItem
            needed = max(len(rows), 500)
            table.setRowCount(needed)
            for r, row_data in enumerate(rows):
                for c, text in enumerate(row_data):
                    if c < table.columnCount():
                        table.setItem(r, c, QTableWidgetItem(str(text)))
        except Exception as e:
            print(f"[WARN] _restore_table_data: {e}")

    def _restore_unit_price_chunks(self, chunks: dict) -> None:
        """chunk_key → JSON 파일 복원."""
        try:
            chunk_dir = os.path.join(self.tab.project_root, "data", "unit_price_chunks")
            for rel_path, chunk_data in chunks.items():
                abs_path = os.path.join(chunk_dir, rel_path.replace("/", os.sep))
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                with open(abs_path, "w", encoding="utf-8") as f:
                    json.dump(chunk_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] _restore_unit_price_chunks: {e}")

    def _activate_first_gongjong(self, gongjong_list: list) -> None:
        """첫 번째 공종을 활성화하여 을지 테이블 표시."""
        try:
            panel = getattr(self.tab, "gongjong_panel", None)
            if panel and hasattr(panel, "list_widget") and gongjong_list:
                panel.list_widget.setCurrentRow(0)
        except Exception as e:
            print(f"[WARN] _activate_first_gongjong: {e}")

    # ─────────────────────────────────────────
    # 유틸리티
    # ─────────────────────────────────────────

    def _update_title(self, name: str) -> None:
        """메인 창 제목 업데이트."""
        try:
            win = self.tab.main_window
            if win:
                win.setWindowTitle(f"OASIS 산출내역 — {name}")
        except Exception:
            pass
