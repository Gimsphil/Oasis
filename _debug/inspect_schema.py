#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""자료사전.db 스키마 검사 스크립트"""

import sqlite3
import json

db_path = r"D:\이지맥스\data\자료사전.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. 모든 테이블 확인
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = cursor.fetchall()
    
    print("=" * 80)
    print("📊 자료사전.db 스키마 검사")
    print("=" * 80)
    print(f"\n[테이블 목록] ({len(tables)} 개)\n")
    
    for table in tables:
        table_name = table[0]
        print(f"  • {table_name}")
    
    # 2. 각 테이블의 스키마 상세 조회
    print("\n" + "=" * 80)
    print("📋 테이블별 상세 스키마")
    print("=" * 80)
    
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print(f"\n[테이블: {table_name}]")
        print(f"{'컬럼명':<25} {'타입':<15} {'NOT NULL':<10} {'기본값':<15}")
        print("-" * 65)
        
        for col in columns:
            col_id, col_name, col_type, not_null, default = col[0:5]
            not_null_str = "Yes" if not_null else "No"
            default_str = str(default) if default else "None"
            print(f"{col_name:<25} {col_type:<15} {not_null_str:<10} {default_str:<15}")
        
        # 행 개수
        cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
        row_count = cursor.fetchone()[0]
        print(f"\n  → 레코드 수: {row_count}")
        
        # 샘플 데이터 (첫 2행)
        if row_count > 0:
            cursor.execute(f"SELECT * FROM [{table_name}] LIMIT 2")
            sample_rows = cursor.fetchall()
            print(f"\n  [샘플 데이터]")
            for i, row in enumerate(sample_rows, 1):
                print(f"    행{i}: {row}")
    
    # 3. "자료사전" 테이블 특별 분석
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%자료%'")
    ref_tables = cursor.fetchall()
    
    if ref_tables:
        print("\n" + "=" * 80)
        print("🔍 [자료사전] 테이블 특별 분석")
        print("=" * 80)
        
        for table in ref_tables:
            table_name = table[0]
            cursor.execute(f"SELECT DISTINCT CODE FROM [{table_name}] LIMIT 5")
            codes = cursor.fetchall()
            
            print(f"\n[테이블명: {table_name}]")
            print(f"  CODE 컬럼 샘플: {codes}")
    
    conn.close()
    print("\n" + "=" * 80)
    print("✅ 스키마 검사 완료")
    print("=" * 80)
    
except Exception as e:
    print(f"❌ 에러: {e}")
    import traceback
    traceback.print_exc()
