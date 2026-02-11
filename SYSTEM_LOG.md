# 오아시스 (OASIS) 시스템 개발 로그 및 사용자 메뉴얼

이 문서는 오아시스 전기견적/산출 자동화 시스템의 주요 기능, 수정 사항 및 트러블슈팅 가이드를 기록합니다. 새로운 기능이 추가되거나 변경될 때마다 이 문서가 업데이트됩니다.

---

## 1. 최신 업데이트 (2026-02-11)

### [Phase 1 완료] 핵심 산출 기능 강화

#### 1-1. 산출수식 문자 포함 안전 파서
- **파일**: `utils/formula_parser.py` (신규)
- **기능**: 산출수식에 한글이나 특수문자가 포함되어도 숫자만 추출하여 안전하게 계산
- **지원 형식**:
  - `"2.3+↗2.3+ 귀로(2.9-1.8)"` → 5.7
  - `"3.5*2+2.3"` → 9.3
  - `"<2.1+6.3+1.2>"` → 꺽쇠 안을 1구간으로 처리
- **변경 파일**:
  - `output_detail_tab.py`: `on_eulji_cell_changed()` → `parse_formula()` 호출
  - `calculation_unit_price_popup.py`: `_evaluate_math()` → `parse_formula()` 호출

#### 1-2. 산출수식 Enter 연속입력 (40byte 자동 줄 추가)
- **파일**: `managers/event_filter.py` (수정)
- **기능**: 산출수식에서 Enter 입력 시 기존 값 뒤에 "+" 추가
- **규칙**:
  - 40byte 초과 시 다음 행으로 자동 이동
  - 다음 행에 산출목록 자동 복사
  - 연속 행의 수식은 첫 행 TOTAL에 합산
- **유틸**: `calc_byte_length()` - 한글=2byte, 영문=1byte 계산

#### 1-3. Ctrl+C/V/X 셀 복사/붙이기
- **파일**: `managers/event_filter.py` (수정), `output_detail_tab.py` (수정)
- **기능**:
  - **Ctrl+C**: NUM 열 → 행 전체 복사 / 다른 열 → 해당 셀만 복사
  - **Ctrl+V**: 시스템 클립보드 + 내부 클립보드 지원
  - **Ctrl+X**: 복사 후 삭제
- **속성**: `self._clipboard = {"type": "row"|"cell", "data": [...]}`

#### 1-4. F4 수량 없이 입력
- **파일**: `managers/event_filter.py` (수정)
- **기능**: F4 입력 시 산출수식에 `"1@"` 자동 입력
- **동작**:
  - 산출수식: `"1@"` 입력
  - 계(TOTAL): 빈 값 (수량 없음)
  - 커서: 다음 행으로 이동
- **파서 연동**: `"1@"` → 0.0 처리 (수량 계산 제외)

---

## 2. Phase 1 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `utils/formula_parser.py` | 신규 | 수식 파서 (문자 포함 지원) |
| `output_detail_tab.py` | 수정 | `on_eulji_cell_changed()` → parse_formula() |
| `popups/calculation_unit_price_popup.py` | 수정 | `_evaluate_math()` → parse_formula() |
| `managers/event_filter.py` | 수정 | Enter 연속입력, Ctrl+C/V/X, F4 |
| `output_detail_tab.py` | 수정 | `_clipboard` 속성 추가 |

---

## 3. Phase 2 완료 (2026-02-11)

### 2-1. $H/$L 변수 대입 시스템
- **파일**: `utils/formula_parser.py` (수정)
- **함수**: `substitute_variables()`, `parse_formula_with_variables()`
- **기능**:
  - `$H` → 층고 값 치환 (예: 3.5)
  - `$L` → 천정내 높이 치환 (예: 1.5)
  - `$Hm-1.8m` → `3.5m-1.8m` (단위 문자 보존)
- **용도**: 총괄표의 층고/천정 데이터를 수식에 자동 반영

### 2-2. 수작업 자재 입력
- **파일**: `utils/formula_parser.py` (수정)
- **함수**: `parse_manual_item()`
- **형식**:
  - `"분전반;P-1;식"` → `{name: "분전반", spec: "P-1", unit: "식"}`
  - `"분전반+P-1+식"` → 동일 동작 (+도 구분자로 인식)
- **제한**: ITEM 컬럼에서만 동작

### 2-3. 구간접속 자동 산출
- **파일**: `core/section_connection.py` (신규), `managers/event_filter.py` (수정)
- **함수**: `count_sections()`, `calculate_section_connection()`
- **기능**:
  - `"2.3+3.2+5+2.3"` → 4구간
  - `"2.3*3+1.2"` → 4구간 (*3은 3구간)
  - `"<1.5+2.3>+3"` → 3구간 (<> 안은 1구간)
- **단축키**: `Ctrl+1~9` → 위로 N줄의 구간 합산하여 접속선 산출
- **결과**: 접속선 산출목록, 수식 `0.2*2*4`, 총길이 1.6m

### 2-4. 기초작업 템플릿
- **파일**: `data/templates/basic_work.json` (신규), `output_detail_tab.py` (수정)
- **함수**: `load_basic_work_template()`
- **포함 항목**:
  - 조명기구 TYPE-A~D (4각BOX)
  - 조명기구 (8각BOX)
  - 직관등(수은등) 400W
  - 분전반 (수작업용/일위대가용)
  - 콘센트 (일반용)
  - 스위치 (1회로)
- **일위대가**: 조명기구당 최대 7개 세부자재 (기구, 등보강, 박스, 커버, 전선관, 콘, 전선)
- **사용법**: `load_basic_work_template()` 호출 시 자동 로드

---

## 4. Phase 2 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `utils/formula_parser.py` | 수정 | substitute_variables, parse_formula_with_variables, parse_manual_item |
| `core/section_connection.py` | 신규 | 구간접속 계산 모듈 |
| `managers/event_filter.py` | 수정 | Ctrl+1~9 핸들러 추가 |
| `output_detail_tab.py` | 수정 | load_basic_work_template, _save_unit_price_chunk |
| `data/templates/basic_work.json` | 신규 | 기초작업 템플릿 데이터 |

---

## 5. Phase 3 완료 (2026-02-11)

### 5-1. 소요자재 집계
- **파일**: `popups/material_summary_popup.py` (신규)
- **클래스**: `MaterialSummaryPopup(QDialog)`
- **기능**:
  - 전체 공종의 자재별 수량 합산
  - 품명/규격/단위별 집계
  - 정렬 및 검색
- **버튼**:
  - 새로고침: 재집계
  - 근거추적: 사용 위치 표시
  - Txt 복사: 엑셀 호환 클립보드

### 5-2. 일괄 변경 도구
- **파일**: `popups/batch_tools_popup.py` (신규)
- **클래스**: `BatchToolsPopup(QDialog)`
- **탭 구성**:
  1. **전체 목록 집계**: 공종 간 산출목록 취합
  2. **수량 증감 (%)**: 특정 자재 수량 %로 증감
  3. **재질 변경**: HI → ST 등 일괄 변경
- **기능**:
  - 확인 대화상자 표시
  -Undo 미지원 (주의 필요)

---

## 6. Phase 3 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `popups/material_summary_popup.py` | 신규 | 소요자재 집계 팝업 |
| `popups/batch_tools_popup.py` | 신규 | 일괄 변경 도구 팝업 |

---

## 7. Phase 4 완료 (2026-02-11)

### 7-1. 견적 변환 옵션 및 로직
- **파일**: `popups/estimate_options_popup.py` (신규), `core/estimate_converter.py` (신규)
- **클래스**: `EstimateOptionsPopup(QDialog)`, `EstimateConverter`
- **기능**:
  - 재료할증률 (%) 적용 (예: 10%, 15%)
  - 수량 소수점 자리수 설정 (정수/1자리/2자리)
  - 1:1 층별 견적서 생성 옵션
  - 이전 단가 재사용 설정
- **견적 변환 프로세스**:
  - 산출내역 → 공종별 취합 → 견적서 형식으로 변환
  - 재료비 자동 계산 및 할증 적용
  - 일위대가는 들여쓰기 유지

### 7-2. 엑셀 내보내기
- **파일**: `core/excel_exporter.py` (신규)
- **클래스**: `ExcelExporter`
- **기능**:
  - 총괄표 시트: 공종별 전체 내역
  - 상세내역 시트: 을지별 세부 산출
  - 서식 적용: 헤더 스타일, 테두리, 숫자 형식
  - 산출일위대: 들여쓰기 및 구분선 표시
- **옵션**:
  - 시트 구성 선택 (총괄표만 / 상세만 / 모두)
  - 날짜/프로젝트 정보 헤더 포함
  - 인쇄 영역 자동 설정

### 7-3. 산식 오류 검사
- **파일**: `core/formula_checker.py` (신규), `popups/formula_check_popup.py` (신규)
- **클래스**: `FormulaChecker`, `FormulaCheckPopup(QDialog)`
- **검사 항목**:
  - 괄호 짝 검사: `(`, `)` 매칭 확인
  - 연속 연산자: `++`, `--`, `**`, `//` 감지
  - 빈 괄호: `()` 내용물 확인
  - 잘못된 문자열: 알 수 없는 문자/기호
  - 0으로 나누기 오류 감지
- **결과 표시**:
  - 오류 위치 (행, 열)
  - 오류 유형 및 설명
  - 수정 제안

---

## 8. Phase 4 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `popups/estimate_options_popup.py` | 신규 | 견적 변환 옵션 대화상자 |
| `core/estimate_converter.py` | 신규 | 견적 변환 로직 모듈 |
| `core/excel_exporter.py` | 신규 | 엑셀 내보내기 모듈 |
| `core/formula_checker.py` | 신규 | 산식 오류 검사 로직 |
| `popups/formula_check_popup.py` | 신규 | 산식 오류 검사 팝업 |

---

## 9. Phase 5 완료 (2026-02-11)

### 9-1. 산출판 시스템
- **파일**: `popups/output_board_popup.py` (신규)
- **클래스**: `OutputBoardPopup(QDialog)`
- **기능**:
  - 산출내역 시각적 판서 형식으로 변환
  - 항목별 그룹화 및 정렬 (공종별, 규격별, 수량순)
  - 검색 및 필터 기능
  - 인쇄 및 내보내기 지원
  - 좌측: 산출판 테이블, 우측: 상세내역 표시

### 9-2. 간선 산출판
- **파일**: `popups/cable_routing_popup.py` (신규)
- **클래스**: `CableRoutingPopup(QDialog)`
- **기능**:
  - 케이블/전선 간선 경로별 정리
  - 트리 구조로 간선 경로 표시
  - 케이블 유형 필터 (전력, 통신, 접지)
  - 회로별 상세내역 표시
  - 경로 추가/인쇄/내보내기 지원

### 9-3. 설계변경
- **파일**: `popups/design_change_popup.py` (신규)
- **클래스**: `DesignChangePopup(QDialog)`
- **기능**:
  - 변경 대상 선택 (체크박스, 필터, 검색)
  - 변경 유형: 수량 일괄 변경, 규격 변경, 수량 증감률
  - 변경 사유 입력
  - 변경 미리보기 (현재↔변경후 비교)
  - 변경 이력 관리 (변경 취소Undo 지원)

---

## 10. Phase 5 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `popups/output_board_popup.py` | 신규 | 산출판 시스템 팝업 |
| `popups/cable_routing_popup.py` | 신규 | 간선 산출판 팝업 |
| `popups/design_change_popup.py` | 신규 | 설계변경 팝업 |

---

## 11. Phase 6 완료 (2026-02-11)

### 11-1. 그림산출
- **파일**: `popups/graphic_output_popup.py` (신규)
- **클래스**: `GraphicOutputPopup(QDialog)`, `DrawingGraphicsScene(QGraphicsScene)`
- **기능**:
  - 도면 이미지/DXF 파일 표시
  - 산출 항목 도면 상에서 선택 및 마킹
  - 점/영역/선 추가 모드
  - 도면 항목과 산출 항목 매핑
  - 레이어별 추출 및 자동 산출
  - 추출 항목 목록 관리 (추가/삭제/수정)
  - 메뉴 바 및 인쇄/내보내기 지원

### 11-2. AutoCAD 연동
- **파일**: `core/cad_integration.py` (신규)
- **클래스**: `CADExtractor`, `CADEntity`, `CADLayer`, `AutoCADIntegrationPopup`
- **기능**:
  - DXF/DWG 파일 열기 지원
  - 레이어별 객체 정보 추출
  - 객체 유형별 분류 (선/면/점)
  - 길이/면적 자동 계산
  - 산출 항목 자동 생성 (레이어 매핑 기반)
  - 레이어별 요약 정보 제공
- **의존성**: `ezdxf` (pip install ezdxf), `comtypes` (Windows AutoCAD)

---

## 12. Phase 6 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `popups/graphic_output_popup.py` | 신규 | 그림산출 팝업 |
| `core/cad_integration.py` | 신규 | AutoCAD 연동 모듈 |

---

## 13. 전체 변경 파일 요약

| Phase | 파일 | 유형 | 설명 |
|-------|------|------|------|
| 전역 | `UPGRADE_ROADMAP.md` | 신규 | 전체 업그레이드 로드맵 |
| Phase 1 | `utils/formula_parser.py` | 신규 | 수식 파서 (문자 포함) |
| Phase 1 | `output_detail_tab.py` | 수정 | parse_formula 적용, _clipboard |
| Phase 1 | `calculation_unit_price_popup.py` | 수정 | parse_formula 적용 |
| Phase 1-2 | `managers/event_filter.py` | 수정 | Enter/Ctrl/F4 핸들러 |
| Phase 2 | `core/section_connection.py` | 신규 | 구간접속 계산 |
| Phase 2 | `data/templates/basic_work.json` | 신규 | 기초작업 템플릿 |
| Phase 3 | `popups/material_summary_popup.py` | 신규 | 소요자재 집계 |
| Phase 3 | `popups/batch_tools_popup.py` | 신규 | 일괄 변경 도구 |
| Phase 4 | `popups/estimate_options_popup.py` | 신규 | 견적 변환 옵션 대화상자 |
| Phase 4 | `core/estimate_converter.py` | 신규 | 견적 변환 로직 모듈 |
| Phase 4 | `core/excel_exporter.py` | 신규 | 엑셀 내보내기 모듈 |
| Phase 4 | `core/formula_checker.py` | 신규 | 산식 오류 검사 로직 |
| Phase 4 | `popups/formula_check_popup.py` | 신규 | 산식 오류 검사 팝업 |
| Phase 5 | `popups/output_board_popup.py` | 신규 | 산출판 시스템 팝업 |
| Phase 5 | `popups/cable_routing_popup.py` | 신규 | 간선 산출판 팝업 |
| Phase 5 | `popups/design_change_popup.py` | 신규 | 설계변경 팝업 |
| Phase 6 | `popups/graphic_output_popup.py` | 신규 | 그림산출 팝업 |
| Phase 6 | `core/cad_integration.py` | 신규 | AutoCAD 연동 모듈 |
| 문서 | `SYSTEM_LOG.md` | 수정 | Phase 1~6 업데이트 |

---

## 15. 이전 업데이트 (2026-02-10)

### [기능 추가] 자료사전(Database Reference) 특수 명령 연동
- **기능 설명**: 자료사전의 '산출수량' 컬럼에서 숫자 외에 특수한 텍스트 명령을 입력하여 작업을 자동화할 수 있습니다.
- **상세 사양**:
    - **숫자 입력**: 산출수량으로 인식되어 부모 테이블로 전송됩니다. (예: `2`, `1+1.5+23`)
    - **`===` 입력**: 현재 선택된 데이터베이스 항목의 코드를 부모 테이블의 해당 행에 강제로 매칭시킵니다. (수동 매칭 영구 등록)
    - **텍스트 입력**: 검색어로 인식되어 하단 목록에서 일치하는 항목으로 즉시 이동(네비게이션)합니다.
- **관리 요령**: 키보드만으로 검색 -> 매칭 -> 수량 입력을 연속적으로 수행할 수 있어 입력 속도가 대폭 향상되었습니다.

### [로직 개선] 산출일위표 수량 및 수식 연동 (Multiplier)
- **기능 설명**: 산출내역서(을지)의 기본 수량과 산출일위표의 세부 수량을 배수(Multiplier) 형태로 연동합니다.
- **상세 사양**:
    - 산출일위표를 새로 열면 첫 행에 부모의 '산출목록'명이 자동 입력되고 단위수량은 `1`로 초기화됩니다.
    - 산출일위표의 모든 '단위계' 합산값이 부모 테이블의 배수가 됩니다.
    - **수식 자동 변환**: 배수가 1이 아닐 경우, 부모의 수식이 `(기존수식)*배수` (예: `(2.5)*2`) 형식으로 자동 변경됩니다.
- **주의 사항**: 수동으로 괄호를 제거하거나 수식을 수정해도 팝업을 다시 열 때 패턴을 감지하여 안전하게 복원합니다.

### [데이터 마킹] 산출일위 'i' 표시 자동화 및 조건부 적용
- **기능 설명**: 자료사전에서 데이터를 불러올 때, 해당 항목이 일위대가 세부 내역을 가질 수 있는 항목(일목)인 경우에만 마커 컬럼에 'i'를 표시합니다.
- **상세 사양**:
    - 자료사전의 **그룹(Group)** 컬럼 값이 **'일목'** (일위대가 목록)인 경우에만 행 앞에 **'i'** 표시가 생성됩니다.
    - 일반 자재나 단순 항목인 경우 마커가 표시되지 않아 데이터의 위계 구조를 한눈에 파악할 수 있습니다.
- **적용 대상**: 산출내역서(을지) 및 산출일위표 팝업 내 모든 행 삽입 시 적용.

### [텍스트 보정] 산출목록 명칭 중복 제거
- **기능 설명**: 자료사전에서 데이터를 불러올 때 명칭과 규격이 겹쳐서 출력되는 현상을 방지합니다.
- **예시**: `강제전선관 16mm` (명칭) + `16mm` (규격) -> `강제전선관 16mm` (중복 제거됨)

---

## 15. 전체 시스템 메뉴얼

### 2.1 산출내역서 (을지) 조작

| 단축키 | 기능 | 추가 버전 |
|--------|------|----------|
| F2 | 셀 편집 | 기존 |
| F3 | 산출일위표 토글 | 기존 |
| **F4** | 수량 없이 입력 (1@) | Phase 1 |
| **Ctrl+1~9** | 구간접속 자동 산출 | Phase 2 |
| Ctrl+N | 행 삽입 | 기존 |
| Ctrl+Y | 행 삭제 | 기존 |
| Ctrl+Z | 실행 취소 | 기존 |
| **Ctrl+C** | 복사 (행/셀) | Phase 1 |
| **Ctrl+V** | 붙이기 | Phase 1 |
| **Ctrl+X** | 잘라내기 | Phase 1 |
| Enter | 산출목록 → 산출일위표 포커스 이동 | 기존 |

### 2.2 산출일위표 (Unit Price Popup)
- **동작 방식**: 각 행의 단위계 합계가 메인 시트의 수량 배수로 작용합니다.
- **단위 고정**: 데이터가 존재하면 부모 테이블의 단위는 자동으로 '식'으로 변경됩니다.

### 2.3 자료사전 (Reference DB)
- **Tab (부모 테이블에서)**: '산출목록' 또는 '산출수식' 컬럼에서 누르면 자료사전이 열립니다.
- **Esc**: 입력된 모든 수량 데이터를 전송하고 창을 닫습니다.

---

## 17. 기술 참조 및 복구 가이드 (Troubleshooting)

### 에러: 수식이 제대로 계산되지 않음
- **원인**: 수식에 숫자, `+`, `-`, `*`, `/`, `.`, `(`, `)` 이외의 문자가 포함된 경우.
- **해결**: 산출수식 열의 텍스트를 확인하고 특수문자나 한글이 섞여있는지 확인하십시오. 시스템은 안전을 위해 유효한 수식만 계산합니다.

### 에러: 산출일위표 데이터 유실
- **원인**: `data/unit_price_chunks` 폴더 내의 JSON 파일이 손상되거나 삭제된 경우.
- **복구**: 프로젝트 폴더 내의 백업 파일을 확인하거나, 해당 폴더의 파일 구조가 `공종명_행번호.json` 형태인지 확인하십시오.

## 18. 전문 지식: 일위대가(一位代價)의 이해

### 4.1 일위대가의 정의
일위대가는 어떤 공사를 **“1단위(1m, 1개, 1㎡, 1식 등)”** 수행하는 데 필요한 비용을, 그 공사를 구성하는 재료비·노무비·경비(필요 시 장비/운반/가공/손료 등)를 **세부 항목(수량×단가)**으로 쪼개서 산출 근거까지 포함해 만든 단가(내역) 체계입니다.
즉, “한 단위를 만들기 위한 재료·인력·장비가 무엇이고 얼마나 들어가는지”를 표준화/근거화한 것입니다.

### 4.2 일위대가가 왜 필요한가
1. **단가의 근거 제공**: 왜 이 금액인지 객관적으로 설명 가능합니다.
2. **변경 대응 용이**: 설계 변경이나 물량 변경 시 어느 재료나 인력이 변하는지 영향 분석이 쉽습니다.
3. **비교 분석**: 업체, 현장, 연도별 단가 차이를 비교하기 좋습니다.
4. **표준화**: 공종(전기/통신/소방/건축)별로 표준화된 산정 방식을 구축할 수 있습니다.

### 4.3 기본 구성 요소
- **단위(Unit)**: m, ㎡, 개, 본, 식 등
- **구성 항목(BOM)**:
    - **재료비**: 케이블, 배관, 박스, 콘크리트 등 직접 소요 자재
    - **노무비**: 전공, 조공 등 직종별 투입 인원(인·시간 또는 인·일)
    - **경비**: 장비손료, 소모품, 가설비 등
- **산출근거**: 여유율, 절단손실, 부속 반영 비율 등 수량 산출의 이유

### 4.4 공종별 예시 개념
- **전기**: "전선관 1m 설치"를 위해 전선관 1.0m + 커플링 + 새들 + 전공/조공 노무량을 합산.
- **통신**: "UTP 케이블 1m 포설"을 위해 케이블 + 여유율 + 라벨 + 통신 전문 인력 노무량 합산.
- **소방**: "감지기 1개 설치"를 위해 감지기 본체 + 베이스 + 결선 노무량 + 시험측정 경비 합산.
- **건축**: "콘크리트 타설 1㎥"를 위해 레미콘 + 타설 인력 + 펌프카 장비비 합산.

---

*본 문서는 AI 어시스턴트 Antigravity에 의해 관리되며, 모든 주요 변경 사항은 여기에 기록됩니다.*
