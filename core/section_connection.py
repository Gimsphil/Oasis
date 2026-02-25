# -*- coding: utf-8 -*-
"""
구간접속 계산 모듈 (Section Connection)
=================================
산출수식에서 구간 수를 계산하고 접속선 산출을 자동 생성

기능:
- 구간 수 계산 (연결점 수)
- 접속선 길이 자동 산출
- Ctrl+1~9 단축키 지원
"""

from typing import Optional, Dict, Any
from utils.formula_parser import count_sections


# 접속선 기본 설정
DEFAULT_WIRE_LENGTH = 0.2  # 기본 접속선 길이 (m)
DEFAULT_CONNECTION_COUNT = 2  # 기본 접속선 수 (양쪽)


def calculate_section_connection(
    formula: str,
    wire_length: Optional[float] = None,
    connection_count: Optional[int] = None,
) -> Dict[str, Any]:
    """
    구간접속 계산

    Args:
        formula: 산출수식
        예: "2.3+3.2+5+2.3" 또는 "2.3*3+1.2"
        wire_length: 접속선 1개당 길이 (기본값: 0.2m)
        connection_count: 접속선 수 (기본값: 2개, 양쪽)

    Returns:
        dict: 계산 결과
        {
            "sections": 4,        # 구간 수
            "wire_length": 0.2,   # 접속선 1개 길이
            "connection_count": 2, # 접속선 수
            "total_length": 1.6,  # 총 접속선 길이
            "formula": "0.2*2*4"  # 계산식
        }
    """
    if wire_length is None:
        wire_length = DEFAULT_WIRE_LENGTH
    if connection_count is None:
        connection_count = DEFAULT_CONNECTION_COUNT

    # 구간 수 계산
    sections = count_sections(formula)

    # 총 길이 계산: wire_length * connection_count * sections
    total_length = wire_length * connection_count * sections

    # 계산식 생성
    formula_str = f"{wire_length}*{connection_count}*{sections}"

    return {
        "sections": sections,
        "wire_length": wire_length,
        "connection_count": connection_count,
        "total_length": total_length,
        "formula": formula_str,
    }


def create_connection_item(section_info: dict, item_prefix: str = "접속선") -> dict:
    """
    접속선 산출 항목 생성

    Args:
        section_info: calculate_section_connection() 결과
        item_prefix: 산출목록 접두사 (기본값: "접속선")

    Returns:
        dict: 을지 행 데이터
        {
            "item": "접속선",
            "formula": "0.2*2*4",
            "total": 1.6,
            "unit": "m"
        }
    """
    return {
        "item": item_prefix,
        "formula": section_info["formula"],
        "total": section_info["total_length"],
        "unit": "m",
    }


def aggregate_sections_for_connections(
    tables,
    rows: list,
    wire_length: Optional[float] = None,
    connection_count: Optional[int] = None,
) -> Dict[str, Any]:
    """
    여러 행의 구간을 합산하여 접속선 산출 (Ctrl+N용)

    Args:
        tables: 출력내역 테이블 객체
        rows: 합산할 행 번호 리스트 (예: [0, 1, 2])
        wire_length: 접속선 길이
        connection_count: 접속선 수

    Returns:
        dict: 합산 결과
    """
    if wire_length is None:
        wire_length = DEFAULT_WIRE_LENGTH
    if connection_count is None:
        connection_count = DEFAULT_CONNECTION_COUNT

    total_sections = 0

    for row in rows:
        if row < 0 or row >= tables.rowCount():
            continue

        formula_item = tables.item(row, 6)  # FORMULA 컬럼
        if not formula_item:
            continue

        formula = formula_item.text().strip()
        sections = count_sections(formula)
        total_sections += sections

    # 총 접속선 길이
    total_length = wire_length * connection_count * total_sections

    return {
        "sections": total_sections,
        "wire_length": wire_length,
        "connection_count": connection_count,
        "total_length": total_length,
        "formula": f"{wire_length}*{connection_count}*{total_sections}",
    }


# ============== 테스트 코드 ==============
if __name__ == "__main__":
    print("=" * 60)
    print("구간접속 계산 테스트")
    print("=" * 60)

    test_cases = [
        ("2.3+3.2+5+2.3", 4, 1.6, "4 sections"),
        ("2.3*3+1.2+2+4", 6, 2.4, "6 sections (*3)"),
        ("2.3+<1.5+2.3>+3", 3, 1.2, "3 sections (<> included)"),
        ("", 0, 0.0, "empty string"),
        ("3.5*4", 4, 1.6, "4 sections"),
    ]

    all_passed = True
    for i, (input_val, expected_sections, expected_total, desc) in enumerate(
        test_cases, 1
    ):
        result = calculate_section_connection(input_val)
        passed = (
            result["sections"] == expected_sections
            and abs(result["total_length"] - expected_total) < 0.01
        )
        status = "✅" if passed else "❌"

        print(f"{i:2d}. {status} {desc}")
        print(f"    입력: {repr(input_val)}")
        print(f"    구간: {result['sections']} (기대: {expected_sections})")
        print(f"    총길이: {result['total_length']}m (기대: {expected_total}m)")
        print()

        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("✅ 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
    print("=" * 60)
