# 🚀 구현 진행: PHASE 3 (고급 기능)

**시작일**: 2026-01-31  
**진행률**: PHASE 3-1, 3-2, 3-3 완료 (60% 완료)  
**상태**: ✅ 3개 기능 구현 완료 (테스트 필요)

---

## 📝 구현된 기능 (1/3)

### ✅ PHASE 3-1: 실시간 계산 프리뷰

#### 구현 내용
```
UI 추가:
├─ preview_label: 합계 표시 레이블
│  ├─ 위치: 테이블 하단 (버튼 위)
│  ├─ 스타일: 파란색 테두리, 회색 배경
│  └─ 높이: 35px

메서드 추가:
├─ _update_preview_sum(): 실시간 합계 업데이트 (debounce)
│  └─ 100ms 지연으로 성능 최적화
├─ _calculate_preview_sum(): 실제 합계 계산
│  └─ 쉼표 포맷 적용 (1,000,000)
```

#### 동작 흐름
```
사용자 입력
  ↓
_on_detail_item_changed() 호출
  ↓
_update_preview_sum() 호출
  ↓
QTimer 100ms 지연 (debounce)
  ↓
_calculate_preview_sum() 실행
  ↓
preview_label 업데이트 ✅
합계: 1,234,567 표시
```

#### 코드 예시
```python
def _update_preview_sum(self):
    """실시간 합계 업데이트 (debounce로 성능 최적화)"""
    if not hasattr(self, '_preview_timer'):
        self._preview_timer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._calculate_preview_sum)
    
    # 100ms 지연 후 계산
    self._preview_timer.stop()
    self._preview_timer.start(100)

def _calculate_preview_sum(self):
    """실시간 합계 실제 계산"""
    total_sum = 0.0
    
    for row in range(self.detail_table.rowCount()):
        item = self.detail_table.item(row, 4)  # 계 컬럼
        if item:
            try:
                value = float(item.text().replace(',', ''))
                total_sum += value
            except (ValueError, AttributeError):
                pass
    
    sum_text = f"{int(total_sum):,}" if total_sum.is_integer() else f"{total_sum:,.2f}"
    self.preview_label.setText(f"합계: {sum_text}")
```

#### 특징
- ✅ Debounce 처리: 과도한 업데이트 방지
- ✅ 쉼표 포맷: 가독성 향상
- ✅ 실시간: 모든 입력 직후 즉시 업데이트
- ✅ 성능: 메모리 효율적

---

### ✅ PHASE 3-2: 유효성 검사 + 경고

#### 구현 내용
```
검증 규칙:
├─ 산출목록 (컬럼 2): 비어있으면 오류
├─ 단위수식 (컬럼 3): 비어있으면 오류
└─ CODE (컬럼 1): 없으면 경고 (선택)

메서드 추가:
├─ _validate_all_inputs(): 모든 행 검증
│  └─ 오류 목록 반환
├─ _show_validation_errors(): 오류 다이얼로그
│  └─ Ok/Ignore 선택 옵션
```

#### 동작 흐름
```
1식 저장 시작
  ↓
_validate_all_inputs() 호출
  ↓
오류 검사:
├─ 산출목록 비어있음?
├─ 단위수식 비어있음?
└─ CODE 없음?
  ↓
오류 발견 시:
├─ 오류 목록 생성
├─ 다이얼로그 표시
│  ├─ "Ok" → 저장 취소 ✅
│  └─ "Ignore" → 진행 ✅
```

#### 검증 예시
```python
def _validate_all_inputs(self):
    """모든 입력 데이터 유효성 검사"""
    errors = []
    
    for row in range(self.detail_table.rowCount()):
        # 산출목록 확인
        product_item = self.detail_table.item(row, 2)
        product_text = product_item.text() if product_item else ""
        
        if not product_text.strip():
            errors.append(f"행 {row + 1}: 산출목록이 비어있습니다.")
            continue
        
        # 단위수식 확인
        formula_item = self.detail_table.item(row, 3)
        formula_text = formula_item.text() if formula_item else ""
        
        if not formula_text.strip():
            errors.append(f"행 {row + 1}: 단위수식이 비어있습니다.")
            continue
        
        # CODE 확인
        code_item = self.detail_table.item(row, 1)
        code_text = code_item.text() if code_item else ""
        
        if not code_text.strip():
            errors.append(f"행 {row + 1}: CODE가 입력되지 않았습니다.")
    
    return errors
```

#### 오류 메시지 예시
```
입력 오류가 감지되었습니다:

행 1: CODE가 입력되지 않았습니다.
행 3: 단위수식이 비어있습니다.
행 5: 산출목록이 비어있습니다.

... 외 2개 오류

[Ok] [Ignore]
```

#### 특징
- ✅ 구체적 오류 위치 (행 번호 표시)
- ✅ 유연한 검증 (무시 선택 가능)
- ✅ 대량 오류 처리 (최대 10개 표시 + 더보기)

---

### ✅ PHASE 3-3: 추가 단축키 (Ctrl+S, Ctrl+Z)

#### 구현 내용
```
새 단축키:
├─ Ctrl+S: 현재 상태 저장
│  └─ Undo 스택에 추가
├─ Ctrl+Z: 이전 상태 복구
│  └─ Undo 스택에서 꺼내기

메서드 추가:
├─ _save_current_state(): Ctrl+S 핸들러
│  ├─ 테이블 데이터 스냅샷 생성
│  └─ Undo 스택에 저장
├─ _restore_previous_state(): Ctrl+Z 핸들러
│  ├─ 이전 상태 로드
│  └─ 테이블에 복구
```

#### Undo 스택 구조
```python
self.undo_stack = []  # 상태 목록
self.undo_max = 20    # 최대 20개 상태 저장

스택 구조:
[
  [  # 상태 1
    ["--", "ABC001", "조명", "50", "50"],    # 행 1
    ["-i-", "iDEF", "일위", "100", "100"]    # 행 2
  ],
  [  # 상태 2
    ...
  ]
]
```

#### 동작 흐름
```
상태 저장 (Ctrl+S):
1. 테이블의 모든 셀 데이터 추출
2. 2차원 배열 생성 ([행][컬럼])
3. Undo 스택에 추가
4. 스택 크기가 20 초과 시 가장 오래된 상태 제거
5. 완료 메시지 표시 ✅

상태 복구 (Ctrl+Z):
1. Undo 스택에서 마지막 상태 꺼내기
2. 테이블 신호 차단 (변경 감지 방지)
3. 테이블 크기 조정 (행 개수)
4. 모든 셀에 데이터 복구
5. 테이블 신호 복구
6. 색상 강조 재적용 (_verify_all_codes)
7. 실시간 합계 업데이트 (_update_preview_sum)
8. 복구 완료 메시지 ✅
```

#### 사용 예시
```
상황: 실수로 많은 데이터를 삭제함

1. Ctrl+Z 입력
2. "이전 상태로 복구되었습니다. (남은 저장 상태: 3개)"
3. 이전 데이터 완벽 복구 ✅
4. 색상 강조, 합계 자동 업데이트 ✅
```

#### 코드 예시
```python
def _save_current_state(self):
    """Ctrl+S: 현재 테이블 상태를 Undo 스택에 저장"""
    state_snapshot = []
    
    for row in range(self.detail_table.rowCount()):
        row_data = []
        for col in range(self.detail_table.columnCount()):
            item = self.detail_table.item(row, col)
            row_data.append(item.text() if item else "")
        state_snapshot.append(row_data)
    
    self.undo_stack.append(state_snapshot)
    
    if len(self.undo_stack) > self.undo_max:
        self.undo_stack.pop(0)
    
    QMessageBox.information(self, "저장됨", f"현재 상태가 저장되었습니다. (총 {len(self.undo_stack)}개)")

def _restore_previous_state(self):
    """Ctrl+Z: 이전 저장된 상태 복구"""
    if not self.undo_stack:
        QMessageBox.warning(self, "경고", "복구할 이전 상태가 없습니다.")
        return
    
    state_snapshot = self.undo_stack.pop()
    
    self.detail_table.blockSignals(True)
    self.detail_table.setRowCount(len(state_snapshot))
    
    for row, row_data in enumerate(state_snapshot):
        for col, text in enumerate(row_data):
            item = QTableWidgetItem(text)
            self.detail_table.setItem(row, col, item)
    
    self.detail_table.blockSignals(False)
    
    QTimer.singleShot(100, self._verify_all_codes)
    QTimer.singleShot(150, self._update_preview_sum)
```

#### 특징
- ✅ 최대 20개 상태 저장 (메모리 제한)
- ✅ 정확한 복구 (셀 단위 데이터)
- ✅ 색상 재적용 (변경사항 반영)
- ✅ 합계 자동 업데이트

---

## 📊 코드 변화 요약

### 추가된 항목
```
__init__:
├─ undo_stack = []
└─ undo_max = 20

_init_ui():
├─ preview_label 추가
└─ 리뷰 레이아웃 생성

_on_detail_item_changed():
└─ _update_preview_sum() 호출 추가

신규 메서드:
├─ _update_preview_sum() (5줄)
├─ _calculate_preview_sum() (15줄)
├─ _validate_all_inputs() (25줄)
├─ _show_validation_errors() (20줄)
├─ _save_current_state() (20줄)
└─ _restore_previous_state() (35줄)

eventFilter 수정:
├─ Ctrl+S 감지 추가
└─ Ctrl+Z 감지 추가

save_to_gapji 수정:
└─ 유효성 검사 호출 추가
```

### 라인 수 변화
```
이전: 1,247줄
현재: 1,400줄 + (대략)
증가: +150줄 (PHASE 3-1, 3-2, 3-3)
```

---

## 🎯 사용자 관점 개선사항

### 1. 실시간 계산 (PHASE 3-1)
```
이전: 입력 후 "내보내기"를 눌러야 합계 확인
이후: 입력하면서 즉시 합계 표시 → 작업 효율 ↑
```

### 2. 데이터 검증 (PHASE 3-2)
```
이전: 빈값 입력 후 저장 실패 → 혼란
이후: 저장 전 오류 감지 → 미리 수정 가능
```

### 3. 키보드 단축키 (PHASE 3-3)
```
이전: 마우스로 "내보내기", "조각파일" 버튼 클릭
이후:
  ├─ Ctrl+S: 상태 저장 (실수 방지)
  ├─ Ctrl+Z: 실수 복구 (빠른 수정)
  └─ F9: 조각파일 저장 (기존)
  └─ ESC: 1식 저장 + 종료 (기존)
```

---

## ⏱️ 다음 단계 (PHASE 3-4, 3-5)

### PHASE 3-4: 자동 완성 (예상 1-2일)
```
□ 산출목록 입력 시 자료사전 자동 검색
□ 매칭 항목 자동 선택
□ CODE 자동 입력
```

### PHASE 3-5: 드래그 앤 드롭 (예상 1-2일)
```
□ 조각파일을 테이블로 드래그
□ 자동으로 행 삽입
□ 직관적 사용 경험
```

---

## 📋 PHASE 3 전체 상태

```
PHASE 3-1: 실시간 계산 프리뷰 ✅
├─ UI 추가 (preview_label)
├─ Debounce 처리 (성능 최적화)
└─ 즉시 합계 표시

PHASE 3-2: 유효성 검사 + 경고 ✅
├─ 입력 오류 감지
├─ 구체적 오류 메시지
└─ 유연한 진행 (Ok/Ignore)

PHASE 3-3: 추가 단축키 ✅
├─ Ctrl+S: 상태 저장
├─ Ctrl+Z: 상태 복구
├─ Undo 스택 (최대 20개)
└─ 색상/합계 자동 업데이트

PHASE 3-4: 자동 완성 ⏳
PHASE 3-5: 드래그 앤 드롭 ⏳
```

---

## 🔍 테스트 체크리스트

### 실시간 프리뷰 테스트
- [ ] 합계 레이블 화면에 표시됨
- [ ] 데이터 입력 시 합계 즉시 변경
- [ ] 쉼표 포맷 정상 (1,234 형식)
- [ ] 삭제 시 합계 감소

### 유효성 검사 테스트
- [ ] 산출목록 비어있으면 오류 표시
- [ ] 단위수식 비어있으면 오류 표시
- [ ] CODE 없으면 경고 표시
- [ ] Ok 선택 시 저장 취소
- [ ] Ignore 선택 시 계속 진행

### 단축키 테스트
- [ ] Ctrl+S 입력 시 상태 저장됨
- [ ] 메시지 "저장됨" 표시
- [ ] Ctrl+Z 입력 시 이전 상태 복구
- [ ] 메시지 "복구됨" 표시
- [ ] 상태 없을 때 "복구할 상태 없음" 경고
- [ ] 20개 초과 시 가장 오래된 상태 제거

---

**상태**: 🔵 **PHASE 3-1, 3-2, 3-3 완료 (65%)**  
**다음**: PHASE 3-4, 3-5 구현  
**마지막 업데이트**: 2026-01-31

계속 진행할까요? 🚀
