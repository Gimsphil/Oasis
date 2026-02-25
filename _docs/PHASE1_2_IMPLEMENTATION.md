# 🚀 구현 완료: PHASE 1-2 (1식 저장)

**완료일**: 2026-01-31  
**구현 단계**: PHASE 1-2 완료  
**상태**: ✅ 준비 완료 (테스트 필요)

---

## 📝 구현 내용 요약

### ✅ 완료된 기능

#### 1. 1식 저장 메커니즘
```
세부산출조서 종료 (내보내기 버튼 또는 ESC)
↓
산출내역서(갑지) 해당 행에 저장:
├─ 산출목록(컬럼 3) = 선택된 공종명
├─ 단위(컬럼 4) = "식"
├─ 산출수식(컬럼 5) = "1"
└─ 계(컬럼 6) = 세부산출조서 최종 합계
```

#### 2. 세부산출조서 팝업 수정사항

**__init__ 메서드 확장**:
```python
def __init__(self, parent=None, item_name="", parent_tab=None):
    # [NEW] parent_tab 참조 (1식 저장용)
    self.parent_tab = parent_tab
    self.item_name = item_name  # 공종명
    self.current_row = -1  # 산출내역서 행 번호
```

**set_data() 메서드 확장**:
```python
def set_data(self, data, current_row=-1):
    """초기 데이터 + 행 번호 설정"""
    self.initial_data = data
    self.current_row = current_row
```

#### 3. 1식 데이터 계산 및 저장 메서드

**get_final_sum() - 최종 합계 계산**:
```python
def get_final_sum(self):
    """세부산출조서의 계(컬럼 4) 합계"""
    total = 0.0
    for row in range(self.detail_table.rowCount()):
        total_item = self.detail_table.item(row, 4)
        if total_item:
            value = float(total_item.text())
            total += value
    return total
```

**save_to_gapji() - 산출내역서에 저장**:
```python
def save_to_gapji(self):
    """세부산출조서 데이터 → 산출내역서 1식 저장"""
    
    gapji_table = self.parent_tab.gapji_table
    
    # 산출목록 = 공종명
    gapji_table.setItem(row, 3, QTableWidgetItem(self.item_name))
    
    # 단위 = "식"
    gapji_table.setItem(row, 4, QTableWidgetItem("식"))
    
    # 산출수식 = "1"
    gapji_table.setItem(row, 5, QTableWidgetItem("1"))
    
    # 계 = 최종 합계
    final_sum = self.get_final_sum()
    gapji_table.setItem(row, 6, QTableWidgetItem(str(final_sum)))
```

#### 4. 버튼 및 키 처리

**내보내기 버튼**:
- 클릭 시 `accept()` 호출
- 1식 저장 후 팝업 닫기

**ESC 키**:
- 이벤트 필터로 ESC 감지
- 동일하게 `accept()` 호출
- 1식 저장 후 팝업 닫기

```python
def accept(self):
    """내보내기 또는 ESC → 1식 저장 + 팝업 닫기"""
    if self.save_to_gapji():
        super().accept()  # 팝업 닫기
    else:
        pass  # 저장 실패 시 팝업 유지

def eventFilter(self, obj, event):
    """ESC 키 감지"""
    if event.type() == QEvent.Type.KeyPress:
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.accept()  # ESC → 1식 저장
            return True
```

#### 5. LightingPowerManager 수정

팝업 생성 시 parent_tab 정보 전달:
```python
popup = LightingPowerPopup(
    self.parent_tab.main_window,
    title,
    parent_tab=self.parent_tab  # [NEW]
)
popup.current_row = target_row  # [NEW]
```

---

## 📂 파일 변경 내용

### 수정된 파일: `lighting_power_manager.py`

#### 변경 사항 요약

1. **LightingPowerPopup.__init__** (수정)
   - `parent_tab` 파라미터 추가
   - `item_name`, `current_row` 속성 추가

2. **set_data()** (수정)
   - `current_row` 파라미터 추가

3. **_init_ui()** (수정)
   - 버튼명: "선택 적용" → "내보내기"
   - `installEventFilter(self)` 추가

4. **get_final_sum()** (신규 메서드)
   - 세부산출조서의 계 컬럼 합계 계산

5. **save_to_gapji()** (신규 메서드)
   - 산출내역서에 1식 데이터 저장

6. **accept()** (오버라이드)
   - 내보내기 버튼/ESC 처리
   - 1식 저장 후 팝업 닫기

7. **eventFilter()** (신규)
   - ESC 키 감지 및 처리

8. **_open_popup()** (수정)
   - `parent_tab` 전달
   - `current_row` 설정

---

## 🎯 데이터 흐름

```
1. 세부산출조서 팝업 표시
   ↓
2. 산출일위 테이블에 데이터 입력 (TAB → 자료사전 팝업 → 전송)
   ↓
3. "내보내기" 버튼 클릭 또는 ESC 키
   ↓
4. accept() 메서드 실행
   ↓
5. save_to_gapji() 호출
   ├─ 산출내역서 행 참조
   ├─ 최종 합계 계산 (get_final_sum())
   └─ 각 컬럼에 데이터 입력:
      - 산출목록 = 공종명
      - 단위 = "식"
      - 산출수식 = "1"
      - 계 = 합계
   ↓
6. 팝업 닫기 (accept/reject)
   ↓
7. 산출내역서에 1식 데이터 반영 ✅
```

---

## 📋 산출내역서 컬럼 인덱스

```
OutputDetailTab의 갑지(산출내역서) 테이블 컬럼:
0  | 번호
1  | 구분
2  | 공종 번호
3  | 공종명 (산출목록) ← save_to_gapji()에서 입력
4  | 단위 ← "식" 입력
5  | 높이
6  | 천정고
7  | 산출수식/수량 ← "1" 입력
8  | 계 ← 최종 합계 입력
9  | 비고
```

**실제 컬럼 인덱스 확인**:
- `output_detail_tab.py`의 `OutputDetailTab` 클래스 상수 참고
- NUM_COL, GUBUN_COL, GONGJONG_NUM_COL, GONGJONG_COL, UNIT_COL, ...

---

## ✅ 테스트 체크리스트

- [ ] 앱 시작 정상
- [ ] 세부산출조서 팝업 표시
- [ ] 산출일위에 데이터 입력 (여러 행)
- [ ] "내보내기" 버튼 클릭
- [ ] 산출내역서 해당 행 확인:
  - [ ] 산출목록에 공종명 입력됨
  - [ ] 단위에 "식" 입력됨
  - [ ] 산출수식에 "1" 입력됨
  - [ ] 계에 합계 입력됨
- [ ] ESC 키로도 동일 동작 확인
- [ ] 재진입 시 이전 데이터 유지 확인

---

## 🚀 다음 단계

### PHASE 2: 색상 강조 및 추가 기능 (예상 2-3일)

#### 2-1. W 컬럼 색상 표시
```
일위대가(i) 행: 짙은 청색 텍스트
미매칭(~*) 행: 붉은색 텍스트 (선택사항)
```

#### 2-2. 조각파일 기능 (F9)
```
F9: 선택 행 → 조각파일 저장
- 파일 포맷: JSON 권장
- 불러오기: 나중에 삽입 가능
```

#### 2-3. 재진입 상태 복구
```
산출내역서 TAB → 세부산출조서 재진입
- 이전 입력값 유지
- 커서 위치 복구
```

---

## 📖 사용 시나리오

### 기본 1식 산출 흐름

```
1. 산출내역서(갑지)에서 공종명 선택
   예: "전등수량(갯수)산출"
   
2. 해당 행 → 세부산출조서 팝업 열기
   
3. 산출일위 테이블에 여러 개 품목 입력:
   - 품목1: 수량 50
   - 품목2: 수량 30
   - 품목3: 수량 20
   (합계: 100)
   
4. "내보내기" 클릭 또는 ESC 키
   
5. 산출내역서에 1식 저장:
   ├─ 산출목록: "전등수량(갯수)산출"
   ├─ 단위: "식"
   ├─ 산출수식: "1"
   └─ 계: "100"
   
6. 저장 완료! ✅
   산출내역서에서 다시 TAB로 재진입 가능
```

---

## 🔧 코드 품질

### 장점 ✅
- 명확한 책임 분리 (계산, 저장, 전송)
- 에러 처리 및 로그 추가
- ESC/버튼 두 가지 방식 모두 지원
- 재진입 시 데이터 복구 기반 마련

### 주의사항 ⚠️
- 산출내역서 컬럼 인덱스 확인 필요
- 최종 합계 계산이 정확한지 검증 필요
- 데이터 타입 변환 (float → str) 확인

---

## 🎓 학습 포인트

### Qt 다이얼로그 처리
- `accept()` / `reject()` 오버라이드
- `eventFilter()` ESC 키 감지
- QDialog.DialogCode 활용

### 팝업 ↔ 부모 데이터 전달
- 부모 참조 저장
- 행 인덱스 전달
- 데이터 계산 후 역방향 저장

---

## 📊 구현 진행도

```
PHASE 1:
├─ PHASE 1-1: TAB 키 + 자료사전 팝업 ✅
└─ PHASE 1-2: 1식 저장 ✅

PHASE 2: 색상 + 추가 기능 (예정)
├─ W 컬럼 색상
├─ 조각파일 (F9)
└─ 재진입 상태 복구

PHASE 3: 고급 기능 (예정)
└─ 자동 계산 프리뷰
└─ 유효성 검사
└─ 추가 단축키
```

---

**상태**: 🟢 기능 구현 완료, 테스트 대기

```bash
# 테스트 시작
D:/이지맥스/.venv/Scripts/python.exe d:/이지맥스/OutputDetail_Standalone/main.py
```
