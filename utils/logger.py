# -*- coding: utf-8 -*-
"""
OASIS 통합 로거 모듈
====================
OASIS_DEBUG=1 환경변수가 설정된 경우에만 파일/콘솔에 로그를 기록합니다.

사용법:
    from utils.logger import oasis_log, debug_enabled
    oasis_log("어떤 메시지", "tab_debug.log")  # DEBUG 모드에서만 기록
"""

import os
import datetime

# 환경변수 OASIS_DEBUG=1 이면 디버그 모드 활성화
debug_enabled: bool = os.getenv("OASIS_DEBUG", "0").strip() == "1"


def oasis_log(msg: str, log_file: str = "oasis_debug.log") -> None:
    """
    조건부 파일 로그 기록.
    OASIS_DEBUG=1 환경변수가 설정된 경우에만 동작합니다.

    Args:
        msg: 로그 메시지
        log_file: 기록할 파일명 (기본값: oasis_debug.log)
    """
    if not debug_enabled:
        return
    try:
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def oasis_print(msg: str) -> None:
    """
    조건부 콘솔 출력.
    OASIS_DEBUG=1 환경변수가 설정된 경우에만 동작합니다.
    """
    if debug_enabled:
        print(msg)
