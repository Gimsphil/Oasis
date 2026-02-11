# -*- coding: utf-8 -*-
"""
견적 변환 모듈 (Estimate Converter)
================================
산출 데이터 → 견적 내역서 변환

기능:
- 산출 데이터 순회 → 개별 자재 분해
- 동일 자재 합산 (CODE 기준)
- 재료할증 적용
- 수량 소수점 반올림
- 일위대가 속성 자재 분리
"""

import os
import json
import sqlite3


def convert_to_estimate(eulji_data: dict, options: dict, db_path: str = None) -> dict:
    """
    산출 → 견적 변환

    Args:
        eulji_data: 산출 데이터 {"공종명": [...]}]
        options: 변환 옵션
            {
                "material_surcharge": False,
                "surcharge_rate": 10.0,
                "qty_decimal": "정수"/"1자리"/"2자리",
                "include_under_1": True,
                "floor_by_floor": False,
                "reuse_unit_price": False,
            }
        db_path: 자료사전 DB 경로

    Returns:
        dict: 견적 데이터
        {
            "공종명": [
                {"품명", "규격", "단위", "산출수량", "결정수량", "단가", "금액", "구분"}
            ]
        }
    """
    # 결과 데이터
    estimate_data = {}

    # 자료사전 로드 (단가 정보)
    db_prices = {}
    if db_path and os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT CODE, 단가 FROM materials")
            for row in cursor.fetchall():
                db_prices[row[0]] = row[1]
            conn.close()
        except Exception as e:
            print(f"[WARN] 자료사전 로드 실패: {e}")

    # 자재 유형별 구분
    manual_items = []  # 수작업 자재
    unit_price_items = []  # 일위대가 자재
    regular_items = []  # 일반 자재

    # 수량 소수점 처리 함수
    def format_qty(value: float) -> float:
        if options["qty_decimal"] == "정수":
            return round(value)
        elif options["qty_decimal"] == "1자리":
            return round(value, 1)
        else:
            return round(value, 2)

    # 1이하 처리
    def should_include(qty: float) -> bool:
        if options["include_under_1"]:
            return True
        return qty > 1

    # 모든 공종 순회
    for gongjong, items in eulji_data.items():
        if gongjong not in estimate_data:
            estimate_data[gongjong] = []

        for row in items:
            item_name = row.get("item", "").strip()
            if not item_name:
                continue

            unit = row.get("unit", "").strip()
            formula = row.get("formula", "")
            total = row.get("total", "").strip()

            # 수량 계산
            try:
                from utils.formula_parser import parse_formula

                if total:
                    qty = float(total)
                elif formula:
                    qty = parse_formula(formula)
                else:
                    qty = 0.0
            except:
                qty = 0.0

            if qty <= 0 or not should_include(qty):
                continue

            # 수량 소수점 처리
            qty = format_qty(qty)

            # 자재 유형 분류
            # "#" 또는 "@" 단위: 일위대가 또는 수량없음
            if unit in ["#", "@"]:
                if unit == "#":
                    unit_price_items.append(
                        {
                            "품명": item_name,
                            "규격": "",
                            "단위": "식",
                            "산출수량": qty,
                            "결정수량": qty,
                            "단가": 0,
                            "금액": 0,
                            "구분": "일위대가",
                        }
                    )
                continue

            # 수작업 자재 (; 포함)
            if ";" in item_name or "+" in item_name:
                manual_items.append(
                    {
                        "품명": item_name,
                        "규격": "",
                        "단위": unit,
                        "산출수량": qty,
                        "결정수량": qty,
                        "단가": 0,
                        "금액": 0,
                        "구분": "수작업",
                    }
                )
                continue

            # 일반 자재
            regular_items.append(
                {
                    "품명": item_name,
                    "규격": "",
                    "단위": unit,
                    "산출수량": qty,
                    "결정수량": qty,
                    "단가": 0,
                    "금액": 0,
                    "구분": "일반",
                }
            )

    # 동일 자재 합산 (품명+규격+단위 기준)
    def aggregate_items(items: list) -> list:
        aggregated = {}
        for item in items:
            key = (item["품명"], item["규격"], item["단위"])
            if key not in aggregated:
                aggregated[key] = item.copy()
                aggregated[key]["산출수량"] = 0
                aggregated[key]["결정수량"] = 0
            aggregated[key]["산출수량"] += item["산출수량"]
            aggregated[key]["결정수량"] = format_qty(aggregated[key]["산출수량"])

        return list(aggregated.values())

    # 합산 적용
    regular_items = aggregate_items(regular_items)
    manual_items = aggregate_items(manual_items)

    # 재료할증 적용
    if options["material_surcharge"]:
        rate = 1 + options["surcharge_rate"] / 100.0
        for item in regular_items + manual_items:
            item["결정수량"] = format_qty(item["산출수량"] * rate)

    # 결과 통합 (일반 → 수작업 → 일위대가 순)
    for gongjong, items in estimate_data.items():
        items.extend(regular_items)
        items.extend(manual_items)
        items.extend(unit_price_items)

    return estimate_data


def save_estimate_to_json(estimate_data: dict, output_path: str):
    """견적 데이터를 JSON으로 저장"""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(estimate_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] 견적 저장 실패: {e}")
        return False


# ============== 테스트 ==============
if __name__ == "__main__":
    # 테스트 데이터
    test_data = {
        "1. 전등공사": [
            {"item": "조명기구", "formula": "10", "total": "10", "unit": "개"},
            {"item": "전선 2.5sq", "formula": "100+50", "total": "150", "unit": "m"},
            {"item": "전선 3.5sq", "formula": "50", "total": "50", "unit": "m"},
        ],
        "2. 전열공사": [
            {"item": "콘센트", "formula": "20", "total": "20", "unit": "개"},
            {"item": "전선 2.5sq", "formula": "200", "total": "200", "unit": "m"},
        ],
    }

    options = {
        "material_surcharge": True,
        "surcharge_rate": 10.0,
        "qty_decimal": "정수",
        "include_under_1": True,
        "floor_by_floor": False,
        "reuse_unit_price": False,
    }

    # 변환 실행
    result = convert_to_estimate(test_data, options)

    # 결과 출력
    print("=" * 60)
    print("견적 변환 결과")
    print("=" * 60)

    for gongjong, items in result.items():
        print(f"\n[{gongjong}]")
        for item in items:
            print(
                f"  - {item['품명']}: {item['산출수량']} {item['단위']} ({item['구분']})"
            )

    # JSON 저장
    save_estimate_to_json(result, "estimate_output.json")
    print("\n✅ JSON 저장 완료: estimate_output.json")
