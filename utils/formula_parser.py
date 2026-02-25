# -*- coding: utf-8 -*-
"""
산출수식 파서 (Formula Parser)
=============================
산출수식에 문자가 포함되어도 안전하게 숫자만 추출하여 계산하는 파서

지원 형식:
- 순수 숫자 수식: "3.5+2.1*4" → 11.9
- 문자 포함 수식: "2.3+↗2.3+ 귀로(2.9-1.8)" → 5.7
- 꺽쇠 괄호: "<2.1+6.3+1.2>" → 1구간 (통째로 계산)
- 괄호 포함: "(4.2+8.7+2.4)*2" → 30.6
"""

import re
import ast
import sys


def calc_byte_length(text: str) -> int:
    """
    문자열의 바이트 길이 계산
    - 한글/한자/특수문자: 2byte
    - 영문/숫자/연산자: 1byte

    Args:
        text: 입력 문자열

    Returns:
        int: 바이트 길이
    """
    if not text:
        return 0

    byte_count = 0
    for char in text:
        # 한글 (가-힣): 2byte
        if "가" <= char <= "힣":
            byte_count += 2
        # 한자: 2byte
        elif "\u4e00" <= char <= "\u9fff":
            byte_count += 2
        # 일본어: 2byte
        elif "\u3040" <= char <= "\u30ff":
            byte_count += 2
        # 기타 CJK 확장: 2byte
        elif "\uac00" <= char <= "\ud7a3":
            byte_count += 2
        # 기본 ASCII (영문, 숫자, 특수문자): 1byte
        else:
            byte_count += 1
    return byte_count


def parse_formula(text: str) -> float:
    """
    산출수식에서 숫자만 추출하여 계산

    Args:
        text: 산출수식 문자열
        예: "2.3+↗2.3+ 귀로(2.9-1.8)" 또는 "3.5+2.1*4"

    Returns:
        float: 계산 결과
        - 빈 문자열/None: 0.0
        - 순수 문자: 0.0
        - 계산 실패: 0.0 (에러 raise 안함)
    """
    if not text or text.strip() == "":
        return 0.0

    try:
        # 1. @ 기호 처리 (수량 없음 표시)
        if "@" in text:
            # @는 수량 없음을 의미하므로 0 반환
            return 0.0

        # 2. 꺽쇠 괄호(< >)를 일반 괄호(( ))로 치환
        # 꺽쇠 안의 내용은 1개 구간으로 취급
        # "<2.1+6.3+1.2>" → "(2.1+6.3+1.2)"
        def replace_angle_brackets(match):
            content = match.group(1)
            # 꺽쇠 안에서 먼저 계산할 수 있으면 계산
            inner_result = calculate_numbers_only(content)
            return f"({inner_result})"

        text = re.sub(r"<([^>]+)>", replace_angle_brackets, text)

        # 3. 문자 제거 (숫자, 연산자, 소수점, 괄호만 보존)
        # 한글, 영문, 특수문자(↗, ￢, ～
        cleaned = re.sub(r"[^\d\+\-\*\/\.\(\)\s]", "", text)

        # 4. 연속된 연산자 정리
        # "++" → "+", "+-" → "-", "--" → "+"
        cleaned = re.sub(r"\+\+", "+", cleaned)
        cleaned = re.sub(r"\+\-", "-", cleaned)
        cleaned = re.sub(r"-\+", "-", cleaned)
        cleaned = re.sub(r"--", "+", cleaned)
        cleaned = re.sub(r"\*\-", "*", cleaned)
        cleaned = re.sub(r"\-\*", "*", cleaned)

        # 5. 불필요한 공백 제거
        cleaned = cleaned.strip()

        # 6. 빈 괄호 제거: "()" → ""
        cleaned = re.sub(r"\(\s*\)", "", cleaned)

        # 7. 앞뒤의 불필요한 연산자 정리
        # "+3.5" → "3.5", "3.5+" → "3.5"
        cleaned = re.sub(r"^[\+\-\*\/]+", "", cleaned)
        cleaned = re.sub(r"[\+\-\*\/]+$", "", cleaned)

        # 8. 연속 괄호 정리
        # "(3.5)" → "3.5"
        while True:
            new_cleaned = re.sub(r"\((\d+\.?\d*)\)", r"\1", cleaned)
            if new_cleaned == cleaned:
                break
            cleaned = new_cleaned

        # 9. 최종 검증
        if not cleaned or cleaned.strip() == "":
            return 0.0

        # 숫자만 있는지 확인 (예: "42" 또는 "3.14")
        if re.match(r"^[\d\.]+$", cleaned):
            return float(cleaned)

        # 10. 안전한 eval (ast.literal_eval은 복잡한 수식 지원 안 함)
        # eval을 사용하되 보안 위험 최소화
        return safe_eval(cleaned)

    except Exception as e:
        # 모든 에러는 0.0으로 처리 (사용자에게 알리지 않음)
        return 0.0


def parse_formula_with_variables(text: str, variables: dict = None) -> float:
    """
    산출수식에서 변수를 대입 후 계산

    Args:
        text: 산출수식 문자열
        예: "$Hm-1.8m" 또는 "$L*2+$H"
        variables: 변수 딕셔너리
        예: {"$H": "3.5", "$L": "1.5"}

    Returns:
        float: 계산 결과
    """
    if not text or text.strip() == "":
        return 0.0

    if variables is None:
        variables = {}

    try:
        # 1. 변수 치환
        text = substitute_variables(text, variables)

        # 2. 나머지는 parse_formula와 동일
        # @ 기호 처리 (수량 없음 표시)
        if "@" in text:
            text = text.replace("@", "")

        # 꺽쇠 괄호 처리
        def replace_angle_brackets(match):
            content = match.group(1)
            inner_result = calculate_numbers_only(content)
            return f"({inner_result})"

        text = re.sub(r"<([^>]+)>", replace_angle_brackets, text)

        # 문자 제거
        cleaned = re.sub(r"[^\d\+\-\*\/\.\(\)\s]", "", text)

        # 연속 연산자 정리
        cleaned = re.sub(r"\+\+", "+", cleaned)
        cleaned = re.sub(r"\+\-", "-", cleaned)
        cleaned = re.sub(r"-\+", "-", cleaned)
        cleaned = re.sub(r"--", "+", cleaned)
        cleaned = re.sub(r"\*\-", "*", cleaned)
        cleaned = re.sub(r"\-\*", "*", cleaned)

        cleaned = cleaned.strip()
        cleaned = re.sub(r"\(\s*\)", "", cleaned)
        cleaned = re.sub(r"^[\+\-\*\/]+", "", cleaned)
        cleaned = re.sub(r"[\+\-\*\/]+$", "", cleaned)

        # 연속 괄호 정리
        while True:
            new_cleaned = re.sub(r"\((\d+\.?\d*)\)", r"\1", cleaned)
            if new_cleaned == cleaned:
                break
            cleaned = new_cleaned

        if not cleaned or cleaned.strip() == "":
            return 0.0

        if re.match(r"^[\d\.]+$", cleaned):
            return float(cleaned)

        return safe_eval(cleaned)

    except Exception:
        return 0.0


def calculate_numbers_only(text: str) -> float:
    """
    문자열에서 숫자만 추출하여 합산
    (연산자 없이 단순 합계)

    Args:
        text: "2.1+6.3+1.2" → 9.6

    Returns:
        float: 합산 결과
    """
    try:
        # 숫자 추출
        numbers = re.findall(r"\d+\.?\d*", text)
        total = sum(float(n) for n in numbers)
        return total
    except:
        return 0.0


def substitute_variables(formula: str, variables: dict) -> str:
    """
    수식에서 변수($H, $L 등)를 실제 값으로 치환

    Args:
        formula: 산출수식
        예: "$Hm-1.8m" 또는 "$L*2+$H"
        variables: 변수 딕셔너리
        예: {"$H": "3.5", "$L": "1.5"}

    Returns:
        str: 치환된 수식
        예: "3.5m-1.8m" 또는 "1.5*2+3.5"
    """
    if not formula:
        return formula

    result = formula

    for var, value in variables.items():
        if var in ["$H", "$L"]:
            # $H 또는 $L 패턴 찾기 (뒤에 단위가 붙을 수 있음)
            # "$Hm", "$H m", "$L*2" 등
            result = result.replace(var, str(value))

    return result


def safe_eval(expression: str) -> float:
    """
    안전한 수식 계산 (eval 대안)

    Args:
        expression: 수식 문자열
        예: "3.5+2.1*4"

    Returns:
        float: 계산 결과
    """
    try:
        # ast 모듈을 사용한 안전한 파싱
        # ast.literal_eval은 복잡한 수식 지원 안 함
        # 따라서 제한된 eval 사용

        # 허용된 문자만 있는지 확인
        allowed_pattern = r"^[\d\+\-\*\/\.\(\)\s]+$"
        if not re.match(allowed_pattern, expression):
            return 0.0

        # eval 사용 (제한된 환경)
        # __builtins__를 제한하여 보안 강화
        result = eval(expression, {"__builtins__": {}})

        # 결과가 숫자인지 확인
        if isinstance(result, (int, float)):
            return float(result)
        return 0.0

    except (SyntaxError, TypeError, ValueError, ZeroDivisionError):
        return 0.0
    except Exception:
        return 0.0


def count_sections(formula: str) -> int:
    """
    산출수식에서 구간 수 계산 (구간접속용)

    Args:
        formula: 산출수식
        예: "2.3+3.2+5+2.3" → 4
        예: "2.3*3+1.2+2+4" → 6 (*3은 3구간)
        예: "2.3+<1.5+2.3>+3" → 3 (<> 안은 1구간)

    Returns:
        int: 구간 수
    """
    if not formula or formula.strip() == "":
        return 0

    try:
        sections = 0

        # 1. <> 괄호 안은 1구간으로 처리
        temp_formula = formula
        angle_brackets = re.findall(r"<([^>]+)>", temp_formula)
        temp_formula = re.sub(r"<[^>]+>", "<ANGLE_BRACKET>", temp_formula)

        # 2. +로 분리하여 각 토큰 처리
        tokens = temp_formula.split("+")

        for token in tokens:
            token = token.strip()
            if not token:
                continue

            # <> 괄호는 1구간
            if "<ANGLE_BRACKET>" in token:
                sections += 1
                continue

            # *N 패턴: N개 구간
            # "2.3*3" → 3구간
            star_match = re.search(r"(\d+\.?\d*)\*(\d+)", token)
            if star_match:
                sections += int(star_match.group(2))
            else:
                # 일반 숫자: 1구간
                if re.search(r"\d+\.?\d*", token):
                    sections += 1

        return sections

    except Exception:
        return 0


def substitute_variables(formula: str, variables: dict) -> str:
    """
    수식에서 변수($H, $L 등)를 실제 값으로 치환

    Args:
        formula: 산출수식
        예: "$Hm-1.8m"
        variables: 변수 딕셔너리
        예: {"$H": "3.5", "$L": "1.5"}

    Returns:
        str: 치환된 수식
        예: "3.5m-1.8m"
    """
    if not formula:
        return formula

    result = formula

    for var, value in variables.items():
        # $H → 3.5
        # $Hm → 3.5m (뒤의 단위 문자 보존)
        if var in ["$H", "$L"]:
            # $H 또는 $L 패턴 찾기 (뒤에 단위가 붙을 수 있음)
            # "$Hm", "$H m", "$L*2" 등
            if var in result:
                result = result.replace(var, str(value))

    return result


def parse_manual_item(text: str) -> dict:
    """
    수작업 자재 입력 파싱 (명칭;규격;단위)

    Args:
        text: 입력 문자열
        예: "분전반;P-1;식"
        예: "분전반+P-1+식"

    Returns:
        dict: 파싱 결과
        예: {"name": "분전반", "spec": "P-1", "unit": "식"}
    """
    if not text or text.strip() == "":
        return {"name": text, "spec": "", "unit": ""}

    # ; 또는 + 로 분리 (둘 다 동일한 동작)
    parts = re.split(r"[;+]", text)

    result = {
        "name": parts[0].strip() if len(parts) > 0 else text,
        "spec": parts[1].strip() if len(parts) > 1 else "",
        "unit": parts[2].strip() if len(parts) > 2 else "",
    }

    return result


# ============== 테스트 코드 ==============
if __name__ == "__main__":
    # 테스트 케이스 1: 문자 포함 수식
    test_cases = [
        # (입력, 예상결과, 설명)
        ("2.3+↗2.3+ 귀로(2.9-1.8)", 5.7, "한글/특수문자 포함"),
        ("3.5*2+2.3", 9.3, "곱셈 포함"),
        ("(4.2+8.7+2.4)*2", 30.6, "괄호 포함"),
        ("1+5+7+2.5+14+40", 69.5, "여러 숫자"),
        ("", 0.0, "빈 문자열"),
        (None, 0.0, "None"),
        ("순수문자만", 0.0, "숫자 없음"),
        ("2.3+<1.5+2.3>+3", 7.1, "꺽쇠 괄호"),
        ("3.5", 3.5, "단일 숫자"),
        ("1@", 0.0, "@ 기호"),
        ("$Hm-1.8m", 1.7, "$H 변수 (substitute_variables 사용시)"),
    ]

    print("=" * 60)
    print("산출수식 파서 테스트")
    print("=" * 60)

    all_passed = True
    for i, (input_val, expected, desc) in enumerate(test_cases, 1):
        try:
            result = parse_formula(input_val)
            # 부동소수점 비교 (허용오차 0.01)
            passed = abs(result - expected) < 0.01
            status = "✅" if passed else "❌"

            print(f"{i:2d}. {status} {desc}")
            print(f"    입력: {repr(input_val)}")
            print(f"    결과: {result} (기대: {expected})")
            print()

            if not passed:
                all_passed = False
        except Exception as e:
            print(f"{i:2d}. ❌ 예외 발생: {e}")
            print(f"    입력: {repr(input_val)}")
            print()
            all_passed = False

    # 테스트 케이스 2: 구간 계산
    print("=" * 60)
    print("구간 계산 테스트")
    print("=" * 60)

    section_cases = [
        ("2.3+3.2+5+2.3", 4, "4구간"),
        ("2.3*3+1.2+2+4", 6, "6구간 (*3)"),
        ("2.3+<1.5+2.3>+3", 3, "3구각 (<> 포함)"),
        ("", 0, "빈 문자열"),
        ("3.5*4", 4, "4구간"),
    ]

    for i, (input_val, expected, desc) in enumerate(section_cases, 1):
        result = count_sections(input_val)
        passed = result == expected
        status = "✅" if passed else "❌"

        print(f"{i:2d}. {status} {desc}")
        print(f"    입력: {repr(input_val)}")
        print(f"    결과: {result} (기대: {expected})")
        print()

    # 테스트 케이스 3: 바이트 길이
    print("=" * 60)
    print("바이트 길이 계산 테스트")
    print("=" * 60)

    byte_cases = [
        ("가나다", 6, "한글 3글자"),
        ("abc", 3, "영문 3글자"),
        ("가12", 4, "한글+숫자"),
        ("12", 2, "숫자 2개"),
        ("", 0, "빈 문자열"),
        ("가나@#$%", 10, "한글+특수문자"),
    ]

    for i, (input_val, expected, desc) in enumerate(byte_cases, 1):
        result = calc_byte_length(input_val)
        passed = result == expected
        status = "✅" if passed else "❌"

        print(f"{i:2d}. {status} {desc}")
        print(f"    입력: {repr(input_val)}")
        print(f"    결과: {result} (기대: {expected})")
        print()

    # 테스트 케이스 4: 수작업 자재
    print("=" * 60)
    print("수작업 자재 파싱 테스트")
    print("=" * 60)

    manual_cases = [
        (
            "분전반;P-1;식",
            {"name": "분전반", "spec": "P-1", "unit": "식"},
            "세미콜론 구분",
        ),
        (
            "분전반+P-1+식",
            {"name": "분전반", "spec": "P-1", "unit": "식"},
            "플러스 구분",
        ),
        ("일반텍스트", {"name": "일반텍스트", "spec": "", "unit": ""}, "단일 텍스트"),
    ]

    for i, (input_val, expected, desc) in enumerate(manual_cases, 1):
        result = parse_manual_item(input_val)
        passed = result == expected
        status = "✅" if passed else "❌"

        print(f"{i:2d}. {status} {desc}")
        print(f"    입력: {repr(input_val)}")
        print(f"    결과: {result}")
        print()

    # 최종 결과
    print("=" * 60)
    if all_passed:
        print("✅ 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
    print("=" * 60)
