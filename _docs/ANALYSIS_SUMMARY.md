# 🎯 산출 시스템 분석 완료 - 요약 및 다음 단계

**분석 완료일**: 2026-01-31  
**분석 대상**: 전기 설비 산출 시스템 (OutputDetail_Standalone)  
**작성자**: GitHub Copilot

---

## 📊 분석 결과 요약

### **전체 구현도: 40% / 100%**

```
✅ 구현 완료 (40%)
├─ 아키텍처 설계 ✅
├─ 기본 UI (갑지 + 좌측 패널) ✅
├─ 세부산출조서 기본 틀 ✅
├─ 사칙연산 계산 엔진 ✅
├─ 단축키 기본 (Ctrl+N/Y) ✅
└─ 자료사전 DB 경로 설정 ✅

❌ 미구현 (60%)
├─ TAB 키 → 자료사전 팝업 호출 🔴 1순위
├─ 자료사전 팝업 3차 창 🔴 2순위
├─ 데이터 전송 규칙 🔴 3순위
├─ W 컬럼 검증 표시 🔴 4순위
├─ 수동 CODE 매칭 (===) 🔴 5순위
├─ 1식 저장 (산출내역서 반영) 🔴 6순위
├─ 조각파일 기능 (F9) 🟡 선택
├─ 재진입 상태 복구 🟡 선택
└─ 추가 색상/경고 표시 🟡 선택
```

---

## 🔴 필수 완료 항목 (1-6순위)

| 순위 | 기능 | 영향도 | 예상소요 | 의존도 |
|------|------|--------|---------|--------|
| 1️⃣ | **TAB 키 → 팝업 호출** | 🔴 높음 | 1-2일 | 독립 |
| 2️⃣ | **자료사전 팝업 UI** | 🔴 높음 | 2-3일 | 1번 이후 |
| 3️⃣ | **데이터 전송 규칙** | 🔴 높음 | 1-2일 | 2번 이후 |
| 4️⃣ | **W 컬럼 검증 표시** | 🟠 중간 | 1-2일 | 1번 이후 |
| 5️⃣ | **수동 CODE 매칭** | 🟠 중간 | 2일 | 2번 이후 |
| 6️⃣ | **1식 저장** | 🔴 높음 | 1-2일 | 3번 이후 |

---

## 💾 생성된 문서

### 1. [ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md)
```
목차:
1. 요구사항 vs 현재 구현 상태 매핑
2. 아키텍처 구조 검증
3. 데이터 흐름 검증
4. DB 스키마 확인 필요
5. 미확정/추정 항목
6. 권장 개선 우선순위
7. 코드 품질 메모
8. 결론
```
**목적**: 3계층 UI 아키텍처와 데이터 흐름 전체 검증

### 2. [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)
```
목차:
1. 현재 구현 현황 (40%)
2. 필수 미확정 사항
3. 파일 구조 및 역할
4. 실행 우선순위 로드맵 (PHASE 1-4)
5. 즉시 필요한 작업
6. 코드 품질 평가
7. 다음 단계
```
**목적**: 세부 구현 상태와 로드맵, 즉시 필요한 작업 명시

---

## 🎯 즉시 필요한 3가지 작업

### **작업 1: 자료사전.db 스키마 상세 분석** 📋
```
확인할 사항:
✓ 테이블 목록
✓ [자료사전] 테이블의 모든 컬럼명
✓ 각 컬럼의 데이터 타입
✓ 샘플 데이터 5-10행
✓ 일위대가 판정 컬럼 (어느 컬럼/값?)
✓ 그룹, 목록2~6, 약칭, W, 검색목록 존재 여부

이 정보가 필요한 이유:
→ 자료사전 팝업 UI 컬럼 구성
→ 검색 기능 구현
→ W 컬럼 매칭 로직
```

### **작업 2: 미확정 정책 3가지 확정** ⚙️
```
1️⃣ 조각파일 (.piece) 포맷
   ├─ JSON 방식
   ├─ CSV 방식
   └─ 이진 방식 중 선택?

2️⃣ 수동 매칭 저장 위치
   ├─ 엑셀 파일에 저장
   ├─ SQLite DB에 저장
   └─ 메모리만 유지 (세션 중) 중 선택?

3️⃣ 미매칭(~*) 상태 저장 정책
   ├─ 저장 차단
   ├─ 경고 후 저장
   └─ 자유롭게 허용 중 선택?
```

### **작업 3: 사용자와 협의** 🤝
```
다음을 사용자와 확인:
1. "일위대가(i)" 판정 기준이 정확히 무엇인가?
   → 자료사전 어느 컬럼의 어떤 값?
   → 조명기구타입.db와 어떤 연관?

2. 산출일위 "원본" 데이터는 어디에 저장되나?
   → 엑셀 파일? SQLite? 메모리?

3. 재진입 시 세부산출조서 데이터 초기화 vs 복구?
   → 매번 초기 상태? 이전 입력값 유지?
```

---

## 📂 현재 파일 구조 및 담당 역할

```
OutputDetail_Standalone/
│
├── main.py ✅ 완성 (진입점)
│   └─ 역할: 앱 초기화, 경로 설정, 예외 처리
│
├── output_detail_tab.py ✅ 부분 (메인 UI)
│   ├─ 역할: 산출내역서(갑지) + 좌측 공종 리스트
│   └─ 미완료: 세부산출조서 종료 후 데이터 반영
│
├── lighting_power_manager.py ⚠️ 부분 (세부산출조서)
│   ├─ LightingPowerManager: 공종 관리
│   ├─ LightingPowerPopup: 세부산출조서 팝업 (UI 기본 틀)
│   └─ 미완료: TAB/자료사전팝업/데이터전송/W컬럼/매칭/저장
│
├── core/app_style.py ✅ 완성 (폰트 + 스타일)
│
├── utils/column_settings.py ✅ 완성 (컬럼 정의)
├── utils/grid_clipboard.py ✅ 완성 (클립보드)
│
└── data/자료사전.db ✅ 존재 (스키마 상세 분석 필요)
```

---

## 🔧 다음 단계별 구현 계획

### **PHASE 1: 핵심 3기능 (예상 3-5일)**

#### 1-1. TAB 키 이벤트 핸들러
```python
# lighting_power_manager.py의 LightingPowerPopup 클래스에 추가:

def eventFilter(self, obj, event):
    """TAB 키 감지 → 자료사전 팝업 호출"""
    if event.type() == QEvent.Type.KeyPress:
        if event.key() == Qt.Key.Key_Tab:
            self.show_reference_db_popup()  # ← 호출
            return True
    return False

def show_reference_db_popup(self):
    """자료사전 DB 팝업 표시"""
    # 팝업 창 생성 및 표시
    pass
```

#### 1-2. 자료사전 팝업 UI 구성
```python
# 새로운 클래스 생성:

class DatabaseReferencePopup(QDialog):
    """자료사전 DB 팝업 (3차 창)"""
    
    def __init__(self, parent=None):
        # 상단: 산출일위 품목 리스트
        # 중앙: 자료사전 데이터 테이블 (6컬럼)
        # 하단: 보내기, 닫기 버튼
        pass
    
    def _init_ui(self):
        # UI 구성
        pass
    
    def _load_reference_data(self):
        # 자료사전.db에서 데이터 로드
        pass
```

#### 1-3. 데이터 전송 로직
```python
# DatabaseReferencePopup에 추가:

def on_send_clicked(self):
    """보내기 버튼 클릭"""
    # 선택된 행의 데이터 추출
    # 산출일위 테이블로 데이터 전송
    # 상위 LightingPowerPopup 신호 발생
    pass

def on_escape_pressed(self):
    """ESC 키 처리"""
    # on_send_clicked()와 동일
    pass
```

### **PHASE 2: 검증 + 매칭 (예상 2-3일)**

#### 2-1. W 컬럼 검증
```python
# lighting_power_manager.py에 추가:

def _verify_all_codes(self):
    """모든 행의 CODE 검증 및 W 컬럼 업데이트"""
    for row in range(self.detail_table.rowCount()):
        code = self.detail_table.item(row, 1).text()  # CODE 컬럼
        w_status = self._get_w_status(code)  # 검증
        self.detail_table.setItem(row, 0, QTableWidgetItem(w_status))  # W 컬럼
```

#### 2-2. 수동 매칭 (=== 기능)
```python
# 자료사전 팝업에서:

def handle_triple_equals(self):
    """수량 컬럼에 === 입력 → CODE 강제 연결"""
    if not self.active_target:
        # 경고: active_target 미선택
        return
    
    # 현재 행의 CODE 읽기
    selected_code = self.get_selected_row_code()
    
    # active_target의 CODE에 저장
    self.set_active_target_code(selected_code)
    
    # 상위 팝업의 W 컬럼 재검증
    self.parent_popup._verify_all_codes()
```

### **PHASE 3: 저장 + 조각파일 (예상 2-3일)**

#### 3-1. 1식 저장
```python
# output_detail_tab.py에 추가:

def save_to_gapji(self, popup_data):
    """세부산출조서 데이터 → 산출내역서 1식 저장"""
    row = self.current_row
    
    # 산출목록 = 선택된 공종명
    self.gapji_table.setItem(row, 3, QTableWidgetItem(popup_data['gongjong']))
    
    # 산출수식 = 1
    self.gapji_table.setItem(row, 5, QTableWidgetItem("1"))
    
    # 계 = 세부산출조서 최종 합계
    self.gapji_table.setItem(row, 6, QTableWidgetItem(str(popup_data['total'])))
    
    # 단위 = 식
    self.gapji_table.setItem(row, 7, QTableWidgetItem("식"))
```

#### 3-2. 조각파일 (F9)
```python
# lighting_power_manager.py에 추가:

def save_as_piece_file(self):
    """F9: 선택 행들을 조각파일로 저장"""
    selected_rows = self.detail_table.selectedIndexes()
    
    # 선택된 행 데이터 추출
    piece_data = self.extract_selected_rows()
    
    # 파일로 저장 (JSON 형식 추천)
    file_path = QFileDialog.getSaveFileName(
        self, "조각파일 저장", "", "조각파일 (*.piece);;모든파일 (*)"
    )[0]
    
    if file_path:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(piece_data, f, ensure_ascii=False, indent=2)
```

---

## ✅ 검증 항목

현재 코드가 다음을 충족하는지 확인:

- [ ] `detail_table`에 KeyEventFilter 설치됨
- [ ] TAB 키 감지 이벤트 핸들러 있음
- [ ] 자료사전 팝업 클래스 존재 (또는 분리 계획)
- [ ] 6컬럼 테이블 구성 (ID/품목/규격/단위/CODE/수량)
- [ ] 상단 품목 리스트 UI 있음
- [ ] 보내기/ESC 데이터 전송 로직 있음
- [ ] 검색 기능 (Enter 입력 시) 구현됨
- [ ] W 컬럼 매칭 로직 있음
- [ ] 수동 매칭 (===) 기능 있음
- [ ] 1식 저장 로직 있음

---

## 📞 사용자 확인 필요

다음 사항을 사용자와 협의하여 확정:

1. **자료사전.db 스키마 설명**
   - 정확한 테이블명 / 컬럼명 / 데이터타입
   - 일위대가 판정 기준 (어느 컬럼/값?)

2. **조각파일 포맷 선택**
   - JSON? CSV? 이진?

3. **수동 매칭 저장 위치**
   - 엑셀/DB/메모리 중 선택

4. **미매칭(~*) 저장 정책**
   - 저장 차단/경고/허용 중 선택

5. **재진입 동작**
   - 이전 입력값 유지? 초기화?

---

## 🎓 학습 포인트

### 현재 코드에서 배울 점 ✅
- 경로 설정 및 임포트 명확화
- 예외 처리 우수 사례
- Qt의 Master-Detail 패턴
- 사칙연산 보안 처리 (eval 제약)
- Undo 스택 구현

### 개선할 점 ⚠️
- 클래스 크기 (683줄 → 300줄 이하로 분리)
- DB 스키마 하드코딩 (설정 파일로 외부화)
- 테스트 코드 작성
- 문서 주석 추가
- 타입 힌팅 (Python 3.9+)

---

## 📋 결론

**현재 상태**: ✅ 기본 아키텍처 구축 완료  
**다음 단계**: 🔴 TAB 키 이벤트 → 자료사전 팝업 → 데이터 전송

**권장 진행 순서**:
1. 자료사전.db 스키마 상세 분석 (1일)
2. TAB 키 + 팝업 호출 구현 (2일)
3. 데이터 전송 로직 (2일)
4. W 컬럼 + 매칭 (2-3일)
5. 1식 저장 + 조각파일 (2-3일)

**예상 총소요**: 1-2주

---

**문서 생성**: ARCHITECTURE_ANALYSIS.md, IMPLEMENTATION_STATUS.md  
**작업 완료**: 2026-01-31
