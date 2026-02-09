## OASIS 앱 - 실행 가이드 (고쳐짐!)

### 🔧 적용된 수정 사항

2026년 2월 9일에 다음 문제들이 수정되었습니다:

#### 1. **PyQt6 호환성 문제 (QMimeData Import Error)**
- **파일**: `lighting_power_manager.py`
- **문제**: QMimeData를 PyQt6.QtCore에서 찾을 수 없음 (버전 호환성)
- **해결책**: 조건부 import 추가
  ```python
  try:
      from PyQt6.QtCore import QMimeData
  except ImportError:
      from PyQt6.QtGui import QMimeData
  ```

#### 2. **인코딩 에러 (UnicodeEncodeError)**
- **파일**: `main.py`
- **문제**: Windows 콘솔이 UTF-8 이모지를 처리할 수 없음
- **해결책**: 
  - 모든 이모지 제거
  - stdout/stderr을 UTF-8로 래핑
  ```python
  if sys.stdout.encoding.lower() != 'utf-8':
      import io
      sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
      sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
  ```

#### 3. **Python 경로 최적화**
- **파일**: `start.bat`
- **문제**: 절대 경로 없이 pythonw.exe를 찾을 수 없음
- **해결책**: 절대 경로 지정
  ```batch
  set PYTHON_PATH=C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe
  ```

#### 4. **필요한 패키지 설치**
- PyQt6
- pandas
- numpy
- openpyxl
- xlrd
- python-dateutil
- pytz

### ▶️ 실행 방법

#### 방법 1: GUI 모드 (권장)
```batch
start.bat
```

#### 방법 2: 콘솔 모드 (디버깅용)
```batch
run_console.bat
```

#### 방법 3: 직접 실행
```bash
python main.py
```

### ⚙️ 요구사항

- **Python**: 3.14 (설치됨)
- **PyQt6**: 6.4.0 이상
- **필수 패키지**: requirements.txt 참조

### 🔗 주요 파일

- `main.py`: 메인 애플리케이션
- `start.bat`: GUI 실행 스크립트
- `lighting_power_manager.py`: 조명/전열 관리 모듈
- `output_detail_tab.py`: 산출내역 탭 UI

### 📝 작동 확인

앱이 정상 시작되면:
1. OASIS 로고가 표시된 윈도우가 나타남
2. `startup_debug.log` 파일에 로그가 기록됨
3. 프로그램이 정상 종료될 때까지 실행 유지

### 🆘 문제 해결

문제가 있으면 다음을 확인하세요:

1. **Python 설치 확인**:
   ```batch
   C:\Users\KIMPHIL\AppData\Local\Programs\Python\Python314\python.exe --version
   ```

2. **PyQt6 설치 확인**:
   ```batch
   python -m pip list | findstr PyQt6
   ```

3. **로그 파일 확인**:
   - `startup_debug.log`
   - `app_startup_debug.txt`

### 📧 최종 상태

✅ **모든 수정 완료** - 앱이 정상 작동해야 합니다!
