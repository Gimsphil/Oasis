# -*- coding: utf-8 -*-
"""formula_parser 단위 테스트"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from utils.formula_parser import parse_formula, calc_byte_length, count_sections


class TestParseFormula:
    def test_simple_number(self):
        assert parse_formula("5") == pytest.approx(5.0)

    def test_addition(self):
        assert parse_formula("3+2") == pytest.approx(5.0)

    def test_multiplication(self):
        assert parse_formula("2*4") == pytest.approx(8.0)

    def test_unit_stripped(self):
        """단위(m, EA 등) 제거 후 계산"""
        assert parse_formula("3m+2m") == pytest.approx(5.0)

    def test_parentheses(self):
        assert parse_formula("(2+3)*4") == pytest.approx(20.0)

    def test_empty_string(self):
        result = parse_formula("")
        assert result == 0 or result is None

    def test_invalid_expression(self):
        """비수식 문자열은 0 또는 None 반환"""
        result = parse_formula("ABC")
        assert result == 0 or result is None

    def test_at_mark(self):
        """1@ 형식은 수량 없음으로 0 處理"""
        result = parse_formula("1@")
        assert result == 0 or result is None


class TestCalcByteLength:
    def test_ascii(self):
        assert calc_byte_length("hello") == 5

    def test_korean(self):
        # 한글 1자 = 2바이트 (EUC-KR 기준)
        assert calc_byte_length("가") == 2

    def test_mixed(self):
        assert calc_byte_length("ab가나") == 2 + 4  # ascii 2 + 한글 4


class TestCountSections:
    def test_single_section(self):
        assert count_sections("3") == 1

    def test_multiple_sections(self):
        """+ 연산자 기준으로 구간 나눔"""
        assert count_sections("3+2") == 2
        assert count_sections("3+2+1") == 3
