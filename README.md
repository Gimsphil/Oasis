# 📑 오아시스 (OASIS)
## 전기 견적,수량산출 시스템

전기 견적 및 수량산출을 위한 PyQt6 기반 GUI 시스템입니다.

## 📋 개요

- **프로그램명**: 오아시스 (OASIS)
- **버전**: 1.0.0 (Standalone)
- **기반**: PyQt6 기반 GUI 애플리케이션

## 🚀 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 프로그램 실행

```bash
python main.py
```

## 📁 폴더 구조

```
OutputDetail_Standalone/
├── main.py                 # 메인 진입점
├── output_detail_tab.py    # 산출내역 탭 (갑지/을지)
├── utils/
│   ├── column_settings.py  # 테이블 컬럼 설정
│   └── grid_clipboard.py   # 클립보드/그리드 유틸리티
├── core/
│   └── app_style.py        # 앱 스타일 설정
├── assets/
│   ├── fonts/             # 폰트 파일
│   └── icons/             # 아이콘 파일
├── requirements.txt       # 의존성 목록
└── README.md             # 이 파일
```

## ✨ 주요 기능

### 갑지 (총괄표)
- 공종 목록 관리
- 공종 순서 및 구분 설정
- 수량 입력 및 계산
- 층고/천장 높이 설정

### 을지 (상세산출)
- 상세 산출내역 작성
- 산출 수식 입력
- 회로 및 단위 관리
- FROM/TO 위치 지정

### 공통 기능
- 엑셀 스타일 테이블 UI
- 행/열 추가 및 삭제 (Ctrl+N, Ctrl+Y)
- 실행 취소 (Ctrl+Z)
- 셀 편집 (F2)
- 클립보드 복사/붙여넣기
- 자동 행 확장

## ⌨️ 단축키

| 단축키 | 기능 |
|--------|------|
| Ctrl+N | 행 삽입 |
| Ctrl+Y | 행 삭제 |
| Ctrl+Z | 실행 취소 |
| F2 | 셀 편집 |
| Enter | 다음 행으로 이동 |
| Tab | 다음 셀로 이동 |

## 📝 데이터 파일

- 공종 목록: `gongjong/` 폴더 내 텍스트 파일
- 설정 및 데이터: SQLite DB 파일

## ⚠️ 주의사항

1. 이 프로그램은 전기 견적 및 수량산출 기능을 포함합니다.
2. 데이터 파일 경로를 확인 후 사용하세요.

## 🔧 문제 해결

### 실행이 안 될 때
```bash
# 의존성 재설치
pip install --upgrade -r requirements.txt
```

### 폰트가 깨질 때
- `assets/fonts/` 폴더에 GoogleSansFlex.ttf 파일을 추가하세요.

## 📞 지원

문제가 발생하면 execution_log.txt 파일을 확인하세요.

---

**라이선스**: 내부 사용 전용
