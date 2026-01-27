# Saver 모듈 아키텍처

이 문서에서는 saver 모듈의 내부 동작 원리와 설계 철학을 설명합니다.

## 개념 소개

saver 모듈은 스크래퍼로 수집한 데이터를 영구 저장소에 저장하는 기능을 담당합니다. CSV 파일과 SQLite 데이터베이스 두 가지 저장 방식을 지원합니다.

## 모듈 구조

```
src/saver/
├── __init__.py       # 모듈 인터페이스 (save_to_csv, save_to_db 공개)
├── csv_saver.py      # CSV 저장 기능
└── db_saver.py       # SQLite DB 저장 기능
```

## CSV Saver 아키텍처

CSV Saver는 단순한 파이프라인 구조입니다.

```
┌─────────────────┐
│  입력 검증      │  Step 1: 빈 데이터 검사
│  (Validation)   │         - 빈 리스트면 None 반환
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  DataFrame 변환 │  Step 2: pandas DataFrame 생성
│  (Conversion)   │         - list[dict] → DataFrame
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  파일 저장      │  Step 3: CSV 파일로 저장
│  (Save)         │         - UTF-8 with BOM 인코딩
└────────┬────────┘         - data/ 디렉토리에 저장
         │
         ↓
┌─────────────────┐
│  경로 반환      │  Step 4: 저장된 파일 경로 반환
│  (Return)       │
└─────────────────┘
```

### 핵심 설계 원리

1. **단순성**: 최소한의 기능으로 빠르고 안정적인 저장
2. **한글 지원**: `utf-8-sig` 인코딩으로 엑셀 호환성 보장
3. **자동 디렉토리 생성**: `data/` 폴더가 없으면 자동 생성

## DB Saver 아키텍처

DB Saver는 타입 추론과 변환 기능이 포함된 복잡한 파이프라인입니다.

```
┌─────────────────┐
│  입력 변환      │  Step 1: 다양한 입력 형식 지원
│  (Input)        │         - DataFrame, list[dict], CSV 경로
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  타입 추론      │  Step 2: 컬럼별 SQLAlchemy 타입 결정
│  (Type Infer)   │         - pandas dtype → SQL 타입
└────────┬────────┘         - 날짜 패턴 감지
         │
         ↓
┌─────────────────┐
│  데이터 변환    │  Step 3: 날짜 컬럼 타입 변환
│  (Convert)      │         - 문자열 → datetime 객체
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  DB 저장        │  Step 4: SQLite에 저장
│  (Save)         │         - SQLAlchemy 엔진 사용
└────────┬────────┘         - replace/append/fail 모드
         │
         ↓
┌─────────────────┐
│  경로 반환      │  Step 5: 저장된 DB 경로 반환
│  (Return)       │
└─────────────────┘
```

### 핵심 설계 원리

1. **다양한 입력 지원**: DataFrame, 딕셔너리 리스트, CSV 파일 경로를 모두 처리
2. **자동 타입 추론**: pandas dtype과 문자열 패턴을 분석하여 적절한 SQL 타입 결정
3. **날짜 처리 최적화**: `YYYY-MM-DD HH:MM:SS` 형식을 자동 인식하여 DATETIME으로 저장
4. **유연한 저장 모드**: replace, append, fail 옵션으로 다양한 사용 시나리오 지원

## 데이터 흐름

### 스크래퍼 → CSV

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Scraper    │ --> │  list[dict]  │ --> │   CSV File   │
│              │     │              │     │  (.csv)      │
└──────────────┘     └──────────────┘     └──────────────┘
     수집                 메모리               파일
```

### 스크래퍼 → DB

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Scraper    │ --> │  list[dict]  │ --> │  DataFrame   │ --> │   SQLite     │
│              │     │              │     │  (pandas)    │     │  (.db)       │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
     수집                 메모리             타입 변환            파일
```

### CSV → DB

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  CSV File    │ --> │  DataFrame   │ --> │   SQLite     │
│  (.csv)      │     │  (pandas)    │     │  (.db)       │
└──────────────┘     └──────────────┘     └──────────────┘
     파일              타입 추론/변환          파일
```

## 저장 위치

모든 데이터는 프로젝트 루트의 `data/` 디렉토리에 저장됩니다.

```python
# csv_saver.py, db_saver.py 공통
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CURRENT_DIR, "..", "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
```

```
project/
├── data/
│   ├── kleague1_match_2025.csv
│   ├── jleague1_match_2025.csv
│   └── match.db
└── src/
    └── saver/
```

## CSV vs DB 비교

| 특성 | CSV | SQLite DB |
|-----|-----|-----------|
| 파일 형식 | 텍스트 | 바이너리 |
| 타입 보존 | 없음 (모두 문자열) | 있음 |
| 쿼리 기능 | 없음 | SQL 지원 |
| 엑셀 호환 | 좋음 | 별도 도구 필요 |
| 대용량 처리 | 느림 | 빠름 |
| 증분 저장 | 어려움 | append 지원 |

## 관련 문서

- [타입 자동 추론](./type-inference.md)
- [CSV Saver API 레퍼런스](../reference/csv-saver-api.md)
- [DB Saver API 레퍼런스](../reference/db-saver-api.md)
