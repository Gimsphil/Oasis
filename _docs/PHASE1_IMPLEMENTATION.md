# 🚀 구현 완료: TAB 키 이벤트 + 자료사전 팝업

**완료일**: 2026-01-31  
**구현 단계**: PHASE 1-1 완료  
**상태**: ✅ 준비 완료 (테스트 필요)

---

## 📝 구현 내용 요약

### ✅ 완료된 기능

#### 1. TAB 키 이벤트 핸들러 구현 (lighting_power_manager.py)
```python
# detail_table에 이벤트 필터 설치
self.detail_table.installEventFilter(self)

# eventFilter 메서드 확장
def eventFilter(self, source, event):
    if source == self.detail_table and event.type() == QEvent.Type.KeyPress:
        key = event.key()
        if key == Qt.Key.Key_Tab:
            self._show_reference_db_popup()  # ← 자료사전 팝업 호출
            return True
```

**특징**:
- 산출일위 테이블(detail_table)의 어느 셀에서든 TAB 키 감지
- TAB 키 입력 시 자동으로 자료사전 팝업 호출
- 기본 TAB 동작(다음 셀 이동) 차단

#### 2. 자료사전 팝업 UI 구현 (database_reference_popup.py - 새 파일)
```
[DatabaseReferencePopup 클래스]

상단 영역:
└─ 산출일위 품목 리스트 (QListWidget)
   ├─ detail_table에서 산출목록(컬럼 2) 항목 추출
   └─ 더블클릭 → active_target 설정 (수동 매칭용)

중앙 영역:
└─ 자료사전 데이터 테이블 (QTableWidget, 6컬럼)
   ├─ ID | 품목 | 규격 | 단위 | CODE | 수량
   ├─ 자료사전.db에서 데이터 로드
   ├─ 진한 녹색 텍스트 표시
   └─ 가로/세로 그리드 표시

하단 영역:
└─ 버튼 (보내기, 닫기)
```

**UI 특징**:
- 팝업 창 모양 (QDialog)
- 최소 크기: 1000 x 700
- 6개 컬럼 구성 (ID/품목/규격/단위/CODE/수량)
- 상단 품목 리스트로 수동 매칭 대상 선택 가능

#### 3. 데이터 전송 규칙 구현 (database_reference_popup.py)
```python
def _on_send_clicked(self):
    """보내기 버튼 클릭 시 자료사전 → 산출일위 데이터 전송"""
    
    # 선택된 행의 데이터 추출
    product_name = self.reference_table.item(row, 1).text()  # 품목
    qty_text = self.reference_table.item(row, 5).text()      # 수량
    code = self.reference_table.item(row, 4).text()          # CODE
    
    # 산출일위에 입력
    detail_table.setItem(row, 2, QTableWidgetItem(product_name))  # 산출목록
    detail_table.setItem(row, 3, QTableWidgetItem(qty_text))      # 단위수식
    detail_table.setItem(row, 1, QTableWidgetItem(code))          # CODE
```

**전송 규칙**:
- 자료사전.품목 → 산출일위.산출목록 (컬럼 2)
- 자료사전.수량 → 산출일위.단위수식 (컬럼 3)
- 자료사전.CODE → 산출일위.CODE (컬럼 1)
- ESC 키 또는 보내기 버튼 클릭 시 전송

#### 4. 검색 기능 구현
```python
def _search_and_navigate(self, search_text, start_row):
    """텍스트 입력 → Enter → 검색 및 행 이동"""
    # 검색 대상: 품목(1), 규격(2), CODE(4)
    # 검색 결과 행으로 자동 스크롤 이동
```

**검색 특징**:
- 수량 컬럼에 텍스트(숫자 아님) 입력 후 Enter
- 품목/규격/CODE 컬럼에서 검색
- 매칭 행으로 자동 이동

#### 5. 수동 CODE 매칭 (=== 기능)
```python
def _handle_manual_matching(self, row):
    """=== 입력 → active_target의 CODE 강제 연결"""
    if self.active_target_row is None:
        경고 표시
        return
    
    # 현재 행의 CODE → active_target 행의 CODE에 저장
    selected_code = self.reference_table.item(row, 4).text()
    detail_table.item(active_target_row, 1).setText(selected_code)
    
    # W 컬럼 재검증
    self._verify_all_codes()
```

**매칭 흐름**:
1. 상단 품목 리스트에서 대상 선택 (active_target 설정)
2. 자료사전 테이블에서 원하는 행 찾기
3. 수량 컬럼에 "===" 입력 후 Enter
4. CODE 자동 연결 + W 컬럼 업데이트

#### 6. W 컬럼 검증 표시 메서드
```python
def _verify_all_codes(self):
    """모든 행의 CODE를 자료사전과 매칭 검증"""
    
    for row in range(self.detail_table.rowCount()):
        code_val = self.detail_table.item(row, 1).text()
        
        if not code_val:
            w_status = "**"        # CODE 빈값
        elif code_val in self.reference_codes:
            w_status = "-i-" or "--"  # 매칭 성공 (일위대가 여부)
        else:
            w_status = "~i" or "~*"   # 매칭 실패
        
        self.detail_table.item(row, 0).setText(w_status)
```

**검증 규칙**:
- `**`: CODE 컬럼 빈값
- `--`: CODE 매칭 성공 (일반 품목)
- `~*`: CODE 매칭 실패 (일반 품목)
- `-i-`: CODE 매칭 성공 (일위대가)
- `~i`: CODE 매칭 실패 (일위대가)

---

## 📂 파일 변경 내용

### 수정된 파일

#### 1. `lighting_power_manager.py` (수정)
```diff
+ 155줄: detail_table.installEventFilter(self)
  
+ eventFilter 메서드 확장:
  - detail_table TAB 키 감지
  - _show_reference_db_popup() 호출
  
+ _verify_all_codes() 메서드 추가:
  - 모든 행의 CODE 검증
  - W 컬럼 자동 업데이트
  
+ _show_reference_db_popup() 메서드 추가:
  - DatabaseReferencePopup 팝업 호출
```

### 신규 파일

#### 2. `database_reference_popup.py` (신규)
```
클래스: DatabaseReferencePopup(QDialog)

메서드:
├─ __init__: 팝업 초기화
├─ _init_ui(): UI 구성
├─ _load_reference_data(): DB에서 자료사전 데이터 로드
├─ _populate_product_list(): 산출일위 품목 리스트 표시
├─ _on_product_selected(): 품목 선택 (active_target 설정)
├─ _on_table_item_changed(): 테이블 항목 변경 처리
├─ _handle_manual_matching(): === 매칭 처리
├─ _search_and_navigate(): 텍스트 검색
├─ _on_send_clicked(): 보내기 버튼 처리
└─ eventFilter(): ESC/Enter 키 처리
```

---

## 🎯 다음 단계

### PHASE 1-2: 1식 저장 (예상 1-2일)
```
세부산출조서 종료 시 (ESC/내보내기):
├─ 산출내역서 해당 행에 저장
├─ 산출목록 = 선택된 공종명
├─ 산출수식 = 1
├─ 계 = 세부산출조서 최종 합계
└─ 단위 = 식
```

### PHASE 2: 색상 강조 (예상 1일)
```
├─ 일위대가(i) 행: 짙은 청색 텍스트
├─ 미매칭(~*) 행: 붉은색 텍스트 (옵션)
└─ CODE 빈값(**) 행: 노란색 배경 (옵션)
```

### PHASE 3: 추가 기능
```
├─ 조각파일 저장/불러오기 (F9)
├─ 재진입 시 상태 복구
├─ Ctrl+S 임시 저장
└─ 추가 검증 및 경고 메시지
```

---

## ✅ 테스트 체크리스트

- [ ] 앱 시작 시 정상 로드
- [ ] 세부산출조서 팝업 표시
- [ ] 산출일위 테이블에서 TAB 키 입력
- [ ] 자료사전 팝업 호출 확인
- [ ] 팝업에 자료사전 데이터 표시됨
- [ ] 상단 품목 리스트 표시됨
- [ ] 품목 선택 (active_target 설정)
- [ ] 수량 컬럼에 숫자 입력 → 보내기 → 데이터 전송
- [ ] 수량 컬럼에 텍스트 입력 → Enter → 검색 + 행 이동
- [ ] 수량 컬럼에 === 입력 → 수동 CODE 매칭
- [ ] ESC 키 → 팝업 닫기 (보내기 동작)
- [ ] W 컬럼 자동 검증 (--/~*/등)

---

## 📖 사용 흐름

### 기본 데이터 입력 흐름
```
1. 세부산출조서 팝업 표시
2. 산출일위 테이블의 어느 셀 → TAB 키 누름
3. 자료사전 팝업 호출
4. 자료사전에서 원하는 행 선택
5. 수량 컬럼에 숫자 입력
6. 보내기 클릭 또는 ESC 키
7. 데이터 자동 전송:
   - 산출목록에 품목명 입력
   - 단위수식에 수량 입력
   - CODE 입력
8. 팝업 닫기
```

### 수동 CODE 매칭 흐름
```
1. 자료사전 팝업 상단 품목 리스트에서 대상 선택
2. 자료사전 테이블에서 원하는 행 찾기 (텍스트 검색 활용)
3. 수량 컬럼에 === 입력 후 Enter
4. CODE 자동 연결
5. W 컬럼 자동 업데이트 (--/~i/등)
```

---

## 🔧 코드 품질

### 강점 ✅
- TAB 키 이벤트 명확하게 분리
- DatabaseReferencePopup 별도 클래스로 구현
- 검색, 매칭, 전송 각각 독립적 메서드
- 예외 처리 및 디버깅 로그

### 개선 필요 ⚠️
- 일위대가 판정 기준: 현재 CODE.startswith('i')로 임시 구현
  → 실제 판정 기준 확인 필요
- 자료사전.db 테이블명 하드코딩 ([자료사전])
  → 설정 파일로 외부화 권장
- 검색 대상 컬럼(1, 2, 4) 하드코딩
  → 요구사항 명시 필요

---

## 📋 남은 미확정 사항

| 항목 | 현황 | 필요사항 |
|------|------|---------|
| 일위대가 판정 기준 | ⚠️ 임시 구현 | CODE.startswith('i') vs 다른 기준? |
| 자료사전 테이블명 | ⚠️ 하드코딩 | [자료사전] 정확한가? |
| 자료사전 컬럼 | ⚠️ 부분 확인 | ID, 품목, 규격, 단위, CODE 외 그룹/목록2~6/약칭 확인 필요 |
| 1식 저장 위치 | ❌ 미구현 | 산출내역서 어느 행에 저장할지 명시 |
| 색상 규칙 | ⚠️ 기본 구현 | 일위대가 청색/미매칭 빨강 추가 필요 |

---

**상태**: 🟢 기능 구현 완료, 테스트 대기

다음 커맨드로 테스트 시작:
```bash
D:/이지맥스/.venv/Scripts/python.exe d:/이지맥스/OutputDetail_Standalone/main.py
```
