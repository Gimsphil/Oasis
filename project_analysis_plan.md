# OASIS SANCHUL_Sheet_1 — 전체 코드베이스 분석 및 보완 플랜

> **분석 기준일**: 2026-04-18  
> **대상 경로**: `d:\오아시스\SANCHUL_Sheet_1`

---

## 1. 프로젝트 개요

**목적**: 건설/전기 공사의 산출내역(수량산출서)을 작성하는 PyQt6 기반 데스크탑 GUI 애플리케이션  
**주요 기능**: 갑지(총괄표) + 을지(산출내역서) 관리, 자료사전 DB 연동, 산출일위표, 전등/전열 산출, 분전반 산출, 엑셀/PDF 출력, CAD 연동  
**기술 스택**: Python 3.x, PyQt6, SQLite3, openpyxl, ezdxf(선택)

---

## 2. 전체 폴더 구조 현황

```
SANCHUL_Sheet_1/
├── main.py                        ← 앱 진입점
├── output_detail_tab.py           ← 핵심 탭 컨트롤러 (1855줄, 비대)
├── lighting_power_manager.py      ← 전등/전열 매니저 (872줄)
├── distribution_board_manager.py  ← 분전반 매니저 (24줄, 미완성)
├── core/
│   ├── app_style.py               ← 폰트/QSS 스타일
│   ├── excel_exporter.py          ← 엑셀 내보내기
│   ├── cad_integration.py         ← CAD(DXF/DWG) 연동
│   ├── formula_checker.py         ← 산출수식 검사
│   ├── estimate_converter.py      ← 견적변환
│   ├── section_connection.py      ← 구간접속 산출
│   └── unit_price_trigger.py      ← 산출일위표 팝업 트리거
├── ui/
│   ├── eulji_table.py             ← 을지 테이블 위젯
│   ├── gapji_table.py             ← 갑지 테이블 위젯
│   ├── side_panel.py              ← 공종 리스트 패널
│   └── eulji_menu.py              ← 을지 카테고리 메뉴
├── managers/
│   └── event_filter.py            ← 전역 키보드 이벤트 필터 (651줄)
├── utils/
│   ├── column_settings.py         ← 컬럼/델리게이트 정의 (729줄)
│   ├── formula_parser.py          ← 산출수식 파서 (530줄)
│   ├── grid_clipboard.py          ← 그리드 클립보드
│   ├── path_config.py             ← 경로 설정
│   └── formula_parser.py          ← (중복 함수 존재)
├── popups/
│   ├── calculation_unit_price_popup.py  ← 산출일위표 팝업 (1592줄)
│   ├── database_reference_popup.py      ← 자료사전 팝업 (49KB)
│   ├── design_change_popup.py           ← 설계변경 팝업
│   ├── material_summary_popup.py        ← 소요자재 팝업
│   ├── cable_routing_popup.py           ← 간선산출 팝업
│   ├── batch_tools_popup.py             ← 일괄변경 팝업
│   ├── formula_check_popup.py           ← 산식검사 팝업
│   ├── output_board_popup.py            ← 산출판 팝업
│   ├── estimate_options_popup.py        ← 견적변환 옵션
│   └── graphic_output_popup.py          ← PDF산출 팝업 (미구현: 691바이트)
├── data/
│   ├── 자료사전.db                 ← SQLite DB (9.4MB)
│   ├── 자료사전.xlsm               ← 원본 엑셀 DB
│   ├── templates/                  ← JSON 템플릿
│   └── unit_price_chunks/          ← 행별 일위대가 JSON 조각파일
├── assets/
│   ├── fonts/                      ← 굴림/새굴림 폰트
│   └── icons/                      ← 앱 아이콘
├── _docs/                          ← 23개 내부 문서(MD)
├── _scripts/                       ← BAT/PS 스크립트(16개)
└── tests/
    └── test_path_config.py         ← 테스트 단 1개
```

---

## 3. 현재 코딩 방향성 분석

### 3.1 긍정적 측면 ✅
- **모듈화 진행 중**: `core/`, [ui/](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/lighting_power_manager.py#80-159), `managers/`, `utils/`, `popups/` 구조로 분리 시도
- **엑셀 스타일 UX**: 500행 기본 그리드, 엑셀형 선택 하이라이트, Tab 키 네비게이션
- **식 파서 완성도**: [formula_parser.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/utils/formula_parser.py)의 꺽쇠 처리, 변수 치환, 안전 eval 등 견고한 설계
- **Undo 스택**: 50개 제한의 실행취소 구현
- **델리게이트 시스템**: 파란색 잔상 제거, 엑셀형 녹색 테두리 등 정밀 렌더링

### 3.2 현재 개발 방향의 문제점 ⚠️
- **God Object 패턴**: [output_detail_tab.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/output_detail_tab.py) (1855줄)이 너무 많은 책임을 가짐
- **디버그 코드 범람**: production 코드에 파일 로그 쓰기, `[DEBUG]` print가 산재
- **미완성 모듈들**: [distribution_board_manager.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/distribution_board_manager.py)(24줄), [graphic_output_popup.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/popups/graphic_output_popup.py)(691바이트)
- **코딩 일관성 부재**: `\r\n` (CRLF) vs `\n` (LF) 혼용, 인코딩 주석 일부 누락

---

## 4. 정리/리팩터링이 필요한 부분

### 4.1 🔴 긴급 정리 — [output_detail_tab.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/output_detail_tab.py) 분리

1855줄짜리 파일이 너무 크며, 다음 로직이 혼재함:
- 갑지/을지 UI 생성 ([create_tab()](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/output_detail_tab.py#400-717))
- 데이터 저장/로드 ([_save_eulji_data](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/output_detail_tab.py#1438-1457), [_load_eulji_data](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/output_detail_tab.py#1458-1473))
- 공종 관리 ([_safe_load_gongjong](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/output_detail_tab.py#831-861), [_on_category_changed](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/output_detail_tab.py#862-866))
- 마커 업데이트, 툴바 이벤트, 팝업 호출 등

**권장 분리 방향:**
```
output_detail_tab.py
  ├── tab_ui_builder.py       ← create_tab() UI 생성만 전담
  ├── gongjong_manager.py     ← 공종 로드/저장/전환
  └── eulji_data_manager.py   ← 을지 데이터 저장/로드/마커
```

### 4.2 🔴 [formula_parser.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/utils/formula_parser.py) — 함수 중복 제거

[substitute_variables()](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/utils/formula_parser.py#345-374) 함수가 **동一 파일에 2번 정의됨** (228번째 줄, 345번째 줄).  
두 번째 정의로 첫 번째가 덮어쓰여짐 → 버그 위험.

### 4.3 🟠 디버그 코드 정리

| 파일 | 문제 |
|------|------|
| [main.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/main.py) | [DebugOutput](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/main.py#26-39) 클래스(주석처리), 하드코딩 디버그 파일 오픈, console 숨기기 주석 |
| [output_detail_tab.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/output_detail_tab.py) | [tab_debug.log](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/tab_debug.log) 모듈 레벨 파일 기록 (매 import마다 실행) |
| [managers/event_filter.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/managers/event_filter.py) | 모든 KeyPress를 파일에 기록 (성능 우려) |
| [core/unit_price_trigger.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/core/unit_price_trigger.py) | 수식 컬럼 클릭마다 [debug_trigger.log](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/debug_trigger.log) 기록 |

**해결책**: 환경변수/설정 플래그로 디버그 로그 ON/OFF 제어

### 4.4 🟠 중복 sys.path 조작 — [main.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/main.py)

모든 서브폴더를 `sys.path`에 수동 추가하는 방식은 패키지 구조상 불필요.  
대신 각 폴더에 [__init__.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/core/__init__.py)를 넣고 올바른 패키지 import를 사용해야 함.  
현재 [core/__init__.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/core/__init__.py), `ui/__init__.py`는 없거나 비어 있어 inconsistency 발생.

### 4.5 🟡 [distribution_board_manager.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/distribution_board_manager.py) — 미완성 스텁

24줄의 사실상 껍데기. [edit_row()](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/lighting_power_manager.py#838-862) 하나만 존재.  
분전반 산출 기능(팝업 연결, DB 조회)이 구현되어야 함.

### 4.6 🟡 [graphic_output_popup.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/popups/graphic_output_popup.py) — 완전 미구현

691바이트(약 20줄 수준)로 추정. PDF 산출 기능이 실질적으로 없음.

### 4.7 🟡 [excel_exporter.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/core/excel_exporter.py) — 버그 존재

[export_estimate_to_excel()](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/core/excel_exporter.py#214-294) 함수에서 `ws = wb.active` 이전에 `ws.cell()`을 참조하는 순서 오류 존재 (259~262줄에서 [ws](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/utils/column_settings.py#473-476) 미정의 상태로 사용).

### 4.8 🟡 [event_filter.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/managers/event_filter.py) — 과도한 전역 필터

`QApplication`에 이벤트 필터를 설치하여 **모든** 이벤트를 가로챔.  
모든 KeyPress를 파일에 기록하는 [_log()](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/managers/event_filter.py#27-37) 호출이 성능에 부정적 영향.

---

## 5. 수정/추가해야 할 부분

### 5.1 🔴 버그 수정

| # | 파일 | 문제 | 수정 방향 |
|---|------|------|-----------|
| 1 | [formula_parser.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/utils/formula_parser.py) | [substitute_variables()](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/utils/formula_parser.py#345-374) 중복 정의 (L228, L345) | 하나의 구현만 유지 |
| 2 | [excel_exporter.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/core/excel_exporter.py) | [export_estimate_to_excel()](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/core/excel_exporter.py#214-294)에서 [ws](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/utils/column_settings.py#473-476) 미정의 상태 `ws.cell()` 호출 | `ws = wb.active` → headers 루프 순서 교정 |
| 3 | [output_detail_tab.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/output_detail_tab.py) | `self.gongjong_category_combo.setFixedWidth(120)` 2번 연속 호출 (L564) | 중복 제거 |
| 4 | [calculation_unit_price_popup.py](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/popups/calculation_unit_price_popup.py) | [_on_piece_save_click()](file:///d:/%EC%98%A4%EC%95%84%EC%8B%9C%EC%8A%A4/SANCHUL_Sheet_1/popups/calculation_unit_price_popup.py#701-727)에서 `piece_file_manager` import → 모듈 미존재 가능성 | `piece_file_manager.py` 존재 여부 확인 및 생성 |

### 5.2 🔴 데이터 영속성 구조 개선 — 조각 파일 vs DB

현재 산출일위표 데이터가 `data/unit_price_chunks/` 폴더에 공종별 JSON 파일로 분산 저장됨.  
이 방식은 프로젝트 단위 저장/불러오기, 이름 충돌, 정리 등에서 취약.

**권장**: SQLite DB 통합 또는 단일 프로젝트 JSON 파일 방식으로 전환

### 5.3 🟠 프로젝트 저장/열기 기능 부재

현재 앱이 **프로젝트 단위 저장/열기** 기능이 없음.  
- 메뉴 "파일(F)" 버튼이 존재하지만 콜백 없음 (`callback_name=None`)
- 을지 데이터가 조각 파일에 분산되어 프로젝트 이식 불가

**추가 필요**: `파일(F)` 메뉴 구현
- 새 프로젝트
- 프로젝트 열기 (`.oasis` 또는 `.json`)
- 저장 / 다른 이름으로 저장

### 5.4 🟠 메뉴 버튼 미연결 항목 구현

| 메뉴 | 현황 |
|------|------|
| 파일(F) | 콜백 없음 |
| 편집(E) | 콜백 없음 |
| 보기(V) | 콜백 없음 |
| 도구(T) | 콜백 없음 |

### 5.5 🟠 테스트 커버리지 대폭 확대

현재 `tests/test_path_config.py` 단 1개만 존재.  
다음 단위 테스트 추가가 필요함:

```python
# 추가 권장 테스트
tests/
  test_formula_parser.py   ← parse_formula(), count_sections() 케이스
  test_column_settings.py  ← format_number(), parse_number()
  test_excel_exporter.py   ← export_to_excel() 정상/오류 케이스
  test_section_connection.py ← calculate_section_connection()
```

### 5.6 🟡 `distribution_board_manager.py` 기능 구현

```python
# 현재 (24줄 껍데기)
class DistributionBoardManager:
    def edit_row(self, row): ...  # 포커스만 이동

# 구현해야 할 기능
- show_panel()           ← 분전반 산출 팝업 표시
- _load_board_list()     ← 분전반 목록 DB/파일 로드
- _on_board_selected()   ← 분전반 선택 시 을지 연동
- save_data()            ← 분전반 데이터 저장
```

### 5.7 🟡 `graphic_output_popup.py` — PDF 출력 구현

현재 미구현. `reportlab` 또는 `PyMuPDF` 라이브러리를 활용한 PDF 산출 기능 구현 필요.

### 5.8 🟡 설정/환경변수 관리 모듈 추가

현재 경로 설정이 두 곳에 분산:
- `main.py`: `OASIS_ROOT`, `LOG_DIR` 정의
- `utils/path_config.py`: `OASIS_ROOT`, `SANCHUL_ROOT`, `CONFIG_DIR` 정의

**통합 권장**: `utils/path_config.py` 하나로 일원화하고 `main.py`에서는 import만

### 5.9 🟡 CAD 연동 UI 팝업 미완성

`core/cad_integration.py`에 `AutoCADIntegrationPopup` 클래스가 있지만  
"실제 팝업 UI는 별도 구현 필요" 주석이 존재 — UI가 없어 실질적으로 비활성 상태.

---

## 6. 아키텍처 개선 방향 (코딩 방향성)

### 6.1 단계별 리팩터링 로드맵

```
Phase A: 긴급 버그 수정 (1~2일)
  - formula_parser.py 중복 함수 제거
  - excel_exporter.py ws 순서 오류 수정
  - 중복 setFixedWidth() 제거

Phase B: 디버그 코드 정리 (2~3일)
  - 설정 기반 로그 레벨 시스템 도입
  - tab_debug.log, debug_trigger.log 조건부 기록
  - main.py DebugOutput 클래스 제거 또는 logger로 교체

Phase C: 데이터 구조 개선 (1주)
  - 단일 프로젝트 저장 포맷 설계 (.oasis JSON/SQLite)
  - 파일(F) 메뉴 구현 (새 프로젝트/열기/저장)

Phase D: 미완성 기능 구현 (2~3주)
  - distribution_board_manager.py 완성
  - graphic_output_popup.py PDF 출력 구현
  - AutoCAD 연동 UI 팝업 구현

Phase E: 대규모 리팩터링 (장기)
  - output_detail_tab.py 분리
  - sys.path 수동 조작 제거, 패키지 구조 정비
  - 테스트 커버리지 확대
```

### 6.2 권장 코딩 컨벤션

| 항목 | 현재 | 권장 |
|------|------|------|
| 줄 종결 | CRLF/LF 혼용 | LF 통일 (`.gitattributes` 설정) |
| 인코딩 선언 | 일부 파일만 `# -*- coding: utf-8 -*-` | 모든 파일 통일 |
| 로그 | print() + 파일 직접 쓰기 혼용 | `logging` 모듈 통합 |
| 임포트 | sys.path 수동 추가 | 패키지 구조 + 상대 임포트 |
| 테스트 | 파일 1개 | pytest 기반 단위 테스트 |

---

## 7. 즉시 조치 권장 항목 (우선순위별)

| 우선순위 | 항목 | 예상 작업량 |
|----------|------|-------------|
| 🔴 P1 | `formula_parser.py` 중복 함수 제거 | 10분 |
| 🔴 P1 | `excel_exporter.py` ws 순서 버그 수정 | 15분 |
| 🔴 P1 | `output_detail_tab.py` L564 중복 `setFixedWidth` 제거 | 5분 |
| 🟠 P2 | 디버그 로그 조건부 처리 (환경변수 `OASIS_DEBUG`) | 2시간 |
| 🟠 P2 | 파일(F) 메뉴 — 프로젝트 저장/열기 구현 | 1~2일 |
| 🟠 P2 | `piece_file_manager.py` 존재 확인 및 생성 | 1시간 |
| 🟡 P3 | 단위 테스트 추가 (formula_parser, column_settings) | 반나절 |
| 🟡 P3 | `distribution_board_manager.py` 기능 구현 | 3~5일 |
| 🟡 P3 | `graphic_output_popup.py` PDF 출력 구현 | 1주 |
| 🟡 P4 | `output_detail_tab.py` 분리 리팩터링 | 2~3일 |

---

## 8. 기타 발견 사항

- `_docs/` 폴더에 23개의 내부 문서(PHASE별 구현 현황, 분석 보고서 등) 존재 → 이미 상세한 개발 이력 기록이 있음. 이를 `README.md`로 통합 정리 권장.
- `_scripts/` 폴더에 `debug_run.bat`, `launch_debug.bat`, `run_main.bat` 등 다양한 실행 스크립트 존재 → `start.bat` 하나로 통합 가능.
- `자료사전.db` (9.4MB) + `자료사전.xlsm` (11.2MB) 이중 관리 → DB만 사용하도록 통합 권장.
- `data/자료사전_Rev01.xlsm` 별도 버전 파일 존재 → 버전 관리 전략 필요.
