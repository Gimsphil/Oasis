# -*- coding: utf-8 -*-
"""
산식 검사 모듈 (Formula Checker)
============================
산출수식 오류 검사

검사 항목:
- 괄호 짝 검사
- 연속 연산자
- 빈 괄호
- 잘못된 문자열
"""

import re


def check_formula_errors(formula: str) -> list:
    """
     수식 오류 검사

     Args:
         formula: 산출수식 문자열

     Returns:
         list: 오류 목록 (빈列表이면 정상 errors = []

    )
    """
    if not formula or not formula.strip():
        return errors

    # 1. 괄호 짝 검사
    open_count = formula.count("(")
    close_count = formula.count(")")
    if open_count != close_count:
        errors.append(
            {
                "type": "괄호_불일치",
                "message": f"여는 괄호 {open_count}개, 닫는 괄호 {close_count}개 - 짝이 맞지 않음",
                "severity": "error",
            }
        )

    # 2. 빈 괄호 검사
    empty_brackets = re.findall(r"\(\s*\)", formula)
    if empty_brackets:
        errors.append(
            {
                "type": "빈_괄호",
                "message": f"빈 괄호 발견: {empty_brackets}",
                "severity": "warning",
            }
        )

    # 3. 연속 연산자 검사
    consecutive_ops = re.findall(r"[\+\-\*\/]{2,}", formula)
    if consecutive_ops:
        errors.append(
            {
                "type": "연속_연산자",
                "message": f"연속된 연산자: {consecutive_ops}",
                "severity": "warning",
            }
        )

    # 4. 연산자로 시작/끝나는지 검사
    formula_clean = re.sub(r"[\d\.\(\)\s]", "", formula)
    if formula_clean:
        # 첫 문자가 연산자
        if formula[0] in "+-*/":
            errors.append(
                {
                    "type": "시작_연산자",
                    "message": "수식이 연산자로 시작함",
                    "severity": "warning",
                }
            )
        # 마지막 문자가 연산자
        if formula[-1] in "+-*/":
            errors.append(
                {
                    "type": "끝_연산자",
                    "message": "수식이 연산자로 끝남",
                    "severity": "warning",
                }
            )

    # 5. 괄호 안에 연산자만 있는 경우
    inner_ops = re.findall(r"\(([\+\-\*\/]+)\)", formula)
    if inner_ops:
        errors.append(
            {
                "type": "괄호내_연산자만",
                "message": f"괄호 안에 연산자만 있음: {inner_ops}",
                "severity": "warning",
            }
        )

    return errors


def check_all_formulas(eulji_data: dict) -> list:
    """
    모든 공종의 산출수식 검사

    Args:
        eulji_data: {"공종명": [...]}

    Returns:
        list: [{"공종", "행", "수식", "오류": [...]}, ...]
    """
    all_errors = []

    for gongjong, items in eulji_data.items():
        for row_idx, item in enumerate(items, 1):
            formula = item.get("formula", "").strip()
            if not formula:
                continue

            errors = check_formula_errors(formula)
            if errors:
                all_errors.append(
                    {
                        "공종": gongjong,
                        "행": row_idx,
                        "수식": formula,
                        "오류": errors,
                    }
                )

    return all_errors


def format_error_summary(errors: list) -> str:
    """
    오류 목록을 문자열로 포맷팅

    Args:
        errors: check_all_formulas() 결과

    Returns:
        str: 포맷팅된 오류 메시지
    """
    if not errors:
        return "✅ 모든 수식이 정상입니다."

    lines = []
    lines.append(f"❌ 총 {len(errors)}개의 오류가 발견되었습니다.\n")

    for error in errors:
        lines.append(f"[{error['공종']} 행 {error['행']}]")
        lines.append(f"  수식: {error['수식']}")
        for err in error["오류"]:
            icon = "🚨" if err["severity"] == "error" else "⚠️"
            lines.append(f"  {icon} {err['type']}: {err['message']}")
        lines.append("")

    return "\n".join(lines)


# ============== 테스트 ==============
if __name__ == "__main__":
    print("=" * 60)
    print("산식 오류 검사 테스트")
    print("=" * 60)

    test_formulas = [
        "(3.5+2.1",  # 괄호 불일치
        "2.3+(5-3)",  # 정상
        "3++5",  # 연속 연산자
        "(  )",  # 빈 괄호
        "+3.5",  # 시작 연산자
        "3.5+",  # 끝 연산자
        "(+)",  # 괄호 내 연산자만
        "2.3+↗5+귀로",  # 문자 포함 (경고 아님)
    ]

    for formula in test_formulas:
        errors = check_formula_errors(formula)
        status = "✅ 정상" if not errors else f"❌ {len(errors)}개 오류"
        print(f"\n[{status}] {repr(formula)}")
        for err in errors:
            icon = "🚨" if err["severity"] == "error" else "⚠️"
            print(f"  {icon} {err['type']}: {err['message']}")

    print("\n" + "=" * 60)
    print("전체 검사 테스트")
    print("=" * 60)

    test_data = {
        "1. 전등공사": [
            {"formula": "(3.5+2.1", "item": "조명기구"},
            {"formula": "++5", "item": "전선"},
        ],
        "2. 전열공사": [
            {"formula": "3.5+", "item": "콘센트"},
        ],
    }

    all_errors = check_all_formulas(test_data)
    print(format_error_summary(all_errors))
